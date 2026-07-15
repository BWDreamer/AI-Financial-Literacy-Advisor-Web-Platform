import type { Goal, GoalCategory, GoalFilter, GoalPriority, GoalSort, GoalStatus } from "../types/goalTypes";
import type { GoalPayload, GoalRecord } from "../api/goals";

export const goalCategories: GoalCategory[] = ["General Saving", "Emergency Fund", "Debt Repayment", "Home Deposit", "Retirement", "Budget"];
export const goalPriorities: GoalPriority[] = ["High", "Medium", "Low"];
export const goalFilters: GoalFilter[] = ["All", "On Track", "Behind", "Completed"];
export const goalSortOptions: GoalSort[] = ["Recent", "Priority", "Target Date", "Progress"];

const priorityRank: Record<GoalPriority, number> = { High: 0, Medium: 1, Low: 2 };
const priorityLabels: Record<number, GoalPriority> = { 1: "High", 2: "High", 3: "Medium", 4: "Low", 5: "Low" };
const priorityValues: Record<GoalPriority, number> = { High: 1, Medium: 3, Low: 5 };

export const mockGoals: Goal[] = [
  { id: "goal-car", name: "Buy a Car", category: "General Saving", targetAmount: 15000, currentAmount: 5200, monthlyContribution: 600, createdAt: "2026-01-15", targetDate: "2027-12-01", priority: "Medium" },
  { id: "goal-emergency", name: "Emergency Fund", category: "Emergency Fund", targetAmount: 6000, currentAmount: 3600, monthlyContribution: 400, createdAt: "2026-04-01", targetDate: "2027-03-01", priority: "High" },
  { id: "goal-home", name: "Home Deposit", category: "Home Deposit", targetAmount: 50000, currentAmount: 12430, monthlyContribution: 800, createdAt: "2025-10-01", targetDate: "2030-06-01", priority: "High" },
  { id: "goal-debt", name: "Credit Card Debt", category: "Debt Repayment", targetAmount: 5200, currentAmount: 2800, monthlyContribution: 500, createdAt: "2026-05-01", targetDate: "2027-10-01", priority: "High" },
];

export function formatGoalCurrency(value: number) {
  return new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 }).format(value || 0);
}

export function goalProgress(goal: Goal) {
  if (goal.targetAmount <= 0) return 0;
  return Math.min(Math.max(goal.currentAmount / goal.targetAmount * 100, 0), 100);
}

export function expectedGoalProgress(goal: Goal, today = new Date()) {
  const created = new Date(goal.createdAt).getTime(); const target = new Date(goal.targetDate).getTime();
  const now = today.getTime(); if (!created || !target || target <= created || now <= created) return 0;
  return Math.min(Math.max((now - created) / (target - created) * 100, 0), 100);
}

export function monthsRemaining(goal: Goal, today = new Date()) {
  const target = new Date(`${goal.targetDate}T00:00:00`);
  const months = (target.getFullYear() - today.getFullYear()) * 12 + target.getMonth() - today.getMonth();
  return Math.max(months + (target.getDate() >= today.getDate() ? 0 : -1), 1);
}

export function requiredMonthlyContribution(goal: Goal, today = new Date()) {
  const remaining = Math.max(goal.targetAmount - goal.currentAmount, 0);
  return remaining / monthsRemaining(goal, today);
}

export function goalStatus(goal: Goal): GoalStatus {
  const actual = goalProgress(goal); if (actual >= 100) return "Completed";
  const target = new Date(`${goal.targetDate}T23:59:59`);
  if (target < new Date()) return "Behind";
  if (goal.monthlyContribution < requiredMonthlyContribution(goal)) return "Behind";
  return actual >= expectedGoalProgress(goal) * 0.9 ? "On Track" : "Behind";
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
    targetDate: record.target_date,
    createdAt: record.created_at.slice(0, 10),
    priority: priorityLabels[record.priority] || "Medium",
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
  };
}

export function normalizeCategory(value: string): GoalCategory {
  return goalCategories.find((item) => item.toLowerCase() === value.toLowerCase()) || "General Saving";
}
