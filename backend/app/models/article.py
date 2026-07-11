from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(String(100), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    cover_image_url = Column(Text, nullable=True)
    author_name = Column(String(100), nullable=False)
    source_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    views = Column(Integer, nullable=False, default=0)
    likes = Column(Integer, nullable=False, default=0)
    saves = Column(Integer, nullable=False, default=0)
    content_blocks = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ArticleLike(Base):
    __tablename__ = "article_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_article_likes_user_article"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(String(100), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class ArticleSave(Base):
    __tablename__ = "article_saves"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_article_saves_user_article"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(String(100), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
