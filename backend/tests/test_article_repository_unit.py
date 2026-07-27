from datetime import datetime, timedelta, timezone

from app.models.article import Article
from app.repositories.article_repository import (
    create_article,
    delete_article,
    get_article,
    get_published_article,
    increment_article_views,
    like_article,
    list_liked_article_ids,
    list_published_articles,
    list_published_categories,
    list_saved_article_ids,
    publish_article,
    save_article,
    unlike_article,
    unsave_article,
    update_article,
)
from app.repositories.user_repository import create_user
from app.schemas.article import ArticleCreateRequest, ArticleUpdateRequest


def article_request(
    article_id: str,
    title: str = "Tax basics",
    category: str = "Tax",
    status: str = "published",
    published_at: datetime | None = None,
) -> ArticleCreateRequest:
    return ArticleCreateRequest(
        id=article_id,
        title=title,
        summary="A short summary",
        coverImageUrl="/uploads/cover.png",
        authorName="FinanceAI Learning Team",
        sourceName="Knowledge Base",
        category=category,
        status=status,
        publishedAt=published_at or datetime.now(timezone.utc),
        contentBlocks=[
            {"type": "paragraph", "text": "First paragraph"},
            {"type": "image", "src": "/uploads/article.png"},
        ],
    )


def test_create_article_persists_content_blocks_and_metadata(db_session):
    article = create_article(db_session, article_request("article-1"))

    assert article.id == "article-1"
    assert article.title == "Tax basics"
    assert article.cover_image_url == "/uploads/cover.png"
    assert article.content_blocks[0]["text"] == "First paragraph"
    assert get_article(db_session, "article-1").id == "article-1"


def test_list_published_articles_filters_and_sorts(db_session):
    older = datetime.now(timezone.utc) - timedelta(days=2)
    newer = datetime.now(timezone.utc) - timedelta(days=1)

    create_article(
        db_session,
        article_request(
            "saving-1",
            title="Saving habits",
            category="Saving",
            published_at=older,
        ),
    )
    popular = create_article(
        db_session,
        article_request(
            "saving-2",
            title="Emergency saving",
            category="Saving",
            published_at=newer,
        ),
    )
    popular.views = 50
    db_session.commit()
    create_article(
        db_session,
        article_request(
            "draft-1",
            title="Draft saving",
            category="Saving",
            status="draft",
            published_at=newer,
        ),
    )

    items, total = list_published_articles(
        db_session,
        keyword="saving",
        category="Saving",
        sort_by="most_viewed",
    )

    assert total == 2
    assert [article.id for article in items] == ["saving-2", "saving-1"]


def test_update_publish_and_delete_article(db_session):
    article = create_article(
        db_session,
        article_request("draft-article", status="draft", published_at=None),
    )

    assert get_published_article(db_session, "draft-article") is None

    updated = update_article(
        db_session,
        article,
        ArticleUpdateRequest(
            title="Updated title",
            category="Budgeting",
            contentBlocks={"type": "doc", "content": []},
        ),
    )
    assert updated.title == "Updated title"
    assert updated.category == "Budgeting"
    assert updated.content_blocks == {"type": "doc", "content": []}

    published = publish_article(db_session, updated)
    assert published.status == "published"
    assert published.published_at is not None
    assert get_published_article(db_session, "draft-article").id == "draft-article"

    delete_article(db_session, published)
    assert get_article(db_session, "draft-article") is None


def test_article_engagement_helpers_are_idempotent(db_session):
    user = create_user(
        db_session,
        email="reader@example.com",
        password_hash="hash",
    )
    article = create_article(db_session, article_request("engagement-article"))

    increment_article_views(db_session, article)
    increment_article_views(db_session, article)
    assert article.views == 2

    like_article(db_session, user.id, article)
    like_article(db_session, user.id, article)
    assert article.likes == 1
    assert list_liked_article_ids(db_session, user.id) == ["engagement-article"]

    unlike_article(db_session, user.id, article)
    unlike_article(db_session, user.id, article)
    assert article.likes == 0
    assert list_liked_article_ids(db_session, user.id) == []

    save_article(db_session, user.id, article)
    save_article(db_session, user.id, article)
    assert article.saves == 1
    assert list_saved_article_ids(db_session, user.id) == ["engagement-article"]

    unsave_article(db_session, user.id, article)
    unsave_article(db_session, user.id, article)
    assert article.saves == 0
    assert list_saved_article_ids(db_session, user.id) == []


def test_list_published_categories_ignores_drafts(db_session):
    create_article(db_session, article_request("budgeting-1", category="Budgeting"))
    create_article(db_session, article_request("tax-1", category="Tax"))
    create_article(
        db_session,
        article_request("draft-saving", category="Saving", status="draft"),
    )

    assert list_published_categories(db_session) == ["Budgeting", "Tax"]
