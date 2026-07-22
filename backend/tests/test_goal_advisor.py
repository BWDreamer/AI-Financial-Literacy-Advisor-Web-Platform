import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.models.goal import Goal
from app.services.goal_service import analyse_goal


GOAL_REVIEW_MESSAGE_PREFIX = "[FinanceAI goal review card:v1]"
GOAL_REVIEW_MESSAGE_SUFFIX = "[/FinanceAI goal review card]"
MONEY = Decimal("0.01")


def _decimal_text(value: Any) -> str:
    return format(
        Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP),
        "f",
    )


def _priority_label(value: int) -> str:
    if value <= 2:
        return "High"
    if value >= 4:
        return "Low"
    return "Medium"


def goal_review_payload(goal: Goal) -> dict[str, Any]:
    analysis = analyse_goal(goal)
    projected = analysis["projected_completion_date"]
    return {
        "kind": "goal_review",
        "version": 1,
        "goal_id": goal.id,
        "name": goal.name,
        "category": goal.category,
        "target_amount": _decimal_text(goal.target_amount),
        "current_amount": _decimal_text(goal.current_amount),
        "monthly_contribution": _decimal_text(goal.monthly_contribution),
        "target_date": goal.target_date.isoformat(),
        "priority": _priority_label(goal.priority),
        "status": analysis["status"],
        "progress_percentage": _decimal_text(
            analysis["progress_percentage"]
        ),
        "required_monthly": _decimal_text(analysis["required_monthly"]),
        "monthly_difference": _decimal_text(
            analysis["monthly_difference"]
        ),
        "months_remaining": analysis["months_remaining"],
        "projected_completion_date": (
            projected.isoformat() if projected is not None else None
        ),
        "category_details": goal.category_details or {},
    }


def build_goal_review_message(goal: Goal) -> str:
    payload = json.dumps(
        goal_review_payload(goal),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )
    return "\n".join(
        [
            GOAL_REVIEW_MESSAGE_PREFIX,
            payload,
            GOAL_REVIEW_MESSAGE_SUFFIX,
        ]
    )


def build_goal_review_context(goal: Goal) -> str:
    payload = goal_review_payload(goal)
    details = json.dumps(
        payload["category_details"],
        ensure_ascii=True,
        sort_keys=True,
        default=str,
    )
    return "\n".join(
        [
            (
                "Existing saved goal review context "
                "(authoritative database record):"
            ),
            f"Goal ID: {payload['goal_id']}.",
            f"Name: {payload['name']}.",
            f"Category: {payload['category']}.",
            f"Priority: {payload['priority']}.",
            f"Target amount: AUD {payload['target_amount']}.",
            f"Current amount: AUD {payload['current_amount']}.",
            (
                "Current monthly contribution: "
                f"AUD {payload['monthly_contribution']}."
            ),
            f"Target date: {payload['target_date']}.",
            f"Progress: {payload['progress_percentage']}%.",
            f"Code-calculated status: {payload['status']}.",
            (
                "Code-calculated required monthly contribution: "
                f"AUD {payload['required_monthly']}."
            ),
            (
                "Monthly contribution minus required monthly amount: "
                f"AUD {payload['monthly_difference']}."
            ),
            f"Months remaining: {payload['months_remaining']}.",
            (
                "Projected completion date at the current contribution: "
                f"{payload['projected_completion_date'] or 'Unavailable'}."
            ),
            f"Category details: {details}.",
            "Goal review directive:",
            (
                "This is a review of an existing saved goal, not a request to "
                "start the new-goal planning workflow."
            ),
            (
                "Give a complete review now. Assess the target, deadline, "
                "current progress, contribution level, and calculated monthly "
                "gap. Identify what is working, the main risks, and practical "
                "prioritised improvements."
            ),
            (
                "Use verified financial context to discuss affordability when "
                "it is available. If it is unavailable, clearly say that "
                "affordability has not been verified."
            ),
            (
                "Do not ask the user to repeat values already present in this "
                "record. Keep the review educational, specific, supportive, "
                "and clear that projections are not guaranteed."
            ),
        ]
    )
