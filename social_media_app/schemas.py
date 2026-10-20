import uuid

from pydantic import BaseModel
from fastapi_users import schemas

class PostCreate(BaseModel):
    id:int
    title: str
    content: str

class PostResponse(BaseModel):
    id:int
    title:str
    content:str

class UserRead(schemas.BaseUser[uuid.UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserCreate):
    pass

class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: str
    email: str
    content: str
    created_at: str
