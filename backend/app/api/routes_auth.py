from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
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
)
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)


router = APIRouter()


@router.get("/ping")
def ping_auth():
    return {
        "module": "auth",
        "status": "ok",
    }


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

    access_token = create_access_token(
        user.id
    )

    return TokenResponse(
        access_token=access_token,
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