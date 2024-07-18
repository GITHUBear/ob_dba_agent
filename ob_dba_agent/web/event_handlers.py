from ob_dba_agent.web.models import Topic, Post, Solved, Like
import ob_dba_agent.web.schemas as schemas
from sqlalchemy.orm import Session
import os
import logging
import subprocess
from ob_dba_agent.web.utils import FORUM_API_USERNAME

from ob_dba_agent.web.utils import (
    extract_files_from_html,
    parse_image,
    extract_bundle,
    download_file,
)
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
    if "event" in kwargs:
        new_task.event = kwargs["event"]

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
        creator_id=topic.created_by.id,
        creator_username=topic.created_by.username,
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
    new_post = schemas.Post(
        id=post.id,
        topic_id=post.topic_id,
        sender_id=post.user_id,
        username=post.username,
        created_at=post.created_at,
        raw=post.raw,
        cooked=post.cooked,
        post_number=post.post_number,
        post_type=post.post_type,
        category_slug=post.category_slug,
    )
    try:
        db.add(new_post)
    except:
        logger.error("Failed to add post to database")

    if post.username == FORUM_API_USERNAME:
        db.commit()
        db.refresh(new_post)
        return new_post

    files = extract_files_from_html(post.cooked)
    for image in files["images"]:
        file_name = os.path.basename(image)
        image_path = download_file(image, file_name)
        image_content = parse_image(image_path)
        stored_content = f"""用户上传的图片 {file_name} 使用 OCR 提取出来的文本内容如下 (用 === 包裹):
===
{image_content}
==="""
        new_file = schemas.UploadedFile(
            post_id=new_post.id,
            name=file_name,
            path=image_path,
            file_type="image",
            created_at=post.created_at,
            content=stored_content,
            processed=True,
        )
        try:
            db.add(new_file)
        except:
            logger.error("Failed to add image to database")

    for file in files["files"]:
        file_name = os.path.basename(file)
        downloaded_path = download_file(file, file_name)
        new_file = schemas.UploadedFile(
            post_id=new_post.id,
            name=file_name,
            path=downloaded_path,
            created_at=post.created_at,
        )
        file_ext = os.path.splitext(file)[1]
        if file_ext in [
            ".tar",
            ".gz",
            ".bz2",
            ".xz",
            ".zip",
        ]:
            extracted_dir = extract_bundle(downloaded_path)
            print("output_dir", extracted_dir)
            new_file.file_type = "archive"
            new_file.processed = True
            # TODO: Implement obdiag log analyze
            # subprocess.run(["obdiag", "log", "analyze", extracted_dir])
            pipe = subprocess.run(["ls", "-l", extracted_dir], capture_output=True, text=True)
            new_file.content = f"""用户上传的文件 {file_name} 解压后的目录结构和使用 obdiag 进行离线日志分析后得到的结果如下 (用 === 包裹):
===
{pipe.stdout}
==="""
        try:
            db.add(new_file)
        except:
            logger.error("Failed to add archive to database")

    try:
        db.commit()
        db.refresh(new_post)
    except:
        logger.error("Failed to commit post to database")

    return new_post


async def handle_solved(db: Session, solved: Solved):
    print("solved", solved)
    return solved


async def handle_like(db: Session, like: Like):
    print("like", like)
    return like
