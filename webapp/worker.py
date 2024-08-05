import time
import random
import datetime
import traceback
from webapp.logger import logger

from webapp.database import SessionLocal
from webapp.schemas import Task, Post, Topic, UploadedFile
from webapp.utils import reply_post
from webapp.doc_rag import doc_rag, classify_intention, doc_search

from common.agents.questioning_agent import questioning_agent
from common.agents.obdiag_agent import obdiag_agent
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class ChatHistory:
    
    def __init__(self, chat_history: list[BaseMessage] = []):
        self.chat_history = chat_history


    def get_turns(self) -> int:
        turns = 0
        for talk in self.chat_history:
            if talk.type == AIMessage.type:
                turns += 1

        return turns

    def add_chat(self, msg: BaseMessage):
        self.chat_history.append(msg)
    
    
    def add_topic_title(self, title: str):
        if len(self.chat_history) > 0:
            self.chat_history[0].content = title + "\n" + self.chat_history[0].content

    
    def pop_latest_user_query(self) -> str:
        messages: list[BaseMessage] = []
        while len(self.chat_history) > 0:
            if self.chat_history[-1].type == HumanMessage.type:
                talk = self.chat_history.pop()
                messages.append(talk.content)
            else:
                break
        return "\n".join(map(lambda m: m.content, messages))


