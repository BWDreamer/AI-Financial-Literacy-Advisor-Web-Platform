from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.repositories.user_repository import create_user, get_user_by_email
from app.schemas.auth import UserRegisterRequest, UserResponse


router = APIRouter()


@router.get("/ping")
def ping_auth():
    return {"module": "auth", "status": "ok"}


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

    existing_user = get_user_by_email(db, email)

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    try:
        user = create_user(
            db=db,
            email=email,
            password_hash=hash_password(request.password),
        )
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error

    return user