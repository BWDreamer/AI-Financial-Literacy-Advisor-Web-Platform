from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.memory_repository import (
    delete_memory,
    get_memory,
    list_memories,
    save_memory,
)
from app.schemas.memory import (
    MemoryExportResponse,
    MemoryRequest,
    MemoryResponse,
)


router = APIRouter()


@router.get("", response_model=list[MemoryResponse])
def get_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_memories(db, current_user.id)


@router.get("/export", response_model=MemoryExportResponse)
def export_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "generated_at": datetime.now(timezone.utc),
        "memories": list_memories(db, current_user.id),
    }


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(
    request: MemoryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return save_memory(
        db,
        current_user.id,
        request,
        source="manual",
    )


@router.put("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: int,
    request: MemoryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = get_memory(db, current_user.id, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory was not found.")
    return save_memory(
        db,
        current_user.id,
        request,
        memory=memory,
        source=memory.source,
    )


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = get_memory(db, current_user.id, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory was not found.")
    delete_memory(db, memory)
    return Response(status_code=status.HTTP_204_NO_CONTENT)