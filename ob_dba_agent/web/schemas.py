from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship

from ob_dba_agent.web.database import Base
import datetime
from enum import Enum as stdEnum

class Topic(Base):
    __tablename__ = "topics"
    
    class Clf(stdEnum):
        Casual = "casual"
        Features = "features"
        Diagnostic = "diagnostic"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer)
    creator_username = Column(String)
    llm_classified_to = Column(String)
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
    cooked = Column(String)
    post_type = Column(String)
    category_slug = Column(String)
    post_number = Column(Integer)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    class FileType(stdEnum):
        Image = "image"
        Archive = "archive"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    post_id = Column(Integer)
    name = Column(String)
    path = Column(String)
    file_type = Column(String)
    created_at = Column(DateTime)
    content = Column(String, nullable=True)
    processed = Column(Boolean, default=False)


class Task(Base):
    __tablename__ = "tasks"
    
    class Status(stdEnum):
        Pending = "pending"
        Processing = "processing"
        Done = "done"
        Failed = "failed"
        Canceled = "canceled"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_type = Column(String)
    triggered_at = Column(DateTime, nullable=True)
    topic_id = Column(Integer, nullable=True)
    post_id = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True)
    task_status = Column(Enum("pending", "processing", "done", "failed", "canceled"), default="pending")

    def delay_processed(self, minutes: int):
        self.triggered_at = datetime.datetime.now() + datetime.timedelta(minutes=minutes)