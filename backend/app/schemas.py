from datetime import datetime
from pydantic import BaseModel, Field

class MaterialFileOut(BaseModel):
    id: int
    filename: str
    size: int
    mime_type: str
    url: str

class MaterialOut(BaseModel):
    id: int
    title: str
    description: str
    discipline: str
    institute: str
    course: int | None
    semester: int | None
    teacher: str
    type: str
    tags: list[str]
    score: int
    views: int
    downloads: int
    created_at: datetime
    files: list[MaterialFileOut] = []

class MaterialListOut(BaseModel):
    id: int
    title: str
    discipline: str
    type: str
    tags: list[str]
    score: int
    created_at: datetime

class VoteIn(BaseModel):
    value: int = Field(ge=-1, le=1)

class SearchResponse(BaseModel):
    items: list[MaterialListOut]
    total: int
    page: int
    page_size: int


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1)

class PostOut(BaseModel):
    id: int
    content: str
    created_at: datetime

class ThreadCreate(BaseModel):
    title: str = Field(..., max_length=300)
    category: str = "free"
    first_post: str = Field("", description="Текст первого сообщения")

class ThreadOut(BaseModel):
    id: int
    title: str
    category: str
    created_at: datetime
    updated_at: datetime
    posts: list[PostOut] = []