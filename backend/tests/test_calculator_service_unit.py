from app.services.calculator_service import (
    calculate_compound_interest,
    calculate_goal_monthly_saving,
    round_money,
)


def test_round_money_uses_half_up_rounding():
    assert round_money(10.005) == 10.01
    assert round_money(10.004) == 10.0


def test_calculate_compound_interest_returns_expected_values():
    result = calculate_compound_interest(
        principal=10000,
        annual_interest_rate=5,
        years=10,
        compounds_per_year=12,
    )

    assert result == {
        "principal": 10000.0,
        "annual_interest_rate": 5,
        "years": 10,
        "compounds_per_year": 12,
        "final_amount": 16470.09,
        "interest_earned": 6470.09,
    }


def test_calculate_goal_monthly_saving_with_interest():
    result = calculate_goal_monthly_saving(
        target_amount=12000,
        current_amount=1000,
        months=12,
        annual_interest_rate=6,
    )

    assert result["projected_current_amount"] == 1061.68
    assert result["remaining_amount"] == 10938.32
    assert result["required_monthly_saving"] == 886.73
    assert result["additional_saving_required"] is True


def test_calculate_goal_monthly_saving_when_goal_already_met():
    result = calculate_goal_monthly_saving(
        target_amount=5000,
        current_amount=6000,
        months=12,
        annual_interest_rate=0,
    )

    assert result["remaining_amount"] == 0
    assert result["required_monthly_saving"] == 0
    assert result["additional_saving_required"] is False
