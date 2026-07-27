import pytest
from pydantic import ValidationError

from app.schemas.article import ArticleCreateRequest, ArticleUpdateRequest


def test_article_create_request_normalizes_text_and_alias_fields():
    request = ArticleCreateRequest(
        id=" article-1 ",
        title=" Tax tips ",
        summary=" Summary ",
        coverImageUrl="/uploads/cover.png",
        authorName=" FinanceAI ",
        sourceName=" Knowledge Base ",
        category=" Tax ",
        contentBlocks={"type": "doc", "content": []},
    )

    assert request.id == "article-1"
    assert request.title == "Tax tips"
    assert request.summary == "Summary"
    assert request.cover_image_url == "/uploads/cover.png"
    assert request.author_name == "FinanceAI"
    assert request.source_name == "Knowledge Base"
    assert request.category == "Tax"
    assert request.content_blocks == {"type": "doc", "content": []}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", " "),
        ("title", " "),
        ("summary", " "),
        ("authorName", " "),
        ("sourceName", " "),
        ("category", " "),
    ],
)
def test_article_create_request_rejects_blank_required_fields(field: str, value: str):
    payload = {
        "id": "article-1",
        "title": "Title",
        "summary": "Summary",
        "authorName": "Author",
        "sourceName": "Source",
        "category": "Budgeting",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        ArticleCreateRequest(**payload)


def test_article_update_request_normalizes_optional_fields():
    request = ArticleUpdateRequest(
        title=" New title ",
        summary=" New summary ",
        authorName=" Author ",
        sourceName=" Source ",
        category=" Saving ",
        contentBlocks=[{"type": "paragraph", "text": "Body"}],
    )

    assert request.title == "New title"
    assert request.summary == "New summary"
    assert request.author_name == "Author"
    assert request.source_name == "Source"
    assert request.category == "Saving"
    assert request.content_blocks == [{"type": "paragraph", "text": "Body"}]
