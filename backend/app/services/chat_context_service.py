from collections.abc import Sequence

from app.models.chat import ChatMessage


MAX_HISTORY_MESSAGES = 16
MAX_MESSAGE_CHARACTERS = 1200


def build_conversation_context(
    messages: Sequence[ChatMessage],
) -> str | None:
    """Format recent messages so the advisor can continue a negotiation."""
    recent_messages = messages[-MAX_HISTORY_MESSAGES:]
    if not recent_messages:
        return None

    lines: list[str] = []
    for message in recent_messages:
        content = message.content.strip()
        if len(content) > MAX_MESSAGE_CHARACTERS:
            content = f"{content[:MAX_MESSAGE_CHARACTERS - 3].rstrip()}..."
        speaker = "User" if message.role == "user" else "Assistant"
        lines.append(f"{speaker}: {content}")

    return (
        "Earlier messages in this same conversation. Use them to continue "
        "the discussion, avoid repeating answered questions, and preserve "
        "agreed details:\n"
        + "\n".join(lines)
    )
