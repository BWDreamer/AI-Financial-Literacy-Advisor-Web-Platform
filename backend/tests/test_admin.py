from datetime import datetime, timedelta, timezone

from app.core.security import hash_password, verify_password
from app.models.advisory_settings import AdvisorySettings
from app.models.user import User


def create_user_and_headers(client, db_session, role="user"):
    user = User(
        email=f"{role}@example.com",
        username=role,
        password_hash=hash_password("Password123"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "Password123"},
    )
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def test_admin_users_require_admin_role(client, db_session):
    headers = create_user_and_headers(client, db_session)
    response = client.get("/api/admin/users", headers=headers)
    assert response.status_code == 403


def test_advisory_settings_require_admin_role(client, db_session):
    headers = create_user_and_headers(client, db_session)

    assert client.get(
        "/api/admin/advisory-settings",
        headers=headers,
    ).status_code == 403
    assert client.patch(
        "/api/admin/advisory-settings",
        headers=headers,
        json={"topics": [{"name": "Budgeting", "enabled": False}]},
    ).status_code == 403


def test_admin_can_read_and_update_advisory_settings(client, db_session):
    headers = create_user_and_headers(client, db_session, role="admin")
    expected_defaults = [
        {"name": "Budgeting", "enabled": True},
        {"name": "Saving", "enabled": True},
        {"name": "Tax", "enabled": True},
        {"name": "Superannuation", "enabled": True},
        {"name": "Investing", "enabled": False},
        {"name": "Debt", "enabled": True},
    ]

    initial = client.get(
        "/api/admin/advisory-settings",
        headers=headers,
    )
    assert initial.status_code == 200
    assert initial.json() == {"topics": expected_defaults}
    assert db_session.query(AdvisorySettings).count() == 0

    updated = client.patch(
        "/api/admin/advisory-settings",
        headers=headers,
        json={
            "topics": [
                {"name": "Investing", "enabled": True},
                {"name": "Tax", "enabled": False},
            ]
        },
    )
    assert updated.status_code == 200
    expected_defaults[2]["enabled"] = False
    expected_defaults[4]["enabled"] = True
    assert updated.json() == {"topics": expected_defaults}

    persisted = client.get(
        "/api/admin/advisory-settings",
        headers=headers,
    )
    assert persisted.status_code == 200
    assert persisted.json() == updated.json()
    assert db_session.query(AdvisorySettings).count() == 1


def test_advisory_settings_reject_invalid_topics(client, db_session):
    headers = create_user_and_headers(client, db_session, role="admin")

    unknown = client.patch(
        "/api/admin/advisory-settings",
        headers=headers,
        json={"topics": [{"name": "Crypto", "enabled": True}]},
    )
    assert unknown.status_code == 422

    duplicate = client.patch(
        "/api/admin/advisory-settings",
        headers=headers,
        json={
            "topics": [
                {"name": "Saving", "enabled": True},
                {"name": "Saving", "enabled": False},
            ]
        },
    )
    assert duplicate.status_code == 422


def test_admin_user_crud(client, db_session):
    headers = create_user_and_headers(client, db_session, role="admin")

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@email.com",
            "password": "111111",
        },
    )
    assert created.status_code == 201
    user = created.json()
    assert user["user_id"].startswith("USR-")
    assert user["first_name"] == "Jane"
    assert user["is_online"] is False
    saved_user = db_session.query(User).filter(User.id == user["id"]).one()
    assert saved_user.password_hash != "111111"
    assert verify_password("111111", saved_user.password_hash)

    listed = client.get("/api/admin/users", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    detail = client.get(f"/api/admin/users/{user['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["email"] == "jane@email.com"

    updated = client.patch(
        f"/api/admin/users/{user['id']}",
        headers=headers,
        json={
            "first_name": "Jane",
            "last_name": "Jones",
            "email": "jane.jones@email.com",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["last_name"] == "Jones"

    partial_update = client.patch(
        f"/api/admin/users/{user['id']}",
        headers=headers,
        json={"first_name": "Janet"},
    )
    assert partial_update.status_code == 200
    assert partial_update.json()["first_name"] == "Janet"
    assert partial_update.json()["last_name"] == "Jones"

    deleted = client.delete(
        f"/api/admin/users/{user['id']}", headers=headers
    )
    assert deleted.status_code == 204


def test_admin_invite_rejects_duplicate_email(client, db_session):
    headers = create_user_and_headers(client, db_session, role="admin")
    payload = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@email.com",
        "password": "111111",
    }
    assert client.post(
        "/api/admin/users", headers=headers, json=payload
    ).status_code == 201
    assert client.post(
        "/api/admin/users", headers=headers, json=payload
    ).status_code == 409


def test_heartbeat_updates_online_status(client, db_session):
    headers = create_user_and_headers(client, db_session)
    response = client.post("/api/auth/heartbeat", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_online"] is True
    assert response.json()["last_seen_at"]


def test_heartbeat_requires_authentication(client):
    response = client.post("/api/auth/heartbeat")
    assert response.status_code == 401


def test_user_becomes_offline_after_five_minutes():
    user = User(
        id=1,
        email="offline@example.com",
        password_hash="not-used",
        role="user",
        last_seen_at=datetime.now(timezone.utc) - timedelta(minutes=6),
    )
    assert user.is_online is False

    user.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=4)
    assert user.is_online is True
