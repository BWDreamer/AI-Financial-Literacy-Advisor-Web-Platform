from datetime import datetime, timedelta, timezone

from app.models.user import User


def test_user_id_uses_zero_padded_database_id():
    user = User(id=7, email="user@example.com", password_hash="hash")

    assert user.user_id == "USR-0007"


def test_user_without_last_seen_is_offline():
    user = User(email="user@example.com", password_hash="hash", last_seen_at=None)

    assert user.is_online is False


def test_user_seen_within_five_minutes_is_online():
    user = User(
        email="user@example.com",
        password_hash="hash",
        last_seen_at=datetime.now(timezone.utc) - timedelta(minutes=4),
    )

    assert user.is_online is True


def test_user_seen_more_than_five_minutes_ago_is_offline():
    user = User(
        email="user@example.com",
        password_hash="hash",
        last_seen_at=datetime.now(timezone.utc) - timedelta(minutes=6),
    )

    assert user.is_online is False


def test_naive_last_seen_is_treated_as_utc():
    user = User(
        email="user@example.com",
        password_hash="hash",
        last_seen_at=datetime.utcnow() - timedelta(minutes=4),
    )

    assert user.is_online is True
