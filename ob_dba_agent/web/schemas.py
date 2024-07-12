from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship

from ob_dba_agent.web.database import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    category_id = Column(Integer)
    created_at = Column(DateTime)
    last_posted_at = Column(DateTime)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer)
    sender_id = Column(Integer)
    username = Column(String)
    created_at = Column(DateTime)
    raw = Column(String)
    post_type = Column(String)
    category_slug = Column(String)
    post_number = Column(Integer)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer)
    name = Column(String)
    path = Column(String)
    file_type = Column(String)
    created_at = Column(DateTime)
    content = Column(String, nullable=True)
    processed = Column(Boolean, default=False)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_type = Column(String)
    triggered_at = Column(DateTime, nullable=True)
    topic_id = Column(Integer, nullable=True)
    post_id = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True)
    task_status = Column(Enum("pending", "processing", "done", "failed", "canceled"), default="pending")
