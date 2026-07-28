from app.models.memory import UserMemory
from app.repositories.memory_repository import (
    add_memory_if_new,
    delete_memory,
    find_existing_memory,
    get_memory,
    list_memories,
    mark_memories_used,
    save_memory,
    search_memories,
)
from app.repositories.user_repository import create_user
from app.schemas.memory import MemoryRequest


def test_save_memory_creates_and_updates_memory(db_session):
    user = create_user(
        db_session,
        email="memory@example.com",
        password_hash="hash",
    )

    memory = save_memory(
        db_session,
        user_id=user.id,
        data=MemoryRequest(fact="I save $500 monthly", category="goal"),
        source="manual",
    )

    assert memory.fact == "I save $500 monthly"
    assert memory.category == "goal"
    assert memory.source == "manual"

    updated = save_memory(
        db_session,
        user_id=user.id,
        data=MemoryRequest(fact="I save $600 monthly", category="goal"),
        memory=memory,
    )

    assert updated.id == memory.id
    assert updated.fact == "I save $600 monthly"


def test_add_memory_if_new_prevents_duplicate_facts(db_session):
    user = create_user(
        db_session,
        email="memory-duplicate@example.com",
        password_hash="hash",
    )

    first = add_memory_if_new(
        db_session,
        user_id=user.id,
        fact="  I have a $1000 emergency fund  ",
        category="asset",
    )
    duplicate = add_memory_if_new(
        db_session,
        user_id=user.id,
        fact="I have a $1000 emergency fund",
        category="asset",
    )

    assert first is not None
    assert duplicate is None
    assert find_existing_memory(
        db_session,
        user_id=user.id,
        fact="i have a $1000 emergency fund",
    ).id == first.id


def test_list_search_mark_and_delete_memories(db_session):
    user = create_user(
        db_session,
        email="memory-list@example.com",
        password_hash="hash",
    )
    rent = save_memory(
        db_session,
        user_id=user.id,
        data=MemoryRequest(fact="My rent is $2300", category="expense"),
    )
    salary = save_memory(
        db_session,
        user_id=user.id,
        data=MemoryRequest(fact="My salary is $7000", category="income"),
    )

    assert [memory.id for memory in list_memories(db_session, user.id)] == [
        salary.id,
        rent.id,
    ]
    assert get_memory(db_session, user.id, rent.id).fact == "My rent is $2300"
    assert search_memories(db_session, user.id, ["salary"]) == [salary]

    mark_memories_used(db_session, [rent, salary])
    db_session.refresh(rent)
    db_session.refresh(salary)
    assert rent.last_used_at is not None
    assert salary.last_used_at is not None

    delete_memory(db_session, rent)
    assert get_memory(db_session, user.id, rent.id) is None


def test_search_memories_ignores_short_keywords(db_session):
    user = create_user(
        db_session,
        email="memory-short-keyword@example.com",
        password_hash="hash",
    )
    memory = save_memory(
        db_session,
        user_id=user.id,
        data=MemoryRequest(fact="My goal is to save $3000", category="goal"),
    )

    assert search_memories(db_session, user.id, ["my", "to"]) == [memory]