def task_worker(no: int, **kwargs):
    logger.info(f"Task worker {no} started")
    debug = kwargs.get("debug", False)
    bot_id = kwargs.get("bot_id", 1)
    while True:
        with SessionLocal() as db:
            try:
                preds = [Task.task_status.in_([Task.Status.Pending.value, Task.Status.Processing.value]), Task.task_type == "topic"]
                if not debug:
                    preds.append(Task.triggered_at <= datetime.datetime.now())
                task: Task | None = (
                    db.query(Task)
                    .filter(*preds)
                    .first()
                )
                if task is None:
                    time.sleep(random.randrange(5, 20))
                    continue

                topic: Topic | None = (
                    db.query(Topic).where(Topic.id == task.topic_id).first()
                )
                if topic is None:
                    logger.info(f"Task worker {no} failed to find topic {task.topic_id}")
                    if task.task_status == task.Status.Pending.value:
                        task.processing()
                        task.delay(minutes=1)
                    elif task.task_status == task.Status.Processing.value:
                        task.failed()
                        
                    db.commit()
                    time.sleep(random.randrange(5, 20))
                    continue

                # Do some work here
                post_extra_content = {}
                posts: list[Post] = (
                    db.query(Post)
                    .where(
                        Post.topic_id == task.topic_id,
                        Post.sender_id.in_([topic.creator_id, bot_id]),
                    )
                    .order_by(Post.post_number)
                    .all()
                )

                if len(posts) == 0:
                    logger.info(f"Topic {topic.id} has no posts, rescheduling task")
                    task.delay(minutes=5)
                    db.commit()
                    continue

                if posts[-1].sender_id != topic.creator_id:
                    # User has not replied
                    logger.info(f"User has not replied topic {topic.id} yet, rescheduling task")
                    task.delay(minutes=random.randrange(5, 20))
                    db.commit()
                    continue

                files: list[UploadedFile] = (
                    db.query(UploadedFile)
                    .where(UploadedFile.post_id.in_([post.id for post in posts]))
                    .all()
                )
                for p in posts:
                    post_extra_content[p.id] = ""
                for f in files:
                    if f.processed:
                        post_extra_content[f.post_id] += ('\n' + f.content)

                history = ChatHistory()
                
                for p in posts:
                    if p.sender_id == bot_id:
                        history.add_chat(AIMessage(p.raw))
                    else:
                        history.add_chat(HumanMessage('\n'.join([p.raw, post_extra_content[p.id]])))

                history.add_topic_title(topic.title)
                
                query_content = history.pop_latest_user_query()
                chat_turns = history.get_turns()
                chat_history = history.chat_history
                
                logger.debug(f"previous conversations: {chat_history}")

                rewritten = query_content
                # Pass to guard agent
                if topic.llm_classified_to is None:
                    logger.debug(f"Guard Agent: {query_content}")
                    ic = classify_intention(query_content, chat_history=chat_history)
                    rewritten = ic.rewritten
                    
                    logger.debug(f"Question type: {ic.intention}, rewritten: {rewritten}")

                    if ic.intention == "闲聊":
                        topic.llm_classified_to = Topic.Clf.Casual.value
                    elif ic.intention == "特性问题":
                        topic.llm_classified_to = Topic.Clf.Features.value
                    elif ic.intention == "诊断问题":
                        topic.llm_classified_to = Topic.Clf.Diagnostic.value

                    db.commit()

                if topic.llm_classified_to == Topic.Clf.Casual.value:
                    task.done()
                    db.commit()
                elif topic.llm_classified_to == Topic.Clf.Features.value:
                    # RAG here
                    answer = doc_rag(query_content, chat_history, rewritten=rewritten)
                    logger.debug(answer)
                    reply_post(topic_id=topic.id, raw=answer)
                    if chat_turns >= 1:
                        # At most reply two posts
                        task.done()
                    else:
                        task.processing()
                        task.delay()
                elif topic.llm_classified_to == Topic.Clf.Diagnostic.value:                
                    log_uploaded = False
                    for f in files:
                        if f.file_type == UploadedFile.FileType.Archive.value and f.processed:
                            log_uploaded = True
                            break

                    if not log_uploaded and task.task_status == task.Status.Pending.value:
                        logger.debug(f"obdiag classification agent: {rewritten}")
                        docs = doc_search(rewritten, length_limit=1200)
                        # Persist the search result
                        content = f"\n根据用户的问题描述查询到的文档如下: (用 === 包裹的部分为搜索结果)\n===\n{docs.documents}\n===\n"
                        saved_search = UploadedFile(
                            post_id=posts[-1].id, 
                            name="search_result", 
                            path="search_result", 
                            file_type=UploadedFile.FileType.Docs.value, 
                            created_at=datetime.datetime.now(), 
                            content=content,
                            processed=True)
                        db.add(saved_search)
                        
                        answer = obdiag_agent.invoke(rewritten, documents_snippets=docs.documents)
                        answer += ('\n\n'+docs.references)
                        answer += ('\n\n'+'附上敏捷诊断工具 [obdiag 使用帮助链接](https://ask.oceanbase.com/t/topic/35605619)')
                        reply_post(topic_id=topic.id, raw=answer)
                        task.processing()
                        task.delay()
                    else:
                        logger.debug(f"questioning agent: query content: {query_content}, chat history: {chat_history}")
                        polished_history = list(map(lambda x: {"content": x["发言"], "type": "human" if x["角色"] == '用户' else "ai"}, chat_history))
                        output_object = questioning_agent.invoke_json(
                            query_content, 
                            history=polished_history
                        )
                        complete = output_object.get("complete", True)
                        logger.debug(f"问题{"可解决" if complete else "不可解决"}")
                        if complete or chat_turns >= 2:
                            answer = doc_rag(query_content, chat_history, rewritten=rewritten)
                            reply_post(topic_id=topic.id, raw=answer)
                            task.done()
                        else:
                            questions = output_object.get("questions")
                            for i, q in enumerate(questions):
                                questions[i] = f"{i + 1}. {q}"
                            
                            answer = "再向您确认几个问题:\n" + '\n'.join(questions)
                            reply_post(topic_id=topic.id, raw=answer)
                            task.delay()

                if debug:
                    return
            except Exception:
                task.failed()
                traceback.print_exc()
            finally:
                db.commit()
            


if __name__ == "__main__":
    print(doc_rag("请问创建租户时 ob_compatiblity_control 这个参数是哪个社区版本开始用的"))
