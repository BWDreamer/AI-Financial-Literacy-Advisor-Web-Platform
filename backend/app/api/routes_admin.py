from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.models.article import ArticleLike, ArticleSave
from app.models.goal import Goal
from app.models.user import User
from app.repositories.article_repository import (
    create_article,
    delete_article,
    get_article,
    list_articles_for_admin,
    publish_article,
    unpublish_article,
    update_article,
)
from app.repositories.user_repository import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    update_admin_user,
)
from app.repositories.profile_repository import get_profile_by_user_id
from app.schemas.article import (
    AdminArticleDetailResponse,
    AdminArticlePageResponse,
    ArticleCreateRequest,
    ArticleImageUploadResponse,
    ArticleSortBy,
    ArticleStatus,
    ArticleUpdateRequest,
)
from app.schemas.admin import (
    AdvisorySettingsResponse,
    AdvisorySettingsUpdateRequest,
    AdminUserCreateRequest,
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from app.services.admin_service import (
    get_advisory_settings,
    update_advisory_settings,
)


router = APIRouter()


def require_article(db: Session, article_id: str):
    article = get_article(db, article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found.",
        )
    return article


def user_engagement_counts(db: Session, user_id: int) -> dict[str, int]:
    goals_count = db.query(func.count(Goal.id)).filter(Goal.user_id == user_id).scalar() or 0
    liked_articles_count = db.query(func.count(ArticleLike.id)).filter(ArticleLike.user_id == user_id).scalar() or 0
    saved_articles_count = db.query(func.count(ArticleSave.id)).filter(ArticleSave.user_id == user_id).scalar() or 0
    return {
        "goals_count": goals_count,
        "liked_articles_count": liked_articles_count,
        "saved_articles_count": saved_articles_count,
    }


def admin_user_payload(db: Session, user: User) -> dict:
    profile = get_profile_by_user_id(db, user.id)
    return {
        "id": user.id,
        "user_id": user.user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "region": profile.region if profile else None,
        "created_at": user.created_at,
        "is_online": user.is_online,
        "last_seen_at": user.last_seen_at,
        **user_engagement_counts(db, user.id),
    }


@router.get("/ping")
def ping_admin():
    return {"module": "admin", "status": "ok"}


@router.get(
    "/advisory-settings",
    response_model=AdvisorySettingsResponse,
)
def read_advisory_settings(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return get_advisory_settings(db)


@router.patch(
    "/advisory-settings",
    response_model=AdvisorySettingsResponse,
)
def patch_advisory_settings(
    request: AdvisorySettingsUpdateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return update_advisory_settings(db, request)


@router.get("/users", response_model=list[AdminUserResponse])
def get_admin_users(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [admin_user_payload(db, user) for user in list_users(db)]


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get one user and their engagement summary",
)
def get_admin_user(
    user_id: int,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User was not found.",
        )
    return admin_user_payload(db, user)


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_user(
    request: AdminUserCreateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    email = request.email.lower().strip()
    if get_user_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    try:
        return create_user(
            db=db,
            email=email,
            password_hash=hash_password(request.password),
            username=f"{request.first_name} {request.last_name}",
            first_name=request.first_name,
            last_name=request.last_name,
        )
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def edit_user(
    user_id: int,
    request: AdminUserUpdateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User was not found.",
        )

    email = None
    if request.email is not None:
        email = request.email.lower().strip()
        existing = get_user_by_email(db, email)
        if existing is not None and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

    try:
        return update_admin_user(
            db=db,
            user=user,
            first_name=request.first_name,
            last_name=request.last_name,
            email=email,
        )
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User was not found.",
        )
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own account.",
        )

    delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/articles",
    response_model=AdminArticleDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_article(
    request: ArticleCreateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if get_article(db, request.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An article with this id already exists.",
        )
    return {
        **create_article(db, request).__dict__,
        "liked_by_me": False,
        "saved_by_me": False,
    }


@router.get(
    "/articles",
    response_model=AdminArticlePageResponse,
    summary="List articles in every publication state",
)
def get_admin_articles(
    keyword: str | None = Query(default=None, max_length=255),
    category: str | None = Query(default=None, max_length=50),
    article_status: ArticleStatus | None = Query(default=None, alias="status"),
    sort_by: ArticleSortBy = "latest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    items, total = list_articles_for_admin(
        db=db,
        keyword=keyword,
        category=category,
        article_status=article_status,
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


@router.get(
    "/articles/{article_id}",
    response_model=AdminArticleDetailResponse,
    summary="Get an article in any publication state",
)
def get_admin_article(
    article_id: str,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    article = require_article(db, article_id)
    return {
        **article.__dict__,
        "liked_by_me": False,
        "saved_by_me": False,
    }


@router.put("/articles/{article_id}", response_model=AdminArticleDetailResponse)
def update_admin_article(
    article_id: str,
    request: ArticleUpdateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    article = require_article(db, article_id)
    article = update_article(db, article, request)
    return {
        **article.__dict__,
        "liked_by_me": False,
        "saved_by_me": False,
    }


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_article(
    article_id: str,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    article = require_article(db, article_id)
    delete_article(db, article)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/articles/{article_id}/publish", response_model=AdminArticleDetailResponse)
def publish_admin_article(
    article_id: str,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    article = publish_article(db, require_article(db, article_id))
    return {
        **article.__dict__,
        "liked_by_me": False,
        "saved_by_me": False,
    }


@router.post("/articles/{article_id}/unpublish", response_model=AdminArticleDetailResponse)
def unpublish_admin_article(
    article_id: str,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    article = unpublish_article(db, require_article(db, article_id))
    return {
        **article.__dict__,
        "liked_by_me": False,
        "saved_by_me": False,
    }


@router.post("/articles/images", response_model=ArticleImageUploadResponse)
async def upload_admin_article_image(
    file: UploadFile = File(...),
    _admin: User = Depends(get_current_admin),
):
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    extension = allowed_types.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG and WebP images are supported.",
        )

    maximum_size = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(maximum_size + 1)
    await file.close()

    if len(content) > maximum_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image must not exceed {settings.max_upload_size_mb} MB.",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    article_directory = Path(settings.upload_dir) / "articles"
    article_directory.mkdir(parents=True, exist_ok=True)
    filename = f"article_{uuid4().hex}{extension}"
    image_path = article_directory / filename
    image_path.write_bytes(content)

    return {
        "image_url": f"/uploads/articles/{filename}",
    }
