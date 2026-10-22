from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from .db import Base

class AnonymousUser(Base):
    __tablename__ = "anonymous_users"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reputation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    discipline: Mapped[str] = mapped_column(String(200), default="", index=True)
    institute: Mapped[str] = mapped_column(String(200), default="")
    course: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    teacher: Mapped[str] = mapped_column(String(200), default="")
    type: Mapped[str] = mapped_column(String(30), default="other", index=True)  # lecture|lab|test|exam|report|other
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    uploader_hash: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("anonymous_users.token_hash"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ready")  # ready|processing|failed
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_vector = mapped_column(Vector(1536), nullable=True)
    search_tsv = mapped_column(TSVECTOR, nullable=True)

    views: Mapped[int] = mapped_column(Integer, default=0)
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)  # сумма голосов

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    files: Mapped[list["MaterialFile"]] = relationship(back_populates="material", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_materials_search_tsv", "search_tsv", postgresql_using="gin"),
        Index("ix_materials_vector", "content_vector", postgresql_using="hnsw",
              postgresql_ops={"content_vector": "vector_cosine_ops"}),
    )

class MaterialFile(Base):
    __tablename__ = "material_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    storage_key: Mapped[str] = mapped_column(String(300), unique=True)
    size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    material: Mapped[Material] = relationship(back_populates="files")

class Vote(Base):
    __tablename__ = "votes"
    token_hash: Mapped[str] = mapped_column(ForeignKey("anonymous_users.token_hash"), primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # -1 or +1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Thread(Base):
    __tablename__ = "threads"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    # Категории: teachers | specific_people | solutions | free
    category: Mapped[str] = mapped_column(String(50), default="free", index=True)
    
    author_hash: Mapped[str | None] = mapped_column(ForeignKey("anonymous_users.token_hash"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    posts: Mapped[list["Post"]] = relationship(back_populates="thread", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    author_hash: Mapped[str | None] = mapped_column(ForeignKey("anonymous_users.token_hash"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[Thread] = relationship(back_populates="posts")