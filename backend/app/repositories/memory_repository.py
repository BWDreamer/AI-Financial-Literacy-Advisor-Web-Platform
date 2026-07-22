from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.memory import UserMemory
from app.schemas.memory import MemoryRequest


def list_memories(db: Session, user_id: int) -> list[UserMemory]:
    return (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id)
        .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        .all()
    )


def get_memory(db: Session, user_id: int, memory_id: int) -> UserMemory | None:
    return (
        db.query(UserMemory)
        .filter(UserMemory.id == memory_id, UserMemory.user_id == user_id)
        .first()
    )


def save_memory(
    db: Session,
    user_id: int,
    data: MemoryRequest,
    memory: UserMemory | None = None,
    source: str = "manual",
) -> UserMemory:
    memory = memory or UserMemory(user_id=user_id)
    memory.category = data.category
    memory.fact = data.fact
    memory.source = source
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def save_memory_replacing(
    db: Session,
    user_id: int,
    data: MemoryRequest,
    memory: UserMemory | None = None,
    duplicates: Sequence[UserMemory] = (),
    source: str = "chat",
) -> UserMemory:
    if memory is not None and memory.user_id != user_id:
        raise ValueError("Cannot replace another user's memory.")

    memory = memory or UserMemory(user_id=user_id)
    memory.category = data.category
    memory.fact = data.fact
    memory.source = source
    db.add(memory)

    for duplicate in duplicates:
        if duplicate.user_id != user_id:
            raise ValueError("Cannot delete another user's memory.")
        if duplicate.id != memory.id:
            db.delete(duplicate)

    db.commit()
    db.refresh(memory)
    return memory


def delete_memory(db: Session, memory: UserMemory) -> None:
    db.delete(memory)
    db.commit()


def find_existing_memory(
    db: Session,
    user_id: int,
    fact: str,
) -> UserMemory | None:
    normalized = " ".join(fact.strip().lower().split())
    return (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            func.lower(UserMemory.fact) == normalized,
        )
        .first()
    )


def add_memory_if_new(
    db: Session,
    user_id: int,
    fact: str,
    category: str,
    source: str = "chat",
) -> UserMemory | None:
    data = MemoryRequest(fact=fact, category=category)
    if find_existing_memory(db, user_id, data.fact) is not None:
        return None
    return save_memory(db, user_id, data, source=source)


def search_memories(
    db: Session,
    user_id: int,
    keywords: list[str],
    limit: int = 5,
) -> list[UserMemory]:
    query = db.query(UserMemory).filter(UserMemory.user_id == user_id)
    terms = [term for term in keywords if len(term) >= 3]

    if terms:
        query = query.filter(
            or_(*[UserMemory.fact.ilike(f"%{term}%") for term in terms])
        )

    return (
        query.order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        .limit(limit)
        .all()
    )


def list_memories_by_categories(
    db: Session,
    user_id: int,
    categories: tuple[str, ...],
    limit: int = 20,
) -> list[UserMemory]:
    return (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.category.in_(categories),
        )
        .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        .limit(limit)
        .all()
    )


def mark_memories_used(db: Session, memories: list[UserMemory]) -> None:
    if not memories:
        return
    now = datetime.now(timezone.utc)
    for memory in memories:
        memory.last_used_at = now
    db.commit()
