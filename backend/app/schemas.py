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