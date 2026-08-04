from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ArticleStatus = Literal["draft", "published", "archived"]
ArticleSortBy = Literal["latest", "most_viewed", "most_liked", "most_saved"]
ArticleContentBlocks = dict[str, Any] | list[dict[str, Any]]


class ArticleBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1)
    cover_image_url: str | None = Field(default=None, alias="coverImageUrl")
    author_name: str = Field(min_length=1, max_length=100, alias="authorName")
    source_name: str = Field(min_length=1, max_length=100, alias="sourceName")
    source_url: str | None = Field(default=None, max_length=2048, alias="sourceUrl")
    category: str = Field(min_length=1, max_length=50)
    published_at: datetime | None = Field(default=None, alias="publishedAt")
    content_blocks: ArticleContentBlocks = Field(default_factory=list, alias="contentBlocks")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("title", "summary", "author_name", "source_name", "category")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.lower().startswith(("https://", "http://")):
            raise ValueError("Source URL must use http or https.")
        return value


class ArticleCreateRequest(ArticleBase):
    id: str = Field(min_length=1, max_length=100)
    status: ArticleStatus = "draft"

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Article id must not be blank.")
        return value


class ArticleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, min_length=1)
    cover_image_url: str | None = Field(default=None, alias="coverImageUrl")
    author_name: str | None = Field(default=None, min_length=1, max_length=100, alias="authorName")
    source_name: str | None = Field(default=None, min_length=1, max_length=100, alias="sourceName")
    source_url: str | None = Field(default=None, max_length=2048, alias="sourceUrl")
    category: str | None = Field(default=None, min_length=1, max_length=50)
    status: ArticleStatus | None = None
    published_at: datetime | None = Field(default=None, alias="publishedAt")
    content_blocks: ArticleContentBlocks | None = Field(default=None, alias="contentBlocks")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("title", "summary", "author_name", "source_name", "category")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_optional_source_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.lower().startswith(("https://", "http://")):
            raise ValueError("Source URL must use http or https.")
        return value


class ArticleListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    title: str
    summary: str
    cover_image_url: str | None = Field(alias="coverImageUrl")
    author_name: str = Field(alias="authorName")
    source_name: str = Field(alias="sourceName")
    source_url: str | None = Field(alias="sourceUrl")
    published_at: datetime | None = Field(alias="publishedAt")
    category: str
    views: int
    likes: int
    saves: int


class ArticleDetailResponse(ArticleListItemResponse):
    content_blocks: ArticleContentBlocks = Field(alias="contentBlocks")
    liked_by_me: bool = Field(default=False, alias="likedByMe")
    saved_by_me: bool = Field(default=False, alias="savedByMe")


class AdminArticleListItemResponse(ArticleListItemResponse):
    status: ArticleStatus
    updated_at: datetime = Field(alias="updatedAt")


class AdminArticleDetailResponse(ArticleDetailResponse):
    status: ArticleStatus
    updated_at: datetime = Field(alias="updatedAt")


class AdminArticlePageResponse(BaseModel):
    items: list[AdminArticleListItemResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int

    model_config = ConfigDict(populate_by_name=True)


class ArticlePageResponse(BaseModel):
    items: list[ArticleListItemResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int

    model_config = ConfigDict(populate_by_name=True)


class ArticleEngagementIdsResponse(BaseModel):
    article_ids: list[str] = Field(alias="articleIds")

    model_config = ConfigDict(populate_by_name=True)


class ArticleLikeResponse(BaseModel):
    article_id: str = Field(alias="articleId")
    liked: bool
    likes: int

    model_config = ConfigDict(populate_by_name=True)


class ArticleSaveResponse(BaseModel):
    article_id: str = Field(alias="articleId")
    saved: bool
    saves: int

    model_config = ConfigDict(populate_by_name=True)


class ArticleViewResponse(BaseModel):
    article_id: str = Field(alias="articleId")
    views: int

    model_config = ConfigDict(populate_by_name=True)


class ArticleImageUploadResponse(BaseModel):
    image_url: str = Field(alias="imageUrl")

    model_config = ConfigDict(populate_by_name=True)
