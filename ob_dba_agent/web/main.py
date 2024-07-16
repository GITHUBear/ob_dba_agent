from agentuniverse.base.agentuniverse import AgentUniverse

# AgentUniverse().start()
from agentuniverse.agent_serve.service_manager import ServiceManager

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ob_dba_agent.web.models import *
from ob_dba_agent.web.schemas import Base
from ob_dba_agent.web.database import engine, get_db
from ob_dba_agent.web.event_handlers import *
from ob_dba_agent.web.worker import task_worker

import datetime
import os
import random
import threading


Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before the app starts
    for i in range(int(os.environ.get("WORKER_COUNT", 1))):
        threading.Thread(target=task_worker, args=(i,), daemon=True).start()
    yield
    # After the app stops
    pass


# app = FastAPI(lifespan=lifespan)
app = FastAPI()


@app.post("/repost/entry")
async def repost_entry(
    req: ForumEvent, tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    # Dispatch the request to different services
    kwargs = {}
    if req.topic:
        kwargs["topic_id"] = req.topic.id
        kwargs["task_type"] = "topic"
        # Triggered in 10 ~ 20 minutes
        kwargs["triggered_at"] = datetime.datetime.now()
        #  + datetime.timedelta(minutes=random.randrange(10, 20))
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
    return task.id


@app.get("/services")
async def get_services() -> list[str]:
    return ServiceManager().get_instance_name_list()
