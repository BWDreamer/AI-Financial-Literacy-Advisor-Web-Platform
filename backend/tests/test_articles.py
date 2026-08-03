from datetime import datetime, timezone

from app.core.security import hash_password
from app.models.article import Article
from app.models.memory import UserMemory
from app.models.user import User


def create_user_and_headers(client, db_session, email="user@example.com", role="user"):
    user = User(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("Password123"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_article(db_session, article_id="budget-start", status="published", **overrides):
    article = Article(
        id=article_id,
        title=overrides.get("title", "Budget Basics"),
        summary=overrides.get("summary", "Learn the basics of budgeting."),
        cover_image_url=overrides.get("cover_image_url", "https://example.com/cover.jpg"),
        author_name=overrides.get("author_name", "FinanceAI Learning Team"),
        source_name=overrides.get("source_name", "Knowledge Base"),
        source_url=overrides.get("source_url", "https://example.gov.au/source"),
        category=overrides.get("category", "Budgeting"),
        status=status,
        published_at=overrides.get("published_at", datetime(2026, 7, 2, tzinfo=timezone.utc)),
        views=overrides.get("views", 10),
        likes=overrides.get("likes", 2),
        saves=overrides.get("saves", 1),
        content_blocks=overrides.get(
            "content_blocks",
            [{"type": "paragraph", "text": "Start with real spending records."}],
        ),
    )
    db_session.add(article)
    db_session.commit()
    return article


def test_article_list_filters_sorts_and_paginates(client, db_session):
    create_article(db_session, article_id="budget", title="Budget Guide", views=3, likes=1)
    create_article(db_session, article_id="tax", title="Tax Guide", category="Tax", views=9, likes=5)
    create_article(db_session, article_id="draft", title="Draft", status="draft")

    response = client.get("/api/articles?sort_by=most_viewed&page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["id"] == "tax"
    assert "contentBlocks" not in data["items"][0]

    filtered = client.get("/api/articles?category=Budgeting&keyword=budget")
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == ["budget"]


def test_article_detail_returns_content_without_incrementing_views(client, db_session):
    create_article(db_session, views=10)

    response = client.get("/api/articles/budget-start")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "budget-start"
    assert data["views"] == 10
    assert data["contentBlocks"][0]["type"] == "paragraph"
    assert data["sourceUrl"] == "https://example.gov.au/source"
    assert data["likedByMe"] is False
    assert data["savedByMe"] is False


def test_regular_user_can_increment_article_views(client, db_session):
    headers = create_user_and_headers(client, db_session)
    create_article(db_session, views=10)

    response = client.post("/api/articles/budget-start/view", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"articleId": "budget-start", "views": 11}


def test_admin_article_view_does_not_increment_views(client, db_session):
    headers = create_user_and_headers(
        client,
        db_session,
        email="admin@example.com",
        role="admin",
    )
    create_article(db_session, views=10)

    response = client.post("/api/articles/budget-start/view", headers=headers)

    assert response.status_code == 403
    assert db_session.get(Article, "budget-start").views == 10


def test_categories_and_featured_only_include_published_articles(client, db_session):
    create_article(db_session, article_id="budget", category="Budgeting")
    create_article(db_session, article_id="tax", category="Tax")
    create_article(db_session, article_id="draft", category="Security", status="draft")

    categories = client.get("/api/articles/categories")
    assert categories.status_code == 200
    assert categories.json() == ["Budgeting", "Tax"]

    featured = client.get("/api/articles/featured?limit=1")
    assert featured.status_code == 200
    assert len(featured.json()) == 1


def test_recommended_articles_use_user_memory(client, db_session):
    headers = create_user_and_headers(client, db_session)
    user = db_session.query(User).filter(User.email == "user@example.com").first()
    db_session.add(UserMemory(
        user_id=user.id,
        category="preference",
        fact="User is mainly interested in saving money and emergency fund planning.",
        source="manual",
    ))
    create_article(db_session, article_id="tax", title="Tax Guide", category="Tax", views=100)
    create_article(db_session, article_id="saving", title="Emergency Funds", category="Saving", views=1)
    db_session.commit()

    response = client.get("/api/articles/recommended?limit=2", headers=headers)

    assert response.status_code == 200
    assert response.json()[0]["id"] == "saving"


def test_like_and_save_require_authentication(client, db_session):
    create_article(db_session)

    assert client.post("/api/articles/budget-start/like").status_code == 401
    assert client.post("/api/articles/budget-start/save").status_code == 401


def test_user_can_like_unlike_save_and_unsave_article(client, db_session):
    headers = create_user_and_headers(client, db_session)
    create_article(db_session, likes=2, saves=1)

    liked = client.post("/api/articles/budget-start/like", headers=headers)
    assert liked.status_code == 200
    assert liked.json() == {"articleId": "budget-start", "liked": True, "likes": 3}

    duplicate_like = client.post("/api/articles/budget-start/like", headers=headers)
    assert duplicate_like.status_code == 200
    assert duplicate_like.json()["likes"] == 3

    saved = client.post("/api/articles/budget-start/save", headers=headers)
    assert saved.status_code == 200
    assert saved.json() == {"articleId": "budget-start", "saved": True, "saves": 2}

    detail = client.get("/api/articles/budget-start", headers=headers)
    assert detail.json()["likedByMe"] is True
    assert detail.json()["savedByMe"] is True

    assert client.get("/api/articles/me/liked", headers=headers).json() == {
        "articleIds": ["budget-start"]
    }
    assert client.get("/api/articles/me/saved", headers=headers).json() == {
        "articleIds": ["budget-start"]
    }

    unliked = client.delete("/api/articles/budget-start/like", headers=headers)
    assert unliked.status_code == 200
    assert unliked.json() == {"articleId": "budget-start", "liked": False, "likes": 2}

    unsaved = client.delete("/api/articles/budget-start/save", headers=headers)
    assert unsaved.status_code == 200
    assert unsaved.json() == {"articleId": "budget-start", "saved": False, "saves": 1}


def test_admin_can_create_publish_update_and_delete_article(client, db_session):
    headers = create_user_and_headers(
        client,
        db_session,
        email="admin@example.com",
        role="admin",
    )

    payload = {
        "id": "new-article",
        "title": "New Article",
        "summary": "Short summary",
        "coverImageUrl": "https://example.com/new.jpg",
        "authorName": "Admin",
        "sourceName": "Knowledge Base",
        "sourceUrl": "https://example.gov.au/new-article",
        "category": "Saving",
        "status": "draft",
        "contentBlocks": [{"type": "paragraph", "text": "Draft body."}],
    }

    created = client.post("/api/admin/articles", headers=headers, json=payload)
    assert created.status_code == 201
    assert created.json()["id"] == "new-article"
    assert created.json()["status"] == "draft"

    admin_list = client.get(
        "/api/admin/articles?status=draft&keyword=New",
        headers=headers,
    )
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1
    assert admin_list.json()["items"][0]["id"] == "new-article"

    admin_detail = client.get(
        "/api/admin/articles/new-article",
        headers=headers,
    )
    assert admin_detail.status_code == 200
    assert admin_detail.json()["contentBlocks"][0]["text"] == "Draft body."
    assert admin_detail.json()["sourceUrl"] == "https://example.gov.au/new-article"

    assert client.get("/api/articles/new-article").status_code == 404

    published = client.post("/api/admin/articles/new-article/publish", headers=headers)
    assert published.status_code == 200
    assert client.get("/api/articles/new-article").status_code == 200

    updated = client.put(
        "/api/admin/articles/new-article",
        headers=headers,
        json={"title": "Updated Article"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Article"

    unpublished = client.post("/api/admin/articles/new-article/unpublish", headers=headers)
    assert unpublished.status_code == 200
    assert client.get("/api/articles/new-article").status_code == 404

    deleted = client.delete("/api/admin/articles/new-article", headers=headers)
    assert deleted.status_code == 204


def test_regular_user_cannot_manage_articles(client, db_session):
    headers = create_user_and_headers(client, db_session)
    response = client.post(
        "/api/admin/articles",
        headers=headers,
        json={
            "id": "blocked",
            "title": "Blocked",
            "summary": "No",
            "authorName": "User",
            "sourceName": "Knowledge Base",
            "category": "Budgeting",
            "contentBlocks": [],
        },
    )
    assert response.status_code == 403
    assert client.get("/api/admin/articles", headers=headers).status_code == 403
