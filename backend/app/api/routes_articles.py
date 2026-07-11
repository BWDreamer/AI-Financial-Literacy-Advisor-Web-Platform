from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.article_repository import (
    get_article_like,
    get_article_save,
    get_published_article,
    increment_article_views,
    like_article,
    list_featured_articles,
    list_liked_article_ids,
    list_published_articles,
    list_published_categories,
    list_saved_article_ids,
    save_article,
    unlike_article,
    unsave_article,
)
from app.schemas.article import (
    ArticleDetailResponse,
    ArticleEngagementIdsResponse,
    ArticleLikeResponse,
    ArticleListItemResponse,
    ArticlePageResponse,
    ArticleSaveResponse,
    ArticleSortBy,
)


router = APIRouter()


def require_published_article(db: Session, article_id: str):
    article = get_published_article(db, article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found.",
        )
    return article


@router.get("", response_model=ArticlePageResponse)
def get_articles(
    keyword: str | None = None,
    category: str | None = None,
    sort_by: ArticleSortBy = "latest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    items, total = list_published_articles(
        db=db,
        keyword=keyword,
        category=category,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/categories", response_model=list[str])
def get_article_categories(
    db: Session = Depends(get_db),
):
    return list_published_categories(db)


@router.get("/featured", response_model=list[ArticleListItemResponse])
def get_featured_articles(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return list_featured_articles(db, limit)


@router.get("/me/liked", response_model=ArticleEngagementIdsResponse)
def get_my_liked_articles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "article_ids": list_liked_article_ids(db, current_user.id),
    }


@router.get("/me/saved", response_model=ArticleEngagementIdsResponse)
def get_my_saved_articles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "article_ids": list_saved_article_ids(db, current_user.id),
    }


@router.get("/{article_id}", response_model=ArticleDetailResponse)
def get_article_detail(
    article_id: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    article = require_published_article(db, article_id)
    article = increment_article_views(db, article)
    liked_by_me = False
    saved_by_me = False

    if current_user is not None:
        liked_by_me = get_article_like(db, current_user.id, article.id) is not None
        saved_by_me = get_article_save(db, current_user.id, article.id) is not None

    return {
        **article.__dict__,
        "liked_by_me": liked_by_me,
        "saved_by_me": saved_by_me,
    }


@router.post("/{article_id}/like", response_model=ArticleLikeResponse)
def like_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = require_published_article(db, article_id)
    article = like_article(db, current_user.id, article)
    return {
        "article_id": article.id,
        "liked": True,
        "likes": article.likes,
    }


@router.delete("/{article_id}/like", response_model=ArticleLikeResponse)
def unlike_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = require_published_article(db, article_id)
    article = unlike_article(db, current_user.id, article)
    return {
        "article_id": article.id,
        "liked": False,
        "likes": article.likes,
    }


@router.post("/{article_id}/save", response_model=ArticleSaveResponse)
def save_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = require_published_article(db, article_id)
    article = save_article(db, current_user.id, article)
    return {
        "article_id": article.id,
        "saved": True,
        "saves": article.saves,
    }


@router.delete("/{article_id}/save", response_model=ArticleSaveResponse)
def unsave_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = require_published_article(db, article_id)
    article = unsave_article(db, current_user.id, article)
    return {
        "article_id": article.id,
        "saved": False,
        "saves": article.saves,
    }
