
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.schemas.profile import ProfileUpsertRequest


def get_profile_by_user_id(
    db: Session,
    user_id: int,
) -> UserProfile | None:
    return (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )


def upsert_profile(
    db: Session,
    user_id: int,
    profile_data: ProfileUpsertRequest,
) -> UserProfile:
    profile = get_profile_by_user_id(
        db,
        user_id,
    )

    if profile is None:
        profile = UserProfile(
            user_id=user_id,
        )
        db.add(profile)

    profile.region = profile_data.region.strip()
    profile.monthly_income = profile_data.monthly_income
    profile.fixed_expenses = profile_data.fixed_expenses
    profile.current_savings = profile_data.current_savings
    profile.initial_savings_target = (
        profile_data.initial_savings_target
    )

    db.commit()
    db.refresh(profile)

    return profile