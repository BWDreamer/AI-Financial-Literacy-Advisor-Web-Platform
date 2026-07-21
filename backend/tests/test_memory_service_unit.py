from app.models.memory import UserMemory
from app.repositories.user_repository import create_user
from app.services.memory_service import (
    build_memory_context,
    extract_memories_from_message,
    remember_from_message,
    retrieve_relevant_memories,
)


def test_extract_memories_from_message_finds_financial_statements():
    memories = extract_memories_from_message(
        "My salary is $7000 per month. "
        "I have $12000 cash. "
        "How should I invest it?"
    )

    assert [(memory.category, memory.fact) for memory in memories] == [
        ("income", "My salary is $7000 per month"),
        ("asset", "I have $12000 cash"),
    ]


def test_extract_memories_from_message_ignores_questions_and_non_financial_text():
    memories = extract_memories_from_message(
        "How much should I save? I like coffee. We went hiking yesterday."
    )

    assert memories == []


def test_remember_from_message_stores_new_memories_only_once(db_session):
    user = create_user(
        db_session,
        email="remember@example.com",
        password_hash="hash",
    )
    message = "My rent is $2400 per month. My salary is $8000 per month."

    first = remember_from_message(db_session, user.id, message)
    second = remember_from_message(db_session, user.id, message)

    assert len(first) == 2
    assert second == []


def test_retrieve_relevant_memories_prioritizes_profile_and_marks_used(db_session):
    user = create_user(
        db_session,
        email="retrieve@example.com",
        password_hash="hash",
    )
    profile_memory = UserMemory(
        user_id=user.id,
        fact="User prefers conservative advice",
        category="preference",
        source="manual",
    )
    salary_memory = UserMemory(
        user_id=user.id,
        fact="My salary is $9000",
        category="income",
        source="chat",
    )
    db_session.add_all([salary_memory, profile_memory])
    db_session.commit()

    memories = retrieve_relevant_memories(
        db_session,
        user_id=user.id,
        message="Can you help with my salary budget?",
    )

    assert profile_memory in memories
    assert salary_memory in memories
    db_session.refresh(profile_memory)
    db_session.refresh(salary_memory)
    assert profile_memory.last_used_at is not None
    assert salary_memory.last_used_at is not None


def test_build_memory_context_formats_memories():
    context = build_memory_context(
        [
            UserMemory(category="income", fact="My salary is $9000"),
            UserMemory(category="goal", fact="I want to save $3000"),
        ]
    )

    assert context is not None
    assert "- income: My salary is $9000" in context
    assert "- goal: I want to save $3000" in context


def test_build_memory_context_returns_none_for_empty_list():
    assert build_memory_context([]) is None
