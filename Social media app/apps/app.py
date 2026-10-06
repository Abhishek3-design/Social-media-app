from fastapi import (
    FastAPI,
    HTTPException,
    File,
    UploadFile,
    Form,
    Depends,
)

from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import shutil
import os
import uuid
import tempfile


# ============================================================
# SCHEMAS
# ============================================================

from apps.schemas import (
    PostCreate,
    PostResponse,
    UserRead,
    UserCreate,
    UserUpdate,
    CommentCreate,
)


# ============================================================
# DATABASE
# ============================================================

from apps.db import (
    Post,
    Like,
    Comment,
    User,
    create_db_and_tables,
    get_async_session,
)


# ============================================================
# IMAGEKIT
# ============================================================

from apps.image import imageKit


# ============================================================
# AUTHENTICATION
# ============================================================

from apps.users import (
    auth_backend,
    current_active_user,
    fastapi_users,
)


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    await create_db_and_tables()

    yield


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    lifespan=lifespan
)


# ============================================================
# FASTAPI USERS ROUTES
# ============================================================

app.include_router(
    fastapi_users.get_auth_router(
        auth_backend
    ),
    prefix="/auth/jwt",
    tags=["auth"],
)


app.include_router(
    fastapi_users.get_register_router(
        UserRead,
        UserCreate,
    ),
    prefix="/register",
    tags=["auth"],
)


app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)


app.include_router(
    fastapi_users.get_verify_router(
        UserRead
    ),
    prefix="/auth",
    tags=["auth"],
)


app.include_router(
    fastapi_users.get_users_router(
        UserRead,
        UserUpdate,
    ),
    prefix="/users",
    tags=["users"],
)


# ============================================================
# UPLOAD POST
# ============================================================

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):

    temp_file_path = None

    try:

        # ----------------------------------------------------
        # File extension
        # ----------------------------------------------------

        suffix = os.path.splitext(
            file.filename or ""
        )[1]


        # ----------------------------------------------------
        # Save file temporarily
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_file_path = temp_file.name

            shutil.copyfileobj(
                file.file,
                temp_file,
            )


        # ----------------------------------------------------
        # Upload to ImageKit
        # ----------------------------------------------------

        with open(
            temp_file_path,
            "rb",
        ) as f:

            upload_result = imageKit.files.upload(
                file=f,
                file_name=file.filename,
                use_unique_file_name=True,
                tags=["backend-upload"],
            )


        # ----------------------------------------------------
        # Determine file type
        # ----------------------------------------------------

        if (
            file.content_type
            and file.content_type.startswith("video/")
        ):

            file_type = "video"

        else:

            file_type = "image"


        # ----------------------------------------------------
        # Create database post
        # ----------------------------------------------------

        post = Post(
            user_id=user.id,
            caption=caption,
            url=upload_result.url,
            file_type=file_type,
            file_name=upload_result.name,
        )


        session.add(post)

        await session.commit()

        await session.refresh(post)


        return {
            "success": True,
            "id": str(post.id),
            "message": "Post uploaded successfully",
        }


    except HTTPException:
        raise


    except Exception as e:

        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


    finally:

        if (
            temp_file_path
            and os.path.exists(temp_file_path)
        ):

            os.remove(temp_file_path)

        file.file.close()


# ============================================================
# GET FEED
# ============================================================

@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(
        current_active_user
    ),
):

    try:

        # ----------------------------------------------------
        # Get posts
        # ----------------------------------------------------

        result = await session.execute(
            select(Post)
            .order_by(
                Post.created_at.desc()
            )
        )

        posts = result.scalars().all()


        # ----------------------------------------------------
        # Get all users
        # ----------------------------------------------------

        result = await session.execute(
            select(User)
        )

        users = result.scalars().all()


        user_dict = {
            u.id: u.email
            for u in users
        }


        posts_data = []


        # ====================================================
        # PROCESS POSTS
        # ====================================================

        for post in posts:


            # ------------------------------------------------
            # Get likes
            # ------------------------------------------------

            like_result = await session.execute(
                select(Like)
                .where(
                    Like.post_id == post.id
                )
            )

            likes = like_result.scalars().all()


            likes_count = len(likes)


            # ------------------------------------------------
            # Check current user's like
            # ------------------------------------------------

            liked_by_me = any(
                like.user_id == user.id
                for like in likes
            )


            # ------------------------------------------------
            # Post data
            # ------------------------------------------------

            posts_data.append({

                "id": str(
                    post.id
                ),

                "user_id": str(
                    post.user_id
                ),

                "caption": post.caption,

                "url": post.url,

                "file_type": post.file_type,

                "file_name": post.file_name,

                "created_at": (
                    post.created_at.isoformat()
                    if post.created_at
                    else ""
                ),

                "is_owner": (
                    post.user_id == user.id
                ),

                "email": user_dict.get(
                    post.user_id,
                    "Unknown",
                ),

                "liked_by_me": liked_by_me,

                "likes_count": likes_count,
            })


        return {
            "posts": posts_data
        }


    except Exception as e:

        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ============================================================
# DELETE POST
# ============================================================

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(
        current_active_user
    ),
):

    try:

        post_uuid = uuid.UUID(
            post_id
        )


    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid post ID",
        )


    result = await session.execute(
        select(Post)
        .where(
            Post.id == post_uuid
        )
    )

    post = result.scalars().first()


    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )


    # --------------------------------------------------------
    # Check ownership
    # --------------------------------------------------------

    if post.user_id != user.id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You don't have permission "
                "to delete this post"
            ),
        )


    await session.delete(post)

    await session.commit()


    return {
        "success": True,
        "message": "Post deleted successfully",
    }


