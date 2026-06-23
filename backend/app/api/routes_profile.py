from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.profile_repository import (
    get_profile_by_user_id,
    upsert_profile,
)
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpsertRequest,
)


router = APIRouter()


@router.get("/ping")
def ping_profile():
    return {
        "module": "profile",
        "status": "ok",
    }


@router.get(
    "",
    response_model=ProfileResponse,
)
def get_my_profile(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    profile = get_profile_by_user_id(
        db,
        current_user.id,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial profile has not been created.",
        )

    return profile


@router.put(
    "",
    response_model=ProfileResponse,
)
def create_or_update_my_profile(
    request: ProfileUpsertRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    return upsert_profile(
        db=db,
        user_id=current_user.id,
        profile_data=request,
    )