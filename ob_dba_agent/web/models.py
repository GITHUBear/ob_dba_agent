from datetime import datetime
from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str
    name: str


class Topic(BaseModel):
    """
    Topic: 论坛帖子
    """

    id: int
    title: str
    posts_count: int
    created_at: datetime
    last_posted_at: datetime
    category_id: int
    created_by: User
    last_poster: User
    reply_count: int
    like_count: int


class Post(BaseModel):
    """
    Post: 论坛回复，包括帖子第一条回复
    """

    id: int
    user_id: int
    username: str
    category_slug: str
    post_number: int
    post_type: int
    topic_id: int
    created_at: datetime
    raw: str
    cooked: str


class Solved(Post):
    """
    Solved: 帖子解决方案
    """

    solved_type: str


class Like(BaseModel):
    """
    Like: 点赞
    """

    post: Post
    user: User


class ForumEvent(BaseModel):
    """
    ForumEvent: 论坛事件
    """

    topic: Topic | None = None
    post: Post | None = None
    solved: Solved | None = None
    like: Like | None = None
