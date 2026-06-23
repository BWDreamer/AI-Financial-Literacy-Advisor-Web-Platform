from decimal import Decimal, ROUND_HALF_UP


MONEY_PRECISION = Decimal("0.01")


def round_money(value: float) -> float:
    return float(
        Decimal(str(value)).quantize(
            MONEY_PRECISION,
            rounding=ROUND_HALF_UP,
        )
    )


def calculate_compound_interest(
    principal: float,
    annual_interest_rate: float,
    years: float,
    compounds_per_year: int,
) -> dict:
    periodic_rate = (
        annual_interest_rate
        / 100
        / compounds_per_year
    )

    total_periods = compounds_per_year * years

    final_amount = principal * (
        1 + periodic_rate
    ) ** total_periods

    interest_earned = final_amount - principal

    return {
        "principal": round_money(principal),
        "annual_interest_rate": annual_interest_rate,
        "years": years,
        "compounds_per_year": compounds_per_year,
        "final_amount": round_money(final_amount),
        "interest_earned": round_money(
            interest_earned
        ),
    }


def calculate_goal_monthly_saving(
    target_amount: float,
    current_amount: float,
    months: int,
    annual_interest_rate: float = 0,
) -> dict:
    monthly_rate = (
        annual_interest_rate
        / 100
        / 12
    )

    projected_current_amount = current_amount * (
        1 + monthly_rate
    ) ** months

    remaining_amount = max(
        target_amount - projected_current_amount,
        0,
    )

    if remaining_amount == 0:
        required_monthly_saving = 0

    elif monthly_rate == 0:
        required_monthly_saving = (
            remaining_amount / months
        )

    else:
        annuity_factor = (
            (1 + monthly_rate) ** months - 1
        )

        required_monthly_saving = (
            remaining_amount
            * monthly_rate
            / annuity_factor
        )

    return {
        "target_amount": round_money(
            target_amount
        ),
        "current_amount": round_money(
            current_amount
        ),
        "months": months,
        "annual_interest_rate": (
            annual_interest_rate
        ),
        "projected_current_amount": round_money(
            projected_current_amount
        ),
        "remaining_amount": round_money(
            remaining_amount
        ),
        "required_monthly_saving": round_money(
            required_monthly_saving
        ),
        "additional_saving_required": (
            remaining_amount > 0
        ),
    }