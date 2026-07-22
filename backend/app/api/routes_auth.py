from datetime import datetime, timezone
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
    delete_user_account,
    get_user_by_email,
    update_avatar_url,
    update_email,
    update_onboarding_completed,
    update_password_hash,
    update_username,
    touch_last_seen,
)
from app.schemas.admin import HeartbeatResponse
from app.schemas.auth import (
    AccountDeleteRequest,
    AvatarResponse,
    EmailUpdateRequest,
    EmailChangeVerificationCodeRequest,
    OnboardingUpdateRequest,
    PasswordUpdateRequest,
    RegistrationVerificationCodeRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
    VerificationCodeSentResponse,
)
from app.services.email_service import EmailDeliveryError
from app.services.email_verification_service import (
    VerificationCodeCooldownError,
    VerificationCodeError,
    consume_verification_code,
    request_verification_code,
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


def _verification_code_response(
    *,
    db: Session,
    email: str,
    purpose: str,
    user_id: int | None = None,
) -> VerificationCodeSentResponse:
    try:
        expires_in = request_verification_code(
            db,
            email=email,
            purpose=purpose,
            user_id=user_id,
        )
    except VerificationCodeCooldownError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The verification email could not be sent.",
        ) from error

    return VerificationCodeSentResponse(
        message="Verification code sent.",
        expires_in=expires_in,
    )


@router.post(
    "/register/verification-code",
    response_model=VerificationCodeSentResponse,
)
def send_registration_verification_code(
    request: RegistrationVerificationCodeRequest,
    db: Session = Depends(get_db),
):
    email = request.email.lower().strip()
    if get_user_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    return _verification_code_response(
        db=db,
        email=email,
        purpose="registration",
    )


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
        consume_verification_code(
            db,
            email=email,
            purpose="registration",
            code=request.verification_code,
        )
        return create_user(
            db=db,
            email=email,
            username=request.username,
            password_hash=hash_password(
                request.password
            ),
            email_verified_at=datetime.now(timezone.utc),
        )
    except VerificationCodeError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
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


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    request: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    avatar_path = None
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/"):
        relative_path = current_user.avatar_url.removeprefix("/uploads/")
        upload_root = Path(settings.upload_dir).resolve()
        candidate = (upload_root / relative_path).resolve()
        if candidate.is_relative_to(upload_root):
            avatar_path = candidate

    delete_user_account(db, current_user)
    if avatar_path and avatar_path.is_file():
        avatar_path.unlink()

    return None


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


@router.patch(
    "/me/onboarding",
    response_model=UserResponse,
)
def update_my_onboarding_status(
    request: OnboardingUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    return update_onboarding_completed(
        db=db,
        user=current_user,
        completed=request.onboarding_completed,
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

    if new_email == current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new email must be different from the current email.",
        )

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

    try:
        consume_verification_code(
            db,
            email=new_email,
            purpose="email_change",
            code=request.verification_code,
            user_id=current_user.id,
        )
        return update_email(
            db=db,
            user=current_user,
            new_email=new_email,
            email_verified_at=datetime.now(timezone.utc),
        )
    except VerificationCodeError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error


@router.post(
    "/email/verification-code",
    response_model=VerificationCodeSentResponse,
)
def send_email_change_verification_code(
    request: EmailChangeVerificationCodeRequest,
    current_user: User = Depends(get_current_user),
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
    if new_email == current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new email must be different from the current email.",
        )
    if get_user_by_email(db, new_email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    return _verification_code_response(
        db=db,
        email=new_email,
        purpose="email_change",
        user_id=current_user.id,
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
