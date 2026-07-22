from app.services.goal_intent_clarification_service import (
    GoalIntentClarificationStatus,
    build_goal_intent_clarification_prompt,
    emergency_fund_bare_amount_clarification,
    normalize_goal_intent_clarification,
    resolve_emergency_fund_amount_answer,
)


EMERGENCY_CONTEXT = (
    "Assistant: What Emergency Fund goal would you like to set?\n"
    "[Financial goal planning mode: category=emergency_fund]"
)


def test_bare_emergency_fund_amount_always_requires_meaning():
    clarification = emergency_fund_bare_amount_clarification(
        "AUD $1,000",
        EMERGENCY_CONTEXT,
    )

    assert clarification is not None
    assert clarification.status == GoalIntentClarificationStatus.NEEDS_CLARIFICATION
    assert clarification.clarifying_question == (
        "Is $1,000 your Emergency Fund target amount, or your essential monthly "
        "expenses?"
    )


def test_bare_amount_outside_emergency_fund_is_not_forced_into_that_meaning():
    assert emergency_fund_bare_amount_clarification("$1,000", None) is None
    assert (
        emergency_fund_bare_amount_clarification(
            "$1,000",
            "Assistant: What General Saving goal would you like to set?",
        )
        is None
    )


def test_most_recent_goal_category_controls_bare_amount_clarification():
    changed_category_context = (
        f"{EMERGENCY_CONTEXT}\n"
        "Assistant: What General Saving goal would you like to set?\n"
        "[Financial goal planning mode: category=general_saving]"
    )

    assert (
        emergency_fund_bare_amount_clarification(
            "$1,000",
            changed_category_context,
        )
        is None
    )


def test_common_clarification_answers_create_self_contained_memory_facts():
    question = (
        "Is $1,000 your Emergency Fund target amount, or your essential monthly "
        "expenses?"
    )

    target = resolve_emergency_fund_amount_answer(
        question,
        "That is my target amount.",
    )
    expenses = resolve_emergency_fund_amount_answer(
        question,
        "每月必要支出。",
    )

    assert target is not None
    assert target.status == GoalIntentClarificationStatus.RESOLVED
    assert target.memory_category == "goal"
    assert target.confirmed_fact == (
        "The user's Emergency Fund target amount is $1,000.00."
    )
    assert expenses is not None
    assert expenses.memory_category == "expense"
    assert expenses.confirmed_fact == (
        "The user's essential monthly expenses for Emergency Fund planning are "
        "$1,000.00."
    )


def test_vague_or_conflicting_answer_is_not_treated_as_confirmation():
    question = (
        "Is $1,000 your Emergency Fund target amount, or your essential monthly "
        "expenses?"
    )

    assert resolve_emergency_fund_amount_answer(question, "Yes.") is None
    assert (
        resolve_emergency_fund_amount_answer(
            question,
            "It is for my Emergency Fund goal.",
        )
        is None
    )
    assert (
        resolve_emergency_fund_amount_answer(
            question,
            "Not the target; it is my monthly expenses.",
        )
        is None
    )


def test_structured_sentence_classifier_requires_valid_confirmation_fields():
    prompt = build_goal_intent_clarification_prompt(
        EMERGENCY_CONTEXT,
        "I want it based on $1,000.",
    )
    clarification = normalize_goal_intent_clarification(
        {
            "status": "resolved",
            "clarifying_question": None,
            "confirmed_fact": "Emergency Fund target amount is $1,000.",
            "memory_category": "goal",
        }
    )
    invalid = normalize_goal_intent_clarification(
        {
            "status": "resolved",
            "clarifying_question": None,
            "confirmed_fact": None,
            "memory_category": "goal",
        }
    )

    assert "two or more plausible meanings" in prompt
    assert "Never choose between those meanings" in prompt
    assert "Never ask whether the user wants a fact saved to memory" in prompt
    assert "saves it automatically" in prompt
    assert clarification.status == GoalIntentClarificationStatus.RESOLVED
    assert invalid.status == GoalIntentClarificationStatus.CLEAR
