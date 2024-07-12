from agentuniverse.base.agentuniverse import AgentUniverse

# AgentUniverse().start()
from agentuniverse.agent_serve.service_manager import ServiceManager

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ob_dba_agent.web.models import *
from ob_dba_agent.web.schemas import Base
from ob_dba_agent.web.database import engine, SessionLocal
from ob_dba_agent.web.evnet_handlers import *

import os
import time
import random
import threading


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)


def task_worker(no: int):
    print(f"Task worker {no} started")
    while True:
        time.sleep(random.randrange(10, 20))
        print(f"Task worker {no} running")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    for i in range(int(os.environ.get("WORKER_COUNT", 5))):
        threading.Thread(target=task_worker, args=(i,), daemon=True).start()
    yield
    # Clean up the ML models and release the resources


app = FastAPI(lifespan=lifespan)


@app.post("/repost/entry")
async def repost_entry(
    req: ForumEvent, tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    # Dispatch the request to different services
    kwargs = {}
    if req.topic:
        kwargs["topic_id"] = req.topic.id
        kwargs["task_type"] = "topic"
        tasks.add_task(handle_topic, db, req.topic)
    elif req.post:
        kwargs["topic_id"] = req.post.topic_id
        kwargs["post_id"] = req.post.id
        kwargs["task_type"] = "post"
        tasks.add_task(handle_post, db, req.post)
    elif req.solved:
        kwargs["topic_id"] = req.solved.id
        kwargs["task_type"] = "solved"
        tasks.add_task(handle_solved, db, req.solved)
    elif req.like:
        kwargs["topic_id"] = req.like.post.topic_id
        kwargs["post_id"] = req.like.post.id
        kwargs["user_id"] = req.like.user.id
        kwargs["task_type"] = "like"
        tasks.add_task(handle_like, db, req.like)
    task = create_task(db, **kwargs)
    tasks.add_task(handle_task, db, task)
    return task.id


@app.get("/services")
async def get_services() -> list[str]:
    return ServiceManager().get_instance_name_list()
