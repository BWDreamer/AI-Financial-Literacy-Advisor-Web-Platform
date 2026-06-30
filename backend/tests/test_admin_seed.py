from app.core.security import hash_password, verify_password
from app.models.user import User
from app.services.admin_service import create_admin_user


def test_create_admin_user_is_hashed_and_idempotent(db_session):
    user, result = create_admin_user(
        db_session,
        "seed-admin@example.com",
        "Password123",
        "Demo Admin",
    )
    assert result == "created"
    assert user.role == "admin"
    assert user.password_hash != "Password123"
    assert verify_password("Password123", user.password_hash)

    repeated_user, repeated_result = create_admin_user(
        db_session,
        "seed-admin@example.com",
        "DifferentPassword123",
        "Changed Name",
    )
    assert repeated_result == "already_exists"
    assert repeated_user.id == user.id
    assert db_session.query(User).filter(
        User.email == "seed-admin@example.com"
    ).count() == 1
    assert verify_password("Password123", repeated_user.password_hash)


def test_existing_user_can_be_upgraded_to_admin(db_session):
    user = User(
        email="upgrade@example.com",
        username="regular-user",
        password_hash=hash_password("OldPassword123"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()

    upgraded, result = create_admin_user(
        db_session,
        "upgrade@example.com",
        "NewPassword123",
        "Upgraded Admin",
    )
    assert result == "upgraded"
    assert upgraded.role == "admin"
    assert upgraded.username == "Upgraded Admin"
    assert verify_password("NewPassword123", upgraded.password_hash)


def test_seeded_admin_can_login_and_access_admin_api(client, db_session):
    create_admin_user(
        db_session,
        "login-admin@example.com",
        "Password123",
        "Login Admin",
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "login-admin@example.com", "password": "Password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "admin"
    assert client.get("/api/admin/users", headers=headers).status_code == 200
