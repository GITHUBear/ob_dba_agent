import time
import random
import datetime
import traceback
from ob_dba_agent.web.logger import logger

from ob_dba_agent.web.database import SessionLocal
from ob_dba_agent.web.schemas import Task, Post, Topic, UploadedFile
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.action.knowledge.store.document import Document
from agentuniverse.agent.agent import Agent
from ob_dba_agent.web.utils import reply_post
from ob_dba_agent.web.doc_rag import doc_rag


class ChatHistory:
    
    class Role:
        User = "用户"
        Bot = "机器人"
    

    def __init__(self, chat_history: list[dict] = []):
        self.chat_history = chat_history


    def get_turns(self) -> int:
        turns = 0
        for talk in self.chat_history:
            if talk["角色"] == self.Role.Bot:
                turns += 1

        return turns

    def add_chat(self, role: str, content: str):
        self.chat_history.append({
            "角色": role,
            "发言": content,
        })
    
    
    def add_topic_title(self, title: str):
        if len(self.chat_history) > 0:
            self.chat_history[0]["发言"] = title + "\n" + self.chat_history[0]["发言"]

    
    def pop_latest_user_query(self) -> str:
        messages: list = []
        while len(self.chat_history) > 0:
            if self.chat_history[-1]["角色"] == "用户":
                talk = self.chat_history.pop()
                messages.append(talk["发言"])
            else:
                break
        return "\n".join(messages)


def task_worker(no: int, **kwargs):
    logger.info(f"Task worker {no} started")
    debug = kwargs.get("debug", False)
    bot_name = kwargs.get("bot_name", "汤圆")
    while True:
        try:
            with SessionLocal() as db:
                preds = [Task.task_status.in_([Task.Status.Pending.value, Task.Status.Processing.value]), Task.task_type == "topic"]
                if not debug:
                    preds.append(Task.triggered_at <= datetime.datetime.now())
                task: Task | None = (
                    db.query(Task)
                    .filter(*preds)
                    .first()
                )
                
                if task is None:
                    sleep_secs = random.randrange(5, 20)
                    logger.info(f"Task worker {no} waiting for task to be triggered. Sleep for {sleep_secs} secs")
                    time.sleep(sleep_secs)
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
                        Post.username.in_([topic.creator_username, bot_name]),
                    )
                    .order_by(Post.post_number)
                    .all()
                )

                if len(posts) == 0:
                    logger.info(f"Topic {topic.id} has no posts, rescheduling task")
                    task.delay(minutes=5)
                    db.commit()
                    continue

                if posts[-1].username != topic.creator_username:
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
                    if p.username == bot_name:
                        history.add_chat(ChatHistory.Role.Bot, p.raw)
                    else:
                        history.add_chat(ChatHistory.Role.User, '\n'.join([p.raw, post_extra_content[p.id]]))

                history.add_topic_title(topic.title)
                
                query_content = history.pop_latest_user_query()
                chat_turns = history.get_turns()
                chat_history = history.chat_history
                
                logger.debug(f"previous conversations: {chat_history}")

                rewritten = query_content
                # Pass to guard agent
                if topic.llm_classified_to is None:
                    logger.debug(f"Guard Agent: {query_content}")
                    guard_agent: Agent = AgentManager().get_instance_obj("ob_dba_guard_agent")
                    output_object: OutputObject = guard_agent.run(
                        input=query_content, history=chat_history,
                    )
                    question_type = output_object.get_data("type")
                    rewritten = output_object.get_data("rewrite")
                    
                    logger.debug(f"Question type: {question_type}, rewritten: {rewritten}")

                    if question_type == "闲聊":
                        topic.llm_classified_to = Topic.Clf.Casual.value
                    elif question_type == "特性问题":
                        topic.llm_classified_to = Topic.Clf.Features.value
                    elif question_type == "诊断问题":
                        topic.llm_classified_to = Topic.Clf.Diagnostic.value

                    db.commit()

                if topic.llm_classified_to == Topic.Clf.Casual.value:
                    task.done()
                    db.commit()
                elif topic.llm_classified_to == Topic.Clf.Features.value:
                    try:
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
                    except Exception as e:
                        traceback.print_exc()
                        task.delay()
                    finally:
                        db.commit()
                elif topic.llm_classified_to == Topic.Clf.Diagnostic.value:                
                    log_uploaded = False
                    for f in files:
                        if f.file_type == UploadedFile.FileType.Archive.value and f.processed:
                            log_uploaded = True
                            break
                    try:
                        if not log_uploaded and task.task_status == task.Status.Pending.value:
                            logger.debug(f"obdiag classification agent: {rewritten}")
                            obdiag_classify_agent: Agent = AgentManager().get_instance_obj("ob_diag_classification_agent")
                            output_object: OutputObject = obdiag_classify_agent.run(input=rewritten)
                            answer = output_object.get_data("output")
                            answer += ('\n\n'+'附上敏捷诊断工具 [obdiag 使用帮助链接](https://ask.oceanbase.com/t/topic/35605619)')
                            reply_post(topic_id=topic.id, raw=answer)
                            task.processing()
                            task.delay()
                        else:
                            logger.debug("questioning agent: query content: {query_content}, chat history: {chat_history}")
                            questioning_agent: Agent = AgentManager().get_instance_obj("ob_dba_questioning_agent")
                            polished_history = list(map(lambda x: {"content": x["发言"], "type": "human" if x["角色"] == '用户' else "ai"}, chat_history))
                            output_object: OutputObject = questioning_agent.run(
                                input=query_content, 
                                chat_history=polished_history
                            )
                            complete = output_object.get_data("complete")
                            logger.debug(f"问题{"可解决" if complete else "不可解决"}")
                            if complete or chat_turns >= 3:
                                answer = doc_rag(query_content, chat_history, rewritten=rewritten)
                                reply_post(topic_id=topic.id, raw=answer)
                                task.done()
                            else:
                                questions = output_object.get_data("questions")
                                for i, q in enumerate(questions):
                                    questions[i] = f"{i + 1}. {q}"
                                
                                answer = "再向您确认几个问题:\n" + '\n'.join(questions)
                                reply_post(topic_id=topic.id, raw=answer)
                                task.delay()
                    except Exception:
                        traceback.print_exc()
                        task.delay()
                    finally:
                        db.commit()

                if debug:
                    return
        except Exception:
            traceback.print_exc()
            


if __name__ == "__main__":
    AgentUniverse().start()
    # task_worker(0, debug=True, bot_name="机器人")
    print(doc_rag("请问创建租户时 ob_compatiblity_control 这个参数是哪个社区版本开始用的"))
