from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    update_admin_user,
)
from app.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserResponse,
    AdminUserUpdateRequest,
)


router = APIRouter()


@router.get("/ping")
def ping_admin():
    return {"module": "admin", "status": "ok"}


@router.get("/users", response_model=list[AdminUserResponse])
def get_admin_users(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return list_users(db)


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
