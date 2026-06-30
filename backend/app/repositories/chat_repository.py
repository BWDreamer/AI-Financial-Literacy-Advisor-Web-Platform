from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chat import ChatConversation, ChatMessage


def list_conversations(db: Session, user_id: int) -> list[ChatConversation]:
    return db.query(ChatConversation).filter(
        ChatConversation.user_id == user_id
    ).order_by(ChatConversation.updated_at.desc()).all()


def get_conversation(
    db: Session,
    user_id: int,
    conversation_id: int,
) -> ChatConversation | None:
    return db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user_id,
    ).first()


def create_conversation(db: Session, user_id: int, title: str | None) -> ChatConversation:
    conversation = ChatConversation(
        user_id=user_id,
        title=title or "New Conversation",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def add_message(
    db: Session,
    conversation: ChatConversation,
    role: str,
    content: str,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
    )
    if role == "user" and conversation.title == "New Conversation":
        conversation.title = content[:60]
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def delete_conversation(db: Session, conversation: ChatConversation) -> None:
    db.delete(conversation)
    db.commit()
