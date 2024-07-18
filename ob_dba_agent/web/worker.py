import time
import random
from ob_dba_agent.web.database import SessionLocal
from ob_dba_agent.web.schemas import Task, Post, Topic, UploadedFile
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.action.knowledge.store.document import Document
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager
from agentuniverse.agent.action.knowledge.knowledge import Knowledge
from ob_dba_agent.web.utils import reply_post

import datetime

def doc_rag(query: str, chat_history: list[dict], **kwargs) -> str:
    print("rag agent", query, chat_history)
    rewritten = kwargs.get("rewritten", query)
    knowledge: Knowledge = KnowledgeManager().get_instance_obj(
        "ob_doc_knowledge"
    )
    chunks: list[Document] = knowledge.query_knowledge(query_str=rewritten)
    documents = "\n".join([chunk.text for chunk in chunks])

    rag_agent: Agent = AgentManager().get_instance_obj("ob_rag_agent")
    output_object: OutputObject = rag_agent.run(
        input=query, 
        document_snippets=documents, 
        history=chat_history,
    )
    answer: str = output_object.get_data("output")
    # print("expressing_result:", expressing_result)
    visited = {}
    doc_list = []
    replace_from = "./oceanbase-doc"
    replace_to = "https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0"
    for c in chunks:
        if c.metadata["doc_name"] in visited:
            continue
        visited[c.metadata["doc_name"]] = True
        doc_list.append(f"- [{c.metadata["doc_name"]}]({c.metadata["doc_url"].replace(replace_from, replace_to)})")
        
    references = "\n具体信息可参考以下文档:\n" + "\n".join(doc_list)
    return answer + references

def task_worker(no: int, **kwargs):
    print(f"Task worker {no} started")
    debug = kwargs.get("debug", False)
    bot_name = kwargs.get("bot_name", "序风")
    while True:
        with SessionLocal() as db:
            preds = [Task.task_status.in_(Task.Status.Pending.value, Task.Status.Processing.value), Task.task_type == "topic"]
            if not debug:
                preds.append(Task.triggered_at <= datetime.datetime.now())
            task: Task | None = (
                db.query(Task)
                .filter(*preds)
                .first()
            )
            if task is None:
                print(f"Task worker {no} waiting for task to be triggered")
                time.sleep(random.randrange(10, 20))
                continue
            
            if task.event == 'topic_destroyed':
                topic: Topic | None = (
                    db.query(Topic).where(Topic.id == task.topic_id).first()
                )
                if topic is not None:
                    db.delete(topic)

                task.task_status = task.Status.Done.value
                db.commit()
                continue
            
            def delay_task():
                task.triggered_at = datetime.datetime.now() + datetime.timedelta(minutes=random.randrange(10, 20))
                db.commit()

            topic: Topic | None = (
                db.query(Topic).where(Topic.id == task.topic_id).first()
            )
            if topic is None:
                print(f"Task worker {no} failed to find topic {task.topic_id}")
                if task.task_status == task.Status.Pending.value:
                    task.task_status = task.Status.Processing.value
                    delay_task()
                elif task.task_status == task.Status.Processing.value:
                    task.task_status = task.Status.Failed.value
                    db.commit()
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
                print(f"Topic {topic.id} has no posts, rescheduling task")
                delay_task()
                continue

            if posts[-1].username == bot_name:
                # User has not replied
                print(f"User has not replied topic {topic.id} yet, rescheduling task")
                delay_task()
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
                    post_extra_content[f.post_id] = f.content

            chat_history = []
            for p in posts:
                if p.username == bot_name:
                    chat_history.append(
                        {
                            "发言": p.raw,
                            "角色": "机器人",
                        }
                    )
                else:
                    chat_history.append(
                        {
                            "发言": p.raw + "\n" + post_extra_content[p.id],
                            "角色": "用户",
                        }
                    )

            chat_history[0]["发言"] = topic.title + "\n" + chat_history[0]["发言"]
            
            print(chat_history)
            
            query_content = chat_history.pop()
                        
            rewritten = query_content
            # Pass to guard agent
            if topic.llm_classified_to == "":
                print(f"Guard Agent: {query_content}")
                guard_agent: Agent = AgentManager().get_instance_obj("ob_dba_guard_agent")
                output_object: OutputObject = guard_agent.run(
                    input=query_content, history=chat_history,
                )
                question_type = output_object.get_data("type")
                rewritten = output_object.get_data("rewrite")
                
                print(f"Question type: {question_type}, rewritten: {rewritten}")

                if question_type == "闲聊":
                    topic.llm_classified_to = Topic.Clf.Casual.value
                elif question_type == "特性问题":
                    topic.llm_classified_to = Topic.Clf.Features.value
                elif question_type == "诊断问题":
                    topic.llm_classified_to = Topic.Clf.Diagnostic.value

                db.commit()

            if topic.llm_classified_to == Topic.Clf.Casual.value:
                task.task_status = task.Status.Done.value
                db.commit()
            elif topic.llm_classified_to == Topic.Clf.Features.value:
                # RAG here
                answer = doc_rag(query_content, chat_history, rewritten=rewritten)
                print(answer)
                try:
                    reply_post(topic_id=topic.id, raw=answer)
                    if len(chat_history) > 2:
                        # At most reply two posts
                        task.task_status = task.Status.Done.value
                    else:
                        task.task_status = task.Status.Failed.value
                    db.commit()
                except Exception as e:
                    print(e)
                    # task.task_status = "failed"
                    task.triggered_at = datetime.datetime.now() + datetime.timedelta(minutes=1)
                    db.commit()
            elif topic.llm_classified_to == Topic.Clf.Diagnostic.value:                
                log_uploaded = False
                for f in files:
                    if f.file_type == UploadedFile.FileType.Archive.value and f.processed:
                        log_uploaded = True
                        break
                try:
                    if not log_uploaded:
                        print("obdiag classification agent: ", rewritten)
                        obdiag_classify_agent: Agent = AgentManager().get_instance_obj("ob_diag_classification_agent")
                        output_object: OutputObject = obdiag_classify_agent.run(input=rewritten)
                        answer = output_object.get_data("output")
                        reply_post(topic_id=topic.id, raw=answer)
                        task.task_status = task.Status.Failed.value
                        task.triggered_at = datetime.datetime.now() + datetime.timedelta(minutes=1)
                        print(answer)
                    else:
                        print("questioning agent: ", query_content, chat_history)
                        questioning_agent: Agent = AgentManager().get_instance_obj("ob_dba_questioning_agent")
                        polished_history = list(map(lambda x: {"content": x["发言"], "type": "human" if x["角色"] == '用户' else "ai"}, chat_history))
                        output_object: OutputObject = questioning_agent.run(
                            input=query_content, 
                            chat_history=polished_history
                        )
                        complete = output_object.get_data("complete")
                        print("问题", "可解决" if complete else "不可解决")
                        if complete:
                            answer = doc_rag(query_content, chat_history, rewritten=rewritten)
                            print(answer)
                            reply_post(topic_id=topic.id, raw=answer)
                            task.task_status = task.Status.Done.value
                        else:
                            questions = output_object.get_data("questions")
                            answer = '\n'.join(questions)
                            reply_post(topic_id=topic.id, raw=answer)
                            print(answer)
                            task.task_status = task.Status.Failed.value
                            task.triggered_at = datetime.datetime.now() + datetime.timedelta(minutes=1)
                    db.commit()
                except Exception as e:
                    print(e)
                    # task.task_status = "failed"
                    task.triggered_at = datetime.datetime.now() + datetime.timedelta(minutes=1)
                    db.commit()

            if debug:
                return


if __name__ == "__main__":
    AgentUniverse().start()
    task_worker(0, debug=True, bot_name="机器人")
