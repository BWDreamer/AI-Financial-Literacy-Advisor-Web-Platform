def calculate_goal_monthly_saving(target_amount: float, current_amount: float, months: int) -> dict:
    if months <= 0:
        return {"error": "months must be greater than 0"}

    remaining_amount = max(target_amount - current_amount, 0)
    monthly_saving = remaining_amount / months

    return {
        "target_amount": round(target_amount, 2),
        "current_amount": round(current_amount, 2),
        "remaining_amount": round(remaining_amount, 2),
        "months": months,
        "required_monthly_saving": round(monthly_saving, 2),
    }
