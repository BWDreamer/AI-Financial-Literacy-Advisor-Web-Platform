import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.memory import UserMemory
from app.repositories.memory_repository import (
    add_memory_if_new,
    list_memories_by_categories,
    mark_memories_used,
    search_memories,
)


FINANCIAL_KEYWORDS = {
    "asset",
    "assets",
    "budget",
    "car loan",
    "cash",
    "credit card",
    "debt",
    "expense",
    "expenses",
    "goal",
    "income",
    "loan",
    "mortgage",
    "rent",
    "salary",
    "save",
    "saving",
    "savings",
    "super",
}
STOPWORDS = {
    "about",
    "after",
    "again",
    "anything",
    "because",
    "before",
    "could",
    "should",
    "their",
    "there",
    "these",
    "think",
    "this",
    "those",
    "would",
}


@dataclass(frozen=True)
class ExtractedMemory:
    fact: str
    category: str


def _category_for(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["loan", "debt", "mortgage", "credit card"]):
        return "debt"
    if any(term in lowered for term in ["rent", "expense", "bill", "spend"]):
        return "expense"
    if any(term in lowered for term in ["salary", "income", "earn", "make"]):
        return "income"
    if any(term in lowered for term in ["save", "goal", "target", "plan to"]):
        return "goal"
    if any(term in lowered for term in ["asset", "own", "cash", "shares", "stock"]):
        return "asset"
    if any(term in lowered for term in ["prefer", "preference", "risk tolerance"]):
        return "preference"
    return "other"


def extract_memories_from_message(message: str) -> list[ExtractedMemory]:
    sentences = [part.strip() for part in re.split(r"[\n.!]+", message) if part.strip()]
    memories: list[ExtractedMemory] = []

    for sentence in sentences:
        lowered = sentence.lower()
        is_question = "?" in sentence or lowered.startswith(
            ("am ", "are ", "can ", "could ", "do ", "does ", "how ", "is ", "should ", "what ")
        )
        if is_question:
            continue

        sentence = sentence.strip(" .")
        has_user_signal = bool(
            re.search(r"\b(i|i'm|i am|my|we|our)\b", lowered)
        )
        has_money = bool(re.search(r"\$?\d[\d,]*(?:\.\d{1,2})?", sentence))
        has_financial_keyword = any(
            keyword in lowered for keyword in FINANCIAL_KEYWORDS
        )

        if not has_user_signal or not (has_money and has_financial_keyword):
            continue

        fact = sentence.strip()
        if len(fact) > 220:
            fact = f"{fact[:217].rstrip()}..."
        memories.append(
            ExtractedMemory(
                fact=fact,
                category=_category_for(fact),
            )
        )

    return memories[:3]


def remember_from_message(db: Session, user_id: int, message: str) -> list[UserMemory]:
    stored: list[UserMemory] = []
    for extracted in extract_memories_from_message(message):
        memory = add_memory_if_new(
            db,
            user_id,
            extracted.fact,
            extracted.category,
            source="chat",
        )
        if memory is not None:
            stored.append(memory)
    return stored


def _keywords_from_message(message: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", message.lower())
    keywords = [
        word
        for word in words
        if word not in STOPWORDS
    ]
    matched_financial_terms = [
        keyword
        for keyword in FINANCIAL_KEYWORDS
        if keyword in message.lower()
    ]
    return list(dict.fromkeys(matched_financial_terms + keywords))[:12]


def retrieve_relevant_memories(
    db: Session,
    user_id: int,
    message: str,
    limit: int = 12,
) -> list[UserMemory]:
    profile_memories = list_memories_by_categories(
        db,
        user_id,
        ("profile", "preference"),
        limit=limit,
    )
    relevant_memories = search_memories(
        db,
        user_id,
        _keywords_from_message(message),
        limit=limit,
    )
    memories: list[UserMemory] = []
    seen_ids: set[int] = set()
    for memory in profile_memories + relevant_memories:
        if memory.id in seen_ids:
            continue
        memories.append(memory)
        seen_ids.add(memory.id)
        if len(memories) == limit:
            break
    mark_memories_used(db, memories)
    return memories


def build_memory_context(memories: list[UserMemory]) -> str | None:
    if not memories:
        return None

    facts = "\n".join(
        f"- {memory.category}: {memory.fact}"
        for memory in memories
    )
    return (
        "Long-term user memory. These are user-managed stored facts. "
        "Use them only when relevant, and do not treat them as verified "
        "financial records:\n"
        f"{facts}"
    )