# ============================================================
# LIKE POST
# ============================================================

@app.post("/posts/{post_id}/like")
async def like_post(
    post_id: str,
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(
        current_active_user
    ),
):

    try:

        post_uuid = uuid.UUID(
            post_id
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid post ID",
        )


    # --------------------------------------------------------
    # Check post
    # --------------------------------------------------------

    result = await session.execute(
        select(Post)
        .where(
            Post.id == post_uuid
        )
    )

    post = result.scalars().first()


    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )


    # --------------------------------------------------------
    # Check existing like
    # --------------------------------------------------------

    result = await session.execute(
        select(Like)
        .where(
            Like.post_id == post_uuid,
            Like.user_id == user.id,
        )
    )

    existing_like = result.scalars().first()


    if existing_like:

        return {
            "success": True,
            "message": "Post already liked",
        }


    # --------------------------------------------------------
    # Create like
    # --------------------------------------------------------

    like = Like(
        user_id=user.id,
        post_id=post_uuid,
    )

    session.add(like)

    await session.commit()


    return {
        "success": True,
        "message": "Post liked",
    }


# ============================================================
# UNLIKE POST
# ============================================================

@app.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: str,
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(
        current_active_user
    ),
):

    try:

        post_uuid = uuid.UUID(
            post_id
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid post ID",
        )


    result = await session.execute(
        select(Like)
        .where(
            Like.post_id == post_uuid,
            Like.user_id == user.id,
        )
    )

    like = result.scalars().first()


    if not like:

        raise HTTPException(
            status_code=404,
            detail="Like not found",
        )


    await session.delete(
        like
    )

    await session.commit()


    return {
        "success": True,
        "message": "Post unliked",
    }


# ============================================================
# GET COMMENTS
# ============================================================

@app.get("/posts/{post_id}/comments")
async def get_comments(
    post_id: str,
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(
        current_active_user
    ),
):

    try:

        post_uuid = uuid.UUID(
            post_id
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid post ID",
        )


    # --------------------------------------------------------
    # Check post exists
    # --------------------------------------------------------

    result = await session.execute(
        select(Post)
        .where(
            Post.id == post_uuid
        )
    )

    post = result.scalars().first()


    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )


    # --------------------------------------------------------
    # Get comments
    # --------------------------------------------------------

    result = await session.execute(
        select(Comment)
        .where(
            Comment.post_id == post_uuid
        )
        .order_by(
            Comment.created_at.asc()
        )
    )

    comments = result.scalars().all()


    # --------------------------------------------------------
    # Get users
    # --------------------------------------------------------

    result = await session.execute(
        select(User)
    )

    users = result.scalars().all()


    user_dict = {
        u.id: u.email
        for u in users
    }


    comments_data = []


    # --------------------------------------------------------
    # Build comments response
    # --------------------------------------------------------

    for comment in comments:

        comments_data.append({

            # IMPORTANT:
            # Streamlit needs this to determine
            # whether the current user owns the comment.

            "id": str(
                comment.id
            ),

            "user_id": str(
                comment.user_id
            ),

            "email": user_dict.get(
                comment.user_id,
                "User",
            ),

            "content": comment.content,

            "created_at": (
                comment.created_at.isoformat()
                if comment.created_at
                else ""
            ),
        })


    return {
        "comments": comments_data
    }


# ============================================================
# ADD COMMENT
# ============================================================

@app.post("/posts/{post_id}/comments")
async def add_comment(
    post_id: str,
    comment_data: CommentCreate,
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(
        current_active_user
    ),
):

    try:

        post_uuid = uuid.UUID(
            post_id
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid post ID",
        )


    # --------------------------------------------------------
    # Validate comment
    # --------------------------------------------------------

    content = comment_data.content.strip()


    if not content:

        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty",
        )


    # --------------------------------------------------------
    # Check post
    # --------------------------------------------------------

    result = await session.execute(
        select(Post)
        .where(
            Post.id == post_uuid
        )
    )

    post = result.scalars().first()


    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )


    # --------------------------------------------------------
    # Create comment
    # --------------------------------------------------------

    comment = Comment(
        user_id=user.id,
        post_id=post_uuid,
        content=content,
    )


    session.add(comment)

    await session.commit()

    await session.refresh(
        comment
    )


    return {

        "id": str(
            comment.id
        ),

        "user_id": str(
            comment.user_id
        ),

        "email": user.email,

        "content": comment.content,

        "created_at": (
            comment.created_at.isoformat()
            if comment.created_at
            else ""
        ),
    }


# ============================================================
# DELETE COMMENT
# ============================================================

@app.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(
        current_active_user
    ),
):

    try:

        comment_uuid = uuid.UUID(
            comment_id
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid comment ID",
        )


    # --------------------------------------------------------
    # Find comment
    # --------------------------------------------------------

    result = await session.execute(
        select(Comment)
        .where(
            Comment.id == comment_uuid
        )
    )

    comment = result.scalars().first()


    if not comment:

        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )


    # --------------------------------------------------------
    # Only owner can delete
    # --------------------------------------------------------

    if comment.user_id != user.id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You can only delete "
                "your own comments"
            ),
        )


    # --------------------------------------------------------
    # Delete comment
    # --------------------------------------------------------

    await session.delete(
        comment
    )

    await session.commit()


    return {
        "success": True,
        "message": "Comment deleted successfully",
    }
