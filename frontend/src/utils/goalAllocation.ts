import type { MonthlyAllocation } from "../api/goals";

type GoalIdentifier = {
  id: string;
};

export function roundMoney(value: number) {
  return Math.round((Number.isFinite(value) ? value : 0) * 100) / 100;
}

export function roundRatio(value: number) {
  return Math.round((Number.isFinite(value) ? value : 0) * 1_000_000) / 1_000_000;
}

export function goalRatiosFromAllocation(
  goals: GoalIdentifier[],
  monthlyAllocation: MonthlyAllocation,
) {
  const ratiosByGoalId = new Map(
    monthlyAllocation.goals.map((item) => [item.goal_id, Number(item.ratio)]),
  );
  return goals.map((goal) => ratiosByGoalId.get(Number(goal.id)) ?? 0);
}

export function monthlyAllocationFromRatios(
  netIncome: number,
  monthlyRatio: number,
  goals: GoalIdentifier[],
  goalRatios: number[],
): MonthlyAllocation {
  const monthlyAllocatable = roundMoney(
    Math.max(netIncome, 0) * monthlyRatio / 100,
  );
  const rows = goals.map((goal, index) => {
    const ratio = roundRatio(goalRatios[index] ?? 0);
    return {
      goal_id: Number(goal.id),
      ratio,
      monthly_amount: roundMoney(monthlyAllocatable * ratio / 100),
    };
  });
  const alreadyAssigned = roundMoney(
    rows.reduce((sum, item) => sum + item.monthly_amount, 0),
  );
  return {
    monthly_net_income: netIncome,
    monthly_allocatable: monthlyAllocatable,
    already_assigned: alreadyAssigned,
    unassigned: roundMoney(Math.max(monthlyAllocatable - alreadyAssigned, 0)),
    goals: rows,
  };
}
