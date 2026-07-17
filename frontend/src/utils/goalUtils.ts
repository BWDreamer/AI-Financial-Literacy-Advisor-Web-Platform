import type { Goal, GoalCategory, GoalFilter, GoalPriority, GoalSort, GoalStatus } from "../types/goalTypes";
import type { GoalPayload, GoalRecord } from "../api/goals";

export const goalCategories: GoalCategory[] = ["General Saving", "Emergency Fund", "Debt Repayment", "Home Deposit", "Retirement", "Budget"];
export const goalPriorities: GoalPriority[] = ["High", "Medium", "Low"];
export const goalFilters: GoalFilter[] = ["All", "On Track", "Behind", "Completed"];
export const goalSortOptions: GoalSort[] = ["Recent", "Priority", "Target Date", "Progress"];

const priorityRank: Record<GoalPriority, number> = { High: 0, Medium: 1, Low: 2 };
const priorityLabels: Record<number, GoalPriority> = { 1: "High", 2: "High", 3: "Medium", 4: "Low", 5: "Low" };
const priorityValues: Record<GoalPriority, number> = { High: 1, Medium: 3, Low: 5 };

export function formatGoalCurrency(value: number) {
  return new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 }).format(value || 0);
}

export function goalProgress(goal: Goal) {
  return goal.progressPercentage;
}

export function goalStatus(goal: Goal): GoalStatus {
  if (goal.status) return goal.status;
  const actual = goalProgress(goal);
  if (actual >= 100) return "Completed";
  return "On Track";
}

export function filterGoals(goals: Goal[], filter: GoalFilter) {
  return filter === "All" ? goals : goals.filter((goal) => goalStatus(goal) === filter);
}

export function sortGoals(goals: Goal[], sort: GoalSort) {
  const rows = [...goals];
  if (sort === "Priority") return rows.sort((a, b) => priorityRank[a.priority] - priorityRank[b.priority]);
  if (sort === "Target Date") return rows.sort((a, b) => a.targetDate.localeCompare(b.targetDate));
  if (sort === "Progress") return rows.sort((a, b) => goalProgress(b) - goalProgress(a));
  return rows.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function orderGoals(goals: Goal[]) {
  return [...goals].sort((a, b) => priorityRank[a.priority] - priorityRank[b.priority] || a.targetDate.localeCompare(b.targetDate));
}

export function formatGoalDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-AU", { month: "short", year: "numeric" });
}

export function tomorrowValue() {
  const date = new Date(); date.setDate(date.getDate() + 1);
  return date.toISOString().slice(0, 10);
}

export function goalFromApi(record: GoalRecord): Goal {
  return {
    id: String(record.id),
    apiId: record.id,
    name: record.name,
    category: normalizeCategory(record.category),
    targetAmount: Number(record.target_amount),
    currentAmount: Number(record.current_amount),
    monthlyContribution: Number(record.monthly_contribution),
    progressPercentage: Number(record.progress_percentage),
    targetDate: record.target_date,
    createdAt: record.created_at.slice(0, 10),
    priority: priorityLabels[record.priority] || "Medium",
    status: record.status === "completed" ? "Completed" : record.status === "behind" ? "Behind" : "On Track",
    categoryDetails: record.category_details as Record<string, string | number> | undefined,
  };
}

export function goalToPayload(goal: Goal, priority?: number): GoalPayload {
  return {
    name: goal.name,
    category: goal.category,
    target_amount: goal.targetAmount,
    current_amount: goal.currentAmount,
    monthly_contribution: goal.monthlyContribution,
    target_date: goal.targetDate,
    priority: priority ?? priorityValues[goal.priority],
    category_details: goal.categoryDetails,
  };
}

export function normalizeCategory(value: string): GoalCategory {
  return goalCategories.find((item) => item.toLowerCase() === value.toLowerCase()) || "General Saving";
}
