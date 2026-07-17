from app.models.chat import ChatMessage
from app.core.config import settings
from app.services.chat_context_service import (
    build_conversation_context,
    build_goal_conversation_context,
)


def test_chat_context_uses_configured_limits(monkeypatch):
    messages = [
        ChatMessage(role="user", content=f"m{index}-abcdefghij")
        for index in range(5)
    ]
    monkeypatch.setattr(settings, "chat_context_max_messages", 2)
    monkeypatch.setattr(settings, "chat_context_max_message_characters", 8)

    context = build_conversation_context(messages)

    assert "m2-" not in context
    assert "m3-ab..." in context
    assert "m4-ab..." in context


def test_goal_context_uses_configured_limit(monkeypatch):
    messages = [
        ChatMessage(role="user", content=f"marker-{index:02d}-end")
        for index in range(8)
    ]
    monkeypatch.setattr(settings, "goal_context_max_messages", 5)

    context = build_goal_conversation_context(messages)

    assert "marker-02-end" not in context
    assert "marker-03-end" in context
