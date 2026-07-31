from datetime import datetime, timezone

from app.core.security import hash_password
from app.models.article import Article
from app.models.user import User


def create_user_and_headers(client, db_session, email: str, role: str = "user"):
    user = User(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("Password123"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    return user, {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_article(db_session, article_id: str = "admin-boundary-article") -> None:
    db_session.add(
        Article(
            id=article_id,
            title="Admin Boundary Article",
            summary="Short summary.",
            cover_image_url="https://example.com/cover.jpg",
            author_name="FinanceAI Learning Team",
            source_name="Knowledge Base",
            category="Budgeting",
            status="published",
            published_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
            content_blocks=[{"type": "paragraph", "text": "Body."}],
        )
    )
    db_session.commit()


def test_admin_cannot_delete_own_account_from_user_management(client, db_session):
    admin, headers = create_user_and_headers(
        client,
        db_session,
        "self-delete-admin@example.com",
        "admin",
    )

    response = client.delete(f"/api/admin/users/{admin.id}", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Administrators cannot delete their own account."
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_admin_user_update_rejects_duplicate_email(client, db_session):
    _, admin_headers = create_user_and_headers(
        client,
        db_session,
        "email-admin@example.com",
        "admin",
    )
    first_user, _ = create_user_and_headers(
        client,
        db_session,
        "first-user@example.com",
    )
    create_user_and_headers(client, db_session, "second-user@example.com")

    response = client.patch(
        f"/api/admin/users/{first_user.id}",
        headers=admin_headers,
        json={"email": "second-user@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists."


def test_admin_user_update_returns_not_found_for_missing_user(client, db_session):
    _, admin_headers = create_user_and_headers(
        client,
        db_session,
        "missing-user-admin@example.com",
        "admin",
    )

    response = client.patch(
        "/api/admin/users/99999",
        headers=admin_headers,
        json={"first_name": "Missing"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User was not found."


def test_regular_user_cannot_manage_admin_articles(client, db_session):
    _, headers = create_user_and_headers(
        client,
        db_session,
        "article-manager-user@example.com",
    )
    create_article(db_session)
    article_payload = {
        "id": "blocked-article",
        "title": "Blocked",
        "summary": "Regular users cannot create this.",
        "authorName": "User",
        "sourceName": "Knowledge Base",
        "category": "Budgeting",
        "contentBlocks": [],
    }

    assert client.post(
        "/api/admin/articles",
        headers=headers,
        json=article_payload,
    ).status_code == 403
    assert client.put(
        "/api/admin/articles/admin-boundary-article",
        headers=headers,
        json={"title": "Blocked update"},
    ).status_code == 403
    assert client.post(
        "/api/admin/articles/admin-boundary-article/publish",
        headers=headers,
    ).status_code == 403
    assert client.post(
        "/api/admin/articles/admin-boundary-article/unpublish",
        headers=headers,
    ).status_code == 403
    assert client.delete(
        "/api/admin/articles/admin-boundary-article",
        headers=headers,
    ).status_code == 403
    assert client.post(
        "/api/admin/articles/images",
        headers=headers,
        files={"file": ("cover.png", b"png", "image/png")},
    ).status_code == 403
