import pytest

from app.core.security import verify_password
from app.repositories.user_repository import create_user, get_user_by_email
from app.schemas.admin import AdvisorySettingsUpdateRequest
from app.services.admin_service import (
    advisory_settings_payload,
    create_admin_user,
    get_advisory_settings,
    update_advisory_settings,
)


def test_create_admin_user_normalizes_email_and_name(db_session):
    user, status = create_admin_user(
        db_session,
        email=" Admin@Example.COM ",
        password="Admin12345!",
        name=" Site Admin ",
    )

    assert status == "created"
    assert user.email == "admin@example.com"
    assert user.username == "Site Admin"
    assert user.role == "admin"
    assert verify_password("Admin12345!", user.password_hash) is True


def test_create_admin_user_returns_existing_admin_without_duplicate(db_session):
    first_user, first_status = create_admin_user(
        db_session,
        email="admin@example.com",
        password="Admin12345!",
        name="Admin",
    )

    second_user, second_status = create_admin_user(
        db_session,
        email=" ADMIN@example.com ",
        password="Different123!",
        name="New Name",
    )

    assert first_status == "created"
    assert second_status == "already_exists"
    assert second_user.id == first_user.id
    assert db_session.query(type(first_user)).count() == 1


def test_create_admin_user_upgrades_existing_standard_user(db_session):
    standard_user = create_user(
        db_session,
        email="member@example.com",
        password_hash="old-hash",
        username="Member",
        role="user",
    )

    admin_user, status = create_admin_user(
        db_session,
        email="member@example.com",
        password="Admin12345!",
        name="Member Admin",
    )

    assert status == "upgraded"
    assert admin_user.id == standard_user.id
    assert admin_user.role == "admin"
    assert admin_user.username == "Member Admin"
    assert verify_password("Admin12345!", admin_user.password_hash) is True


@pytest.mark.parametrize(
    ("email", "password", "error_message"),
    [
        ("not-an-email", "Admin12345!", "ADMIN_EMAIL must be a valid email address"),
        ("admin@example.com", "short", "ADMIN_PASSWORD must contain 8 to 72 characters"),
    ],
)
def test_create_admin_user_rejects_invalid_credentials(
    db_session,
    email: str,
    password: str,
    error_message: str,
):
    with pytest.raises(ValueError, match=error_message):
        create_admin_user(db_session, email=email, password=password)


def test_advisory_settings_payload_merges_saved_topics_with_defaults():
    payload = advisory_settings_payload(
        type(
            "Settings",
            (),
            {
                "topics": [
                    {"name": "Budgeting", "enabled": False},
                    {"name": "Investing", "enabled": True},
                    {"name": "Unknown", "enabled": False},
                    {"name": "Tax", "enabled": "yes"},
                ]
            },
        )()
    )

    topics = {topic["name"]: topic["enabled"] for topic in payload["topics"]}

    assert topics["Budgeting"] is False
    assert topics["Investing"] is True
    assert topics["Tax"] is True
    assert "Unknown" not in topics


def test_update_advisory_settings_preserves_unspecified_defaults(db_session):
    updated = update_advisory_settings(
        db_session,
        AdvisorySettingsUpdateRequest(
            topics=[
                {"name": "Investing", "enabled": True},
                {"name": "Debt", "enabled": False},
            ]
        ),
    )

    topics = {topic["name"]: topic["enabled"] for topic in updated["topics"]}

    assert topics["Investing"] is True
    assert topics["Debt"] is False
    assert topics["Budgeting"] is True

    persisted = {
        topic["name"]: topic["enabled"]
        for topic in get_advisory_settings(db_session)["topics"]
    }
    assert persisted == topics
