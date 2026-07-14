import re
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.article import Article, ArticleLike, ArticleSave
from app.models.memory import UserMemory
from app.schemas.article import ArticleCreateRequest, ArticleSortBy, ArticleUpdateRequest


MEMORY_INTEREST_KEYWORDS = {
    "budget": ["budget", "budgeting", "spending", "cash flow"],
    "saving": ["saving", "savings", "save", "emergency fund", "cash"],
    "debt": ["debt", "loan", "mortgage", "credit card"],
    "tax": ["tax", "taxes", "deduction"],
    "superannuation": ["super", "superannuation", "retirement"],
    "investing": ["invest", "investing", "stocks", "etfs", "shares"],
    "security": ["security", "scam", "fraud", "online safety"],
}

STOPWORDS = {
    "about",
    "advisor",
    "answers",
    "avoid",
    "being",
    "currently",
    "financial",
    "finance",
    "guidance",
    "interested",
    "language",
    "learning",
    "mainly",
    "plans",
    "prefers",
    "simple",
    "their",
    "user",
    "wants",
}


def get_article(db: Session, article_id: str) -> Article | None:
    return db.query(Article).filter(Article.id == article_id).first()


def get_published_article(db: Session, article_id: str) -> Article | None:
    return (
        db.query(Article)
        .filter(Article.id == article_id, Article.status == "published")
        .first()
    )


def list_published_articles(
    db: Session,
    keyword: str | None = None,
    category: str | None = None,
    sort_by: ArticleSortBy = "latest",
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[Article], int]:
    query = db.query(Article).filter(Article.status == "published")

    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Article.title.ilike(pattern),
                Article.summary.ilike(pattern),
                Article.author_name.ilike(pattern),
                Article.source_name.ilike(pattern),
                Article.category.ilike(pattern),
            )
        )

    if category:
        query = query.filter(Article.category == category)

    total = query.count()

    if sort_by == "most_viewed":
        query = query.order_by(Article.views.desc(), Article.published_at.desc())
    elif sort_by == "most_liked":
        query = query.order_by(Article.likes.desc(), Article.published_at.desc())
    elif sort_by == "most_saved":
        query = query.order_by(Article.saves.desc(), Article.published_at.desc())
    else:
        query = query.order_by(Article.published_at.desc(), Article.created_at.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def list_featured_articles(db: Session, limit: int = 5) -> list[Article]:
    return (
        db.query(Article)
        .filter(Article.status == "published")
        .order_by(Article.published_at.desc(), Article.views.desc())
        .limit(limit)
        .all()
    )


def _keywords_from_memories(memories: list[UserMemory]) -> list[str]:
    text = " ".join(memory.fact.lower() for memory in memories)
    keywords: list[str] = []

    for grouped_keywords in MEMORY_INTEREST_KEYWORDS.values():
        if any(keyword in text for keyword in grouped_keywords):
            keywords.extend(grouped_keywords)

    words = [
        word
        for word in re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text)
        if word not in STOPWORDS
    ]
    keywords.extend(words)
    return list(dict.fromkeys(keywords))[:30]


def _article_text(article: Article) -> str:
    blocks_text = " ".join(
        str(block.get("text", ""))
        for block in (article.content_blocks or [])
        if isinstance(block, dict)
    )
    return " ".join([
        article.title or "",
        article.summary or "",
        article.category or "",
        blocks_text,
    ]).lower()


def _score_article_for_keywords(article: Article, keywords: list[str]) -> int:
    title = (article.title or "").lower()
    summary = (article.summary or "").lower()
    category = (article.category or "").lower()
    full_text = _article_text(article)
    score = 0

    for keyword in keywords:
        if keyword in category:
            score += 6
        if keyword in title:
            score += 4
        if keyword in summary:
            score += 2
        if keyword in full_text:
            score += 1

    score += min(article.views or 0, 5000) // 1000
    score += min(article.likes or 0, 500) // 100
    return score


def list_recommended_articles(db: Session, user_id: int, limit: int = 5) -> list[Article]:
    memories = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id)
        .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        .limit(20)
        .all()
    )
    keywords = _keywords_from_memories(memories)

    if not keywords:
        return list_featured_articles(db, limit)

    articles = (
        db.query(Article)
        .filter(Article.status == "published")
        .order_by(Article.published_at.desc(), Article.views.desc())
        .limit(80)
        .all()
    )
    scored_articles = [
        (article, _score_article_for_keywords(article, keywords))
        for article in articles
    ]
    recommended = [
        article
        for article, score in sorted(
            scored_articles,
            key=lambda item: (
                item[1],
                item[0].published_at or item[0].created_at,
                item[0].views or 0,
            ),
            reverse=True,
        )
        if score > 0
    ][:limit]

    return recommended or list_featured_articles(db, limit)


def list_published_categories(db: Session) -> list[str]:
    rows = (
        db.query(Article.category)
        .filter(Article.status == "published")
        .distinct()
        .order_by(Article.category.asc())
        .all()
    )
    return [row[0] for row in rows]


def create_article(db: Session, request: ArticleCreateRequest) -> Article:
    article = Article(
        id=request.id,
        title=request.title,
        summary=request.summary,
        cover_image_url=request.cover_image_url,
        author_name=request.author_name,
        source_name=request.source_name,
        category=request.category,
        status=request.status,
        published_at=request.published_at,
        content_blocks=request.content_blocks,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def update_article(db: Session, article: Article, request: ArticleUpdateRequest) -> Article:
    changes = request.model_dump(exclude_unset=True, by_alias=False)
    for field, value in changes.items():
        setattr(article, field, value)
    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article: Article) -> None:
    db.delete(article)
    db.commit()


def publish_article(db: Session, article: Article) -> Article:
    article.status = "published"
    if article.published_at is None:
        article.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


def unpublish_article(db: Session, article: Article) -> Article:
    article.status = "draft"
    db.commit()
    db.refresh(article)
    return article


def increment_article_views(db: Session, article: Article) -> Article:
    article.views = (article.views or 0) + 1
    db.commit()
    db.refresh(article)
    return article


def get_article_like(db: Session, user_id: int, article_id: str) -> ArticleLike | None:
    return (
        db.query(ArticleLike)
        .filter(ArticleLike.user_id == user_id, ArticleLike.article_id == article_id)
        .first()
    )


def get_article_save(db: Session, user_id: int, article_id: str) -> ArticleSave | None:
    return (
        db.query(ArticleSave)
        .filter(ArticleSave.user_id == user_id, ArticleSave.article_id == article_id)
        .first()
    )


def list_liked_article_ids(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(ArticleLike.article_id)
        .join(Article, Article.id == ArticleLike.article_id)
        .filter(ArticleLike.user_id == user_id, Article.status == "published")
        .order_by(ArticleLike.created_at.desc())
        .all()
    )
    return [row[0] for row in rows]


def list_saved_article_ids(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(ArticleSave.article_id)
        .join(Article, Article.id == ArticleSave.article_id)
        .filter(ArticleSave.user_id == user_id, Article.status == "published")
        .order_by(ArticleSave.created_at.desc())
        .all()
    )
    return [row[0] for row in rows]


def like_article(db: Session, user_id: int, article: Article) -> Article:
    if get_article_like(db, user_id, article.id) is None:
        db.add(ArticleLike(user_id=user_id, article_id=article.id))
        article.likes = (article.likes or 0) + 1
        db.commit()
        db.refresh(article)
    return article


def unlike_article(db: Session, user_id: int, article: Article) -> Article:
    like = get_article_like(db, user_id, article.id)
    if like is not None:
        db.delete(like)
        article.likes = max((article.likes or 0) - 1, 0)
        db.commit()
        db.refresh(article)
    return article


def save_article(db: Session, user_id: int, article: Article) -> Article:
    if get_article_save(db, user_id, article.id) is None:
        db.add(ArticleSave(user_id=user_id, article_id=article.id))
        article.saves = (article.saves or 0) + 1
        db.commit()
        db.refresh(article)
    return article


def unsave_article(db: Session, user_id: int, article: Article) -> Article:
    save = get_article_save(db, user_id, article.id)
    if save is not None:
        db.delete(save)
        article.saves = max((article.saves or 0) - 1, 0)
        db.commit()
        db.refresh(article)
    return article
