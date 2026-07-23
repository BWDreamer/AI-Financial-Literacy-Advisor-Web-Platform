from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


MAX_GOAL_RATIO = Decimal("100.000000")
RATIO_QUANTUM = Decimal("0.000001")


def ratio_percent(value: Decimal) -> Decimal:
    """Round a percentage without losing cent-accurate monthly allocations."""
    return Decimal(value).quantize(RATIO_QUANTUM, rounding=ROUND_HALF_UP)


def normalize_goal_ratio_rows(ratios: list) -> list[dict[str, int | str]]:
    """Return normalized goal ratios whose total never exceeds 100%."""
    rows: list[tuple[int, Decimal]] = []
    for item in ratios:
        goal_id = item["goal_id"] if isinstance(item, dict) else item.goal_id
        ratio = item["ratio"] if isinstance(item, dict) else item.ratio
        rows.append(
            (
                int(goal_id),
                max(ratio_percent(Decimal(str(ratio))), Decimal("0")),
            )
        )

    total = sum((ratio for _, ratio in rows), Decimal("0"))
    if total > MAX_GOAL_RATIO:
        exact_scaled = [
            (goal_id, ratio * MAX_GOAL_RATIO / total)
            for goal_id, ratio in rows
        ]
        rows = [
            (
                goal_id,
                ratio.quantize(RATIO_QUANTUM, rounding=ROUND_DOWN),
            )
            for goal_id, ratio in exact_scaled
        ]
        remaining_units = int(
            (
                MAX_GOAL_RATIO
                - sum((ratio for _, ratio in rows), Decimal("0"))
            )
            / RATIO_QUANTUM
        )
        remainder_order = sorted(
            range(len(rows)),
            key=lambda index: (
                exact_scaled[index][1] - rows[index][1],
                -index,
            ),
            reverse=True,
        )
        for index in remainder_order[:remaining_units]:
            goal_id, ratio = rows[index]
            rows[index] = (goal_id, ratio + RATIO_QUANTUM)

    return [
        {"goal_id": goal_id, "ratio": str(ratio_percent(ratio))}
        for goal_id, ratio in rows
    ]
