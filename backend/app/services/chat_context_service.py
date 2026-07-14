from collections.abc import Sequence

from app.models.chat import ChatMessage


MAX_HISTORY_MESSAGES = 16
MAX_MESSAGE_CHARACTERS = 1200
MAX_GOAL_HISTORY_MESSAGES = 96
MAX_GOAL_MESSAGE_CHARACTERS = 400


def build_conversation_context(
    messages: Sequence[ChatMessage],
    max_messages: int = MAX_HISTORY_MESSAGES,
    max_message_characters: int = MAX_MESSAGE_CHARACTERS,
    preserve_message_end: bool = False,
) -> str | None:
    """Format recent messages so the advisor can continue a negotiation."""
    recent_messages = messages[-max_messages:]
    if not recent_messages:
        return None

    lines: list[str] = []
    for message in recent_messages:
        content = message.content.strip()
        if len(content) > max_message_characters:
            if preserve_message_end:
                content = f"...{content[-(max_message_characters - 3):].lstrip()}"
            else:
                content = f"{content[:max_message_characters - 3].rstrip()}..."
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
        max_messages=MAX_GOAL_HISTORY_MESSAGES,
        max_message_characters=MAX_GOAL_MESSAGE_CHARACTERS,
        preserve_message_end=True,
    )
