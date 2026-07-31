from app.repositories.chat_repository import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)
from app.repositories.user_repository import create_user


def test_create_conversation_uses_default_title(db_session):
    user = create_user(
        db_session,
        email="chat@example.com",
        password_hash="hash",
    )

    conversation = create_conversation(db_session, user.id, title=None)

    assert conversation.title == "New Conversation"
    assert conversation.user_id == user.id
    assert conversation.conversation_id == conversation.id


def test_add_first_user_message_updates_default_conversation_title(db_session):
    user = create_user(
        db_session,
        email="chat-title@example.com",
        password_hash="hash",
    )
    conversation = create_conversation(db_session, user.id, title=None)

    message = add_message(
        db_session,
        conversation,
        role="user",
        content="Please help me build a budget for the next six months.",
    )

    assert message.role == "user"
    assert message.content.startswith("Please help me")
    assert conversation.title == "Please help me build a budget for the next six months."
    assert conversation.updated_at is not None


def test_add_assistant_message_does_not_replace_existing_title(db_session):
    user = create_user(
        db_session,
        email="chat-assistant@example.com",
        password_hash="hash",
    )
    conversation = create_conversation(db_session, user.id, title="Budget chat")

    add_message(db_session, conversation, role="assistant", content="Sure.")

    assert conversation.title == "Budget chat"


def test_get_list_and_delete_conversation_respects_user_ownership(db_session):
    owner = create_user(db_session, email="owner@example.com", password_hash="hash")
    other = create_user(db_session, email="other@example.com", password_hash="hash")
    conversation = create_conversation(db_session, owner.id, title="Owner chat")

    assert get_conversation(db_session, owner.id, conversation.id).id == conversation.id
    assert get_conversation(db_session, other.id, conversation.id) is None
    assert list_conversations(db_session, owner.id) == [conversation]

    delete_conversation(db_session, conversation)

    assert list_conversations(db_session, owner.id) == []
