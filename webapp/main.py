import os
import random
import datetime
import threading
from typing import Union
from typing_extensions import Annotated

from webapp.logger import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, BackgroundTasks, Header
from sqlalchemy.orm import Session
from webapp.models import *
from webapp.schemas import Base
from webapp.database import engine, get_db
from webapp.event_handlers import *
from webapp.worker import task_worker
from webapp.dingtalk import dingtalk_app


Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before the app starts
    for i in range(int(os.environ.get("WORKER_COUNT", 1))):
        threading.Thread(target=task_worker, args=(i,), daemon=True).start()
    yield
    # After the app stops
    pass


app = FastAPI(lifespan=lifespan)
# app = FastAPI()

app.mount("/dingtalk", dingtalk_app)


@app.post("/repost/entry")
async def repost_entry(
    req: ForumEvent,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_discourse_event: Annotated[Union[str, None], Header()] = None,
):
    # Dispatch the request to different services
    logger.info(f"Received event {x_discourse_event}, request {req}")
    kwargs = {
        "event": x_discourse_event,
    }
    if req.topic:
        kwargs["topic_id"] = req.topic.id
        kwargs["task_type"] = "topic"
        # Triggered in 10 ~ 20 minutes
        kwargs["triggered_at"] = datetime.datetime.now() + datetime.timedelta(
            seconds=random.randrange(10, 20),
            # minutes=random.randrange(10, 20),
        )
        tasks.add_task(handle_topic, db, req.topic, event=x_discourse_event)
    elif req.post:
        kwargs["topic_id"] = req.post.topic_id
        kwargs["post_id"] = req.post.id
        kwargs["task_type"] = "post"
        tasks.add_task(handle_post, db, req.post, event=x_discourse_event)
    elif req.solved:
        kwargs["topic_id"] = req.solved.id
        kwargs["task_type"] = "solved"
        tasks.add_task(handle_solved, db, req.solved, event=x_discourse_event)
    elif req.like:
        kwargs["topic_id"] = req.like.post.topic_id
        kwargs["post_id"] = req.like.post.id
        kwargs["user_id"] = req.like.user.id
        kwargs["task_type"] = "like"
        tasks.add_task(handle_like, db, req.like, event=x_discourse_event)
    elif req.ping:
        return "ok"
    task = handle_task(db, **kwargs)
    return task.id