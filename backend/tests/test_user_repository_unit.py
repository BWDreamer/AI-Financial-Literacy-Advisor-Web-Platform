from app.core.security import hash_password
from app.repositories.user_repository import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    touch_last_seen,
    update_avatar_url,
    update_email,
    update_onboarding_completed,
    update_password_hash,
    update_username,
)


def test_create_user_normalizes_email_names_and_default_username(db_session):
    user = create_user(
        db_session,
        email=" Test.User@Example.COM ",
        password_hash="hash",
        first_name=" Jane ",
        last_name=" Smith ",
    )

    assert user.email == "test.user@example.com"
    assert user.username == "test.user"
    assert user.first_name == "Jane"
    assert user.last_name == "Smith"
    assert user.role == "user"


def test_get_user_by_email_normalizes_lookup(db_session):
    user = create_user(
        db_session,
        email="lookup@example.com",
        password_hash="hash",
    )

    assert get_user_by_email(db_session, " LOOKUP@EXAMPLE.COM ").id == user.id


def test_update_user_fields_and_touch_last_seen(db_session):
    user = create_user(
        db_session,
        email="updates@example.com",
        password_hash="hash",
    )

    update_username(db_session, user, " Updated Name ")
    update_email(db_session, user, " New.Email@Example.COM ")
    update_password_hash(db_session, user, hash_password("NewPassword123!"))
    update_avatar_url(db_session, user, "/uploads/avatar.png")
    update_onboarding_completed(db_session, user, True)
    touch_last_seen(db_session, user)

    assert user.username == "Updated Name"
    assert user.email == "new.email@example.com"
    assert user.avatar_url == "/uploads/avatar.png"
    assert user.onboarding_completed is True
    assert user.last_seen_at is not None
    assert user.is_online is True


def test_list_get_and_delete_user(db_session):
    first = create_user(db_session, email="first@example.com", password_hash="hash")
    second = create_user(db_session, email="second@example.com", password_hash="hash")

    assert [user.id for user in list_users(db_session)] == [first.id, second.id]
    assert get_user_by_id(db_session, first.id).email == "first@example.com"

    delete_user(db_session, first)

    assert get_user_by_id(db_session, first.id) is None
    assert [user.id for user in list_users(db_session)] == [second.id]
