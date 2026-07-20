from collections.abc import Sequence

from app.core.config import settings
from app.models.chat import ChatMessage


def build_conversation_context(
    messages: Sequence[ChatMessage],
    max_messages: int | None = None,
    max_message_characters: int | None = None,
    preserve_message_end: bool = False,
) -> str | None:
    """Format recent messages so the advisor can continue a negotiation."""
    effective_max_messages = (
        max_messages
        if max_messages is not None
        else settings.chat_context_max_messages
    )
    effective_max_characters = (
        max_message_characters
        if max_message_characters is not None
        else settings.chat_context_max_message_characters
    )
    if effective_max_messages < 1 or effective_max_characters < 4:
        raise ValueError("Conversation context limits are invalid.")

    recent_messages = messages[-effective_max_messages:]
    if not recent_messages:
        return None

    lines: list[str] = []
    for message in recent_messages:
        content = message.content.strip()
        if len(content) > effective_max_characters:
            if preserve_message_end:
                content = (
                    f"...{content[-(effective_max_characters - 3):].lstrip()}"
                )
            else:
                content = (
                    f"{content[:effective_max_characters - 3].rstrip()}..."
                )
        speaker = "User" if message.role == "user" else "Assistant"
        lines.append(f"{speaker}: {content}")

    return (
        "Earlier messages in this same conversation. Use them to continue "
        "the discussion, avoid repeating answered questions, and preserve "
        "agreed details:\n"
        + "\n".join(lines)
    )


def build_goal_conversation_context(
    messages: Sequence[ChatMessage],
) -> str | None:
    """Format enough concise history to recover all six MyGoals flows."""
    return build_conversation_context(
        messages,
        max_messages=settings.goal_context_max_messages,
        max_message_characters=settings.goal_context_max_message_characters,
        preserve_message_end=True,
    )
