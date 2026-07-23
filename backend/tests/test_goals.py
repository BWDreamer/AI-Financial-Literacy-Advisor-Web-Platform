import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError

from app.models.goal import GoalAllocationSettings
from app.models.user import User
from app.repositories.goal_repository import get_allocation_settings
from app.services.goal_planning_service import normalize_goal_planning_state
from app.services.goal_service import build_confirmed_goal_plan
from tests.helpers import register_verified_user


def auth_headers(client, email: str) -> dict[str, str]:
    register_verified_user(
        client,
        {"email": email, "password": "Password123"},
    )
    response = client.post("/api/auth/login", json={"email": email, "password": "Password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def payload(**overrides):
    data = {"name": "Emergency fund", "category": "savings", "target_amount": "10000.00", "current_amount": "1000.00", "monthly_contribution": "500.00", "target_date": (date.today() + timedelta(days=365)).isoformat(), "priority": 1}
    data.update(overrides)
    return data


def test_allocation_settings_recovers_from_concurrent_default_creation():
    db = MagicMock()
    query = MagicMock()
    concurrent_settings = GoalAllocationSettings(
        id=7,
        user_id=42,
        goal_monthly_ratios=[],
    )
    query.filter.return_value.first.side_effect = [
        None,
        concurrent_settings,
    ]
    db.query.return_value = query
    db.commit.side_effect = IntegrityError(
        "INSERT INTO goal_allocation_settings",
        {"user_id": 42},
        Exception("duplicate user allocation settings"),
    )

    settings = get_allocation_settings(db, user_id=42)

    assert settings is concurrent_settings
    db.rollback.assert_called_once_with()
    db.refresh.assert_not_called()


def test_confirmed_ai_plan_maps_all_supported_goal_categories():
    deadline = (date.today() + timedelta(days=730)).isoformat()
    planned_goals = [
        {
            "category": "general_saving",
            "goal_title": "Reliable used car",
            "target_amount": 15000,
            "current_amount": 1000,
            "monthly_contribution": 500,
            "deadline": deadline,
            "priority": "High",
        },
        {
            "category": "emergency_fund",
            "essential_monthly_expenses": 2000,
            "coverage_months": 3,
            "current_amount": 1000,
            "monthly_contribution": 500,
            "deadline": deadline,
            "priority": "Medium",
        },
        {
            "category": "debt_repayment",
            "debt_name": "Credit card",
            "debt_balance": 4000,
            "minimum_repayment": 100,
            "extra_repayment": 50,
            "deadline": deadline,
            "priority": "High",
        },
        {
            "category": "home_deposit",
            "deposit_target": 50000,
            "cost_buffer": 5000,
            "current_amount": 10000,
            "monthly_contribution": 1000,
            "deadline": deadline,
            "priority": "Medium",
        },
        {
            "category": "retirement",
            "target_age": 65,
            "current_super": 100000,
            "target_amount": 1000000,
            "regular_contribution": 1000,
            "deadline": deadline,
            "priority": "Low",
        },
        {
            "category": "budget",
            "monthly_income": 5000,
            "fixed_expenses": 2500,
            "variable_expenses": 1000,
            "target_monthly_surplus": 1500,
            "deadline": deadline,
            "priority": "Medium",
        },
    ]
    state = normalize_goal_planning_state(
        {
            "goal_count": len(planned_goals),
            "goals": planned_goals,
            "recommendation_status": "accepted",
        }
    )

    confirmed_plan = build_confirmed_goal_plan(state, user_id=42)
    goals = confirmed_plan.goals

    assert len(confirmed_plan.fingerprint) == 64
    assert [goal.category for goal in goals] == [
        "General Saving",
        "Emergency Fund",
        "Debt Repayment",
        "Home Deposit",
        "Retirement",
        "Budget",
    ]
    assert [goal.name for goal in goals] == [
        "Reliable used car",
        "Emergency Fund",
        "Credit card",
        "Home Deposit",
        "Retirement Plan",
        "Improve Monthly Cash Flow",
    ]
    assert [float(goal.target_amount) for goal in goals] == [
        15000,
        6000,
        4000,
        55000,
        1000000,
        18000,
    ]
    assert [goal.priority for goal in goals] == [1, 3, 1, 3, 5, 3]
    for goal in goals:
        json.dumps(goal.category_details)


def test_goal_crud_progress_and_summary(client):
    headers = auth_headers(client, "goals@example.com")
    created = client.post("/api/goals", headers=headers, json=payload())
    assert created.status_code == 201
    goal_id = created.json()["id"]
    assert client.get(f"/api/goals/{goal_id}", headers=headers).status_code == 200
    assert len(client.get("/api/goals", headers=headers).json()) == 1
    progress = client.post(f"/api/goals/{goal_id}/progress", headers=headers, json={
        "amount": "250.00", "progress_date": date.today().isoformat(),
        "note": "Monthly saving", "source": "manual",
    })
    assert progress.status_code == 201
    assert progress.json()["goal_id"] == goal_id
    assert float(client.get(f"/api/goals/{goal_id}", headers=headers).json()["current_amount"]) == 1250
    assert len(client.get(f"/api/goals/{goal_id}/progress", headers=headers).json()) == 1
    updated = client.put(f"/api/goals/{goal_id}", headers=headers, json=payload(name="Holiday", current_amount="1250.00"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Holiday"
    summary = client.get("/api/goals/summary", headers=headers).json()
    assert summary["total_goals"] == 1
    assert float(summary["total_current_amount"]) == 1250
    assert client.delete(f"/api/goals/{goal_id}", headers=headers).status_code == 204


def test_goal_preview_calculates_category_values_on_backend(client):
    headers = auth_headers(client, "goal-preview@example.com")
    preview = client.post("/api/goals/preview", headers=headers, json={
        "category": "Emergency Fund", "target_date": (date.today() + timedelta(days=365)).isoformat(),
        "priority": "High", "category_details": {
            "essential_monthly_expenses": 2000, "coverage_months": 3,
            "current_amount": 1000, "monthly_contribution": 500,
        },
    })
    assert preview.status_code == 200
    data = preview.json()
    assert float(data["goal"]["target_amount"]) == 6000
    assert data["goal"]["priority"] == 1
    assert data["analysis"]["progress_percentage"] == "16.67"
    assert data["analysis"]["required_monthly"] != "0.00"

    direct_preview = client.post("/api/goals/preview", headers=headers, json={
        "category": "Emergency Fund", "target_date": (date.today() + timedelta(days=365)).isoformat(),
        "priority": "High", "category_details": {
            "target_amount": 1000,
            "essential_monthly_expenses": 1000, "coverage_months": 3,
            "current_amount": 0, "monthly_contribution": 200,
        },
    })
    assert direct_preview.status_code == 200
    assert float(direct_preview.json()["goal"]["target_amount"]) == 1000


def test_goals_are_private_and_validate_amounts(client):
    first = auth_headers(client, "goal-first@example.com")
    second = auth_headers(client, "goal-second@example.com")
    goal_id = client.post("/api/goals", headers=first, json=payload()).json()["id"]
    assert client.get(f"/api/goals/{goal_id}", headers=second).status_code == 404
    assert client.get(f"/api/goals/{goal_id}/progress", headers=second).status_code == 404
    assert client.post(f"/api/goals/{goal_id}/progress", headers=first, json={
        "amount": "10000", "progress_date": date.today().isoformat(),
    }).status_code == 422
    assert client.post("/api/goals", headers=first, json=payload(current_amount="11000")).status_code == 422


def test_goal_analysis_progress_chart_and_allocation(client):
    headers = auth_headers(client, "goal-analysis@example.com")
    created = client.post("/api/goals", headers=headers, json=payload(category_details={"risk": "low"}))
    assert created.status_code == 201
    goal_id = created.json()["id"]
    assert created.json()["category_details"] == {"risk": "low"}

    progress_payload = {
        "amount": "200.00", "progress_date": date.today().isoformat(),
        "note": "Automatic transfer", "source": "bank_transfer",
    }
    progress = client.post(f"/api/goals/{goal_id}/progress", headers=headers, json=progress_payload)
    assert progress.status_code == 201
    progress_id = progress.json()["id"]
    assert float(progress.json()["new_current_amount"]) == 1200
    assert client.get(f"/api/goals/{goal_id}/analysis", headers=headers).json()["progress_percentage"] == "12.00"
    chart = client.get(f"/api/goals/{goal_id}/chart", headers=headers)
    assert chart.status_code == 200
    assert float(chart.json()["target_amount"]) == 10000
    assert len(chart.json()["actual_progress_points"]) == 2

    changed = client.put(
        f"/api/goals/{goal_id}/progress/{progress_id}", headers=headers,
        json={**progress_payload, "amount": "300.00"},
    )
    assert float(changed.json()["new_current_amount"]) == 1300
    assert client.delete(f"/api/goals/{goal_id}/progress/{progress_id}", headers=headers).status_code == 204
    assert float(client.get(f"/api/goals/{goal_id}", headers=headers).json()["current_amount"]) == 1000

    client.post("/api/financials/assets", headers=headers, json={"asset_type": "cash", "name": "Savings", "amount": "5000"})
    client.post("/api/financials/recurring-cash-flows", headers=headers, json={
        "flow_type": "income", "name": "Salary", "amount": "4000", "frequency": "monthly",
        "start_date": date.today().isoformat(),
    })
    client.post("/api/financials/cash-buckets", headers=headers, json={
        "bucket_type": "goal_reserved", "name": "Goal reserve", "amount": "1000",
    })
    settings = {
        "cash_allocatable_ratio": "60", "monthly_allocatable_ratio": "50",
        "goal_monthly_ratios": [{"goal_id": goal_id, "ratio": "40"}],
    }
    allocation = client.put("/api/goals/allocation-settings", headers=headers, json=settings)
    assert allocation.status_code == 200
    monthly = allocation.json()["monthly_allocation"]
    assert float(monthly["monthly_allocatable"]) == 2000
    assert float(monthly["goals"][0]["monthly_amount"]) == 800
    saved = client.get("/api/goals/allocation-settings", headers=headers).json()
    assert saved["monthly_allocation"] == monthly
    assert float(client.get(f"/api/goals/{goal_id}", headers=headers).json()["monthly_contribution"]) == 500
    summary = client.get("/api/goals/summary", headers=headers).json()
    assert float(summary["cash_allocatable"]) == 3000
    assert float(summary["cash_already_assigned"]) == 1000
    assert float(summary["monthly_already_assigned"]) == 800


def test_deprecated_goal_contribution_routes_are_removed(client):
    headers = auth_headers(client, "goal-no-contributions@example.com")
    goal_id = client.post("/api/goals", headers=headers, json=payload()).json()["id"]
    assert client.get(f"/api/goals/{goal_id}/contributions", headers=headers).status_code == 404
    assert client.post(
        f"/api/goals/{goal_id}/contributions", headers=headers, json={"amount": "10"},
    ).status_code == 404


def test_goal_allocation_validation_and_cash_buckets(client):
    headers = auth_headers(client, "goal-buckets@example.com")
    first = client.post("/api/goals", headers=headers, json=payload(name="First")).json()["id"]
    second = client.post("/api/goals", headers=headers, json=payload(name="Second")).json()["id"]
    invalid = client.put("/api/goals/allocation-settings", headers=headers, json={
        "cash_allocatable_ratio": 50, "monthly_allocatable_ratio": 50,
        "goal_monthly_ratios": [{"goal_id": first, "ratio": 60}, {"goal_id": second, "ratio": 50}],
    })
    assert invalid.status_code == 422
    foreign = client.put("/api/goals/allocation-settings", headers=headers, json={
        "cash_allocatable_ratio": 50, "monthly_allocatable_ratio": 50,
        "goal_monthly_ratios": [{"goal_id": 99999, "ratio": 10}],
    })
    assert foreign.status_code == 422

    bucket = client.post("/api/financials/cash-buckets", headers=headers, json={
        "bucket_type": "emergency_fund", "name": "Emergency", "amount": "2500",
    })
    assert bucket.status_code == 201
    bucket_id = bucket.json()["id"]
    assert len(client.get("/api/financials/cash-buckets", headers=headers).json()) == 1
    assert client.put(f"/api/financials/cash-buckets/{bucket_id}", headers=headers, json={
        "bucket_type": "goal_reserved", "amount": "3000",
    }).status_code == 200
    assert client.delete(f"/api/financials/cash-buckets/{bucket_id}", headers=headers).status_code == 204


def test_goal_chart_caps_expected_points_and_preserves_endpoints(client):
    headers = auth_headers(client, "goal-long-chart@example.com")
    created = client.post("/api/goals", headers=headers, json=payload(target_date="9999-12-31"))
    assert created.status_code == 201

    chart = client.get(f"/api/goals/{created.json()['id']}/chart", headers=headers)
    assert chart.status_code == 200
    expected = chart.json()["expected_progress_points"]
    assert len(expected) <= 600
    assert expected[0] == {"date": created.json()["created_at"][:10], "amount": "0.00"}
    assert expected[-1] == {"date": "9999-12-31", "amount": "10000.00"}
    assert [point["date"] for point in expected] == sorted(point["date"] for point in expected)


def test_goal_progress_is_private(client):
    owner = auth_headers(client, "progress-owner@example.com")
    other = auth_headers(client, "progress-other@example.com")
    goal_id = client.post("/api/goals", headers=owner, json=payload()).json()["id"]
    progress_payload = {
        "amount": "200.00", "progress_date": date.today().isoformat(),
        "note": "Owner only", "source": "manual",
    }
    progress_id = client.post(
        f"/api/goals/{goal_id}/progress", headers=owner, json=progress_payload,
    ).json()["id"]

    assert client.get(f"/api/goals/{goal_id}/progress", headers=other).status_code == 404
    assert client.post(
        f"/api/goals/{goal_id}/progress", headers=other, json=progress_payload,
    ).status_code == 404
    assert client.put(
        f"/api/goals/{goal_id}/progress/{progress_id}", headers=other,
        json={**progress_payload, "amount": "300.00"},
    ).status_code == 404
    assert client.delete(
        f"/api/goals/{goal_id}/progress/{progress_id}", headers=other,
    ).status_code == 404


def test_completed_goal_notification_and_archive(client):
    headers = auth_headers(client, "goal-notifications@example.com")
    goal_id = client.post("/api/goals", headers=headers, json=payload(
        target_amount="1000.00", current_amount="1000.00",
    )).json()["id"]

    notifications = client.get("/api/goals/notifications", headers=headers)
    assert notifications.status_code == 200
    assert client.get(f"/api/goals/{goal_id}", headers=headers).json()["status"] == "pending_archive"
    assert notifications.json()[0]["goal_id"] == goal_id

    archived = client.post(f"/api/goals/{goal_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "completed"
    assert client.get("/api/goals", headers=headers).json()[0]["status"] == "completed"
    assert client.put(f"/api/goals/{goal_id}", headers=headers, json=payload()).status_code == 422
    assert client.post(f"/api/goals/{goal_id}/progress", headers=headers, json={
        "amount": "1.00", "progress_date": date.today().isoformat(), "source": "manual",
    }).status_code == 422


def test_completed_goals_are_excluded_from_monthly_allocation(client):
    headers = auth_headers(client, "goal-completed-allocation@example.com")
    done = client.post("/api/goals", headers=headers, json=payload(
        name="Done", target_amount="1000.00", current_amount="1000.00",
    )).json()["id"]
    active = client.post("/api/goals", headers=headers, json=payload(name="Active")).json()["id"]
    assert client.post(f"/api/goals/{done}/archive", headers=headers).status_code == 200
    client.post("/api/financials/recurring-cash-flows", headers=headers, json={
        "flow_type": "income", "name": "Salary", "amount": "10000",
        "frequency": "monthly", "start_date": date.today().isoformat(),
    })
    settings = client.put("/api/goals/allocation-settings", headers=headers, json={
        "cash_allocatable_ratio": 50, "monthly_allocatable_ratio": 50,
        "goal_monthly_ratios": [{"goal_id": done, "ratio": 50}, {"goal_id": active, "ratio": 40}],
    })
    assert settings.status_code == 200
    assert [row["goal_id"] for row in settings.json()["monthly_allocation"]["goals"]] == [active]


def test_updating_goal_syncs_monthly_ratio_as_json(client):
    headers = auth_headers(client, "goal-edit-ratio@example.com")
    first = client.post("/api/goals", headers=headers, json=payload(name="First")).json()["id"]
    second_payload = payload(name="Second", monthly_contribution="800.00")
    second = client.post("/api/goals", headers=headers, json=second_payload).json()["id"]

    client.post("/api/financials/recurring-cash-flows", headers=headers, json={
        "flow_type": "income", "name": "Salary", "amount": "20000", "frequency": "monthly",
        "start_date": date.today().isoformat(),
    })
    response = client.put(f"/api/goals/{second}", headers=headers, json={
        **second_payload, "monthly_contribution": "6400.00",
    })

    assert response.status_code == 200
    settings = client.get("/api/goals/allocation-settings", headers=headers).json()
    ratios = settings["goal_monthly_ratios"]
    assert any(item["goal_id"] == second for item in ratios)
    assert all(isinstance(item["ratio"], (int, float, str)) for item in ratios)


def test_allocation_settings_repairs_rounding_overflow_for_my_goals(
    client,
    db_session,
):
    email = "goal-rounding@example.com"
    headers = auth_headers(client, email)
    client.post("/api/financials/recurring-cash-flows", headers=headers, json={
        "flow_type": "income", "name": "Salary", "amount": "1000",
        "frequency": "monthly", "start_date": date.today().isoformat(),
    })
    goal_ids = [
        client.post(
            "/api/goals",
            headers=headers,
            json=payload(name=name, monthly_contribution=contribution),
        ).json()["id"]
        for name, contribution in [
            ("Computer", "500.01"),
            ("Graphics card", "333.33"),
            ("Car", "166.66"),
        ]
    ]

    user = db_session.query(User).filter(User.email == email).one()
    settings = db_session.query(GoalAllocationSettings).filter(
        GoalAllocationSettings.user_id == user.id,
    ).one()
    settings.goal_monthly_ratios = [
        {"goal_id": goal_ids[0], "ratio": "50.00"},
        {"goal_id": goal_ids[1], "ratio": "33.34"},
        {"goal_id": goal_ids[2], "ratio": "16.67"},
    ]
    db_session.add(settings)
    db_session.commit()

    allocation = client.get("/api/goals/allocation-settings", headers=headers)

    assert allocation.status_code == 200
    repaired_ratios = allocation.json()["goal_monthly_ratios"]
    assert sum(
        (Decimal(str(item["ratio"])) for item in repaired_ratios),
        Decimal("0"),
    ) <= Decimal("100")
    assert client.get("/api/goals", headers=headers).status_code == 200
    assert client.get("/api/goals/summary", headers=headers).status_code == 200


def test_cash_buckets_are_private(client):
    owner = auth_headers(client, "bucket-owner@example.com")
    other = auth_headers(client, "bucket-other@example.com")
    bucket = client.post("/api/financials/cash-buckets", headers=owner, json={
        "bucket_type": "emergency_fund", "name": "Private emergency fund", "amount": "2500",
    })
    assert bucket.status_code == 201
    bucket_id = bucket.json()["id"]

    assert client.get("/api/financials/cash-buckets", headers=other).json() == []
    assert client.put(f"/api/financials/cash-buckets/{bucket_id}", headers=other, json={
        "bucket_type": "goal_reserved", "amount": "3000",
    }).status_code == 404
    assert client.delete(
        f"/api/financials/cash-buckets/{bucket_id}", headers=other,
    ).status_code == 404
