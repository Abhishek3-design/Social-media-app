from collections.abc import AsyncGenerator
import uuid
from datetime import datetime

from fastapi import Depends
from fastapi_users.db import (
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyUserDatabase,
)

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Uuid,
    UniqueConstraint,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from sqlalchemy.orm import DeclarativeBase, relationship


DATABASE_URL = "sqlite+aiosqlite:///./test.db"


class Base(DeclarativeBase):
    pass


# =========================
# User
# =========================

class User(SQLAlchemyBaseUserTableUUID, Base):

    posts = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    likes = relationship(
        "Like",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    comments = relationship(
        "Comment",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# =========================
# Post
# =========================

class Post(Base):
    __tablename__ = "posts"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False,
    )

    caption = Column(Text)

    url = Column(
        String,
        nullable=False,
    )

    file_type = Column(
        String,
        nullable=False,
    )

    file_name = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    user = relationship(
        "User",
        back_populates="posts",
    )

    likes = relationship(
        "Like",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
    )


# =========================
# Like
# =========================

class Like(Base):
    __tablename__ = "likes"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False,
    )

    post_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("posts.id"),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    # One user can like a post only once
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "post_id",
            name="unique_user_post_like",
        ),
    )

    user = relationship(
        "User",
        back_populates="likes",
    )

    post = relationship(
        "Post",
        back_populates="likes",
    )


# =========================
# Comment
# =========================

class Comment(Base):
    __tablename__ = "comments"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False,
    )

    post_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("posts.id"),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    user = relationship(
        "User",
        back_populates="comments",
    )

    post = relationship(
        "Post",
        back_populates="comments",
    )


# =========================
# Database
# =========================

engine = create_async_engine(
    DATABASE_URL
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def create_db_and_tables():

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:

    async with async_session_maker() as session:

        yield session


async def get_user_db(
    session: AsyncSession = Depends(
        get_async_session
    ),
):

    yield SQLAlchemyUserDatabase(
        session,
        User
    )