from app.repositories.profile_repository import get_profile_by_user_id, upsert_profile
from app.repositories.user_repository import create_user
from app.schemas.profile import ProfileUpsertRequest


def make_profile_request(region: str = " Australia ") -> ProfileUpsertRequest:
    return ProfileUpsertRequest(
        region=region,
        monthly_income=6000,
        fixed_expenses=2500,
        current_savings=12000,
        initial_savings_target=20000,
    )


def test_get_profile_by_user_id_returns_none_when_missing(db_session):
    assert get_profile_by_user_id(db_session, user_id=999) is None


def test_upsert_profile_creates_new_profile(db_session):
    user = create_user(
        db_session,
        email="profile@example.com",
        password_hash="hash",
    )

    profile = upsert_profile(
        db_session,
        user_id=user.id,
        profile_data=make_profile_request(),
    )

    assert profile.user_id == user.id
    assert profile.region == "Australia"
    assert profile.monthly_income == 6000
    assert profile.fixed_expenses == 2500
    assert profile.current_savings == 12000
    assert profile.initial_savings_target == 20000


def test_upsert_profile_updates_existing_profile(db_session):
    user = create_user(
        db_session,
        email="profile-update@example.com",
        password_hash="hash",
    )
    first_profile = upsert_profile(
        db_session,
        user_id=user.id,
        profile_data=make_profile_request(),
    )

    updated_profile = upsert_profile(
        db_session,
        user_id=user.id,
        profile_data=ProfileUpsertRequest(
            region="New Zealand",
            monthly_income=7000,
            fixed_expenses=3000,
            current_savings=15000,
            initial_savings_target=25000,
        ),
    )

    assert updated_profile.id == first_profile.id
    assert updated_profile.region == "New Zealand"
    assert updated_profile.monthly_income == 7000
    assert get_profile_by_user_id(db_session, user.id).id == first_profile.id
