from ob_dba_agent.web.models import Topic, Post, Solved, Like
import ob_dba_agent.web.schemas as schemas
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def create_task(
    db: Session,
    task_type: str,
    **kwargs,
) -> schemas.Task:
    new_task = schemas.Task(
        task_type=task_type,
    )
    if "triggered_at" in kwargs:
        new_task.triggered_at = kwargs["triggered_at"]
    if "topic_id" in kwargs:
        new_task.topic_id = kwargs["topic_id"]
    if "post_id" in kwargs:
        new_task.post_id = kwargs["post_id"]
    if "user_id" in kwargs:
        new_task.user_id = kwargs["user_id"]

    try:
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
    except Exception as e:
        logger.error(e)
        logger.error("Failed to add task to database")
    return new_task


async def handle_topic(db: Session, topic: Topic):
    print("topic", topic)
    new_topic = schemas.Topic(
        id=topic.id,
        title=topic.title,
        category_id=topic.category_id,
        created_at=topic.created_at,
        last_posted_at=topic.last_posted_at,
    )
    try:
        db.add(new_topic)
        db.commit()
        db.refresh(new_topic)
    except:
        logger.error("Failed to add topic to database")
    return new_topic


async def handle_post(db: Session, post: Post):
    print("post", post)
    return post


async def handle_solved(db: Session, solved: Solved):
    print("solved", solved)
    return solved


async def handle_like(db: Session, like: Like):
    print("like", like)
    return like


async def handle_task(db: Session, task: schemas.Task):
    print("task", task)
    return task
