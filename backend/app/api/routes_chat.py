from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.chat_repository import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)
from app.schemas.chat import (
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageCreateRequest,
)


router = APIRouter()


@router.get("/conversations", response_model=list[ConversationListResponse])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_conversations(db, current_user.id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation_detail(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation(db, current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    return conversation


@router.post(
    "/conversations",
    response_model=ConversationListResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_conversation(
    request: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_conversation(db, current_user.id, request.title)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: int,
    request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation(db, current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    return add_message(db, conversation, request.role, request.content)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation(db, current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    delete_conversation(db, conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
