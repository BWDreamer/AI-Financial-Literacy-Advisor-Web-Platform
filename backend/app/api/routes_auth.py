from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    update_avatar_url,
    update_email,
    update_password_hash,
    update_username,
    touch_last_seen,
)
from app.schemas.admin import HeartbeatResponse
from app.schemas.auth import (
    AvatarResponse,
    EmailUpdateRequest,
    PasswordUpdateRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)


router = APIRouter()


@router.get("/ping")
def ping_auth():
    return {
        "module": "auth",
        "status": "ok",
    }


@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
)
def heartbeat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return touch_last_seen(db, current_user)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: UserRegisterRequest,
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
            username=request.username,
            password_hash=hash_password(
                request.password
            ),
        )

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(
        db,
        request.email,
    )

    if user is None or not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        expires_in=(
            settings.jwt_expire_minutes * 60
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_account(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
)
def update_my_account(
    request: UserUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    return update_username(
        db=db,
        user=current_user,
        username=request.username,
    )


@router.put(
    "/email",
    response_model=UserResponse,
)
def change_my_email(
    request: EmailUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    if not verify_password(
        request.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    new_email = request.new_email.lower().strip()

    existing_user = get_user_by_email(
        db,
        new_email,
    )

    if (
        existing_user is not None
        and existing_user.id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return update_email(
        db=db,
        user=current_user,
        new_email=new_email,
    )


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def change_my_password(
    request: PasswordUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    if not verify_password(
        request.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    if verify_password(
        request.new_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new password must be different from the current password.",
        )

    update_password_hash(
        db=db,
        user=current_user,
        password_hash=hash_password(
            request.new_password
        ),
    )

    return None


@router.post(
    "/avatar",
    response_model=AvatarResponse,
)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    extension = allowed_types.get(
        file.content_type or ""
    )

    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG and WebP images are supported.",
        )

    maximum_size = (
        settings.max_upload_size_mb
        * 1024
        * 1024
    )

    content = await file.read(
        maximum_size + 1
    )

    await file.close()

    if len(content) > maximum_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Avatar must not exceed "
                f"{settings.max_upload_size_mb} MB."
            ),
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    avatar_directory = (
        Path(settings.upload_dir)
        / "avatars"
    )

    avatar_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"user_{current_user.id}_"
        f"{uuid4().hex}{extension}"
    )

    avatar_path = (
        avatar_directory
        / filename
    )

    avatar_path.write_bytes(content)

    avatar_url = (
        f"/uploads/avatars/{filename}"
    )

    update_avatar_url(
        db=db,
        user=current_user,
        avatar_url=avatar_url,
    )

    return AvatarResponse(
        avatar_url=avatar_url
    )
