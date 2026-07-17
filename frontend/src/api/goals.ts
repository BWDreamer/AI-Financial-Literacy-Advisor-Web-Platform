import { apiRequest } from "./client";

export type GoalPayload = {
  name: string;
  category: string;
  target_amount: number;
  current_amount: number;
  monthly_contribution: number;
  target_date: string;
  priority: number;
  status?: "on_track" | "behind" | "completed";
  category_details?: Record<string, unknown>;
};

export type GoalRecord = GoalPayload & {
  id: number;
  created_at: string;
  updated_at: string;
};

export type GoalContribution = {
  id: number;
  goal_id: number;
  amount: number;
  created_at: string;
};

export type GoalSummaryRecord = {
  total_goals: number;
  on_track_goals: number;
  behind_goals: number;
  completed_goals: number;
  cash_savings: number;
  cash_allocatable: number;
  cash_already_assigned: number;
  monthly_net_income: number;
  monthly_allocatable: number;
  monthly_already_assigned: number;
  total_target_amount: number;
  total_current_amount: number;
  total_monthly_contribution: number;
};

export type GoalRatio = { goal_id: number; ratio: number };
export type GoalAllocationSettings = {
  cash_allocatable_ratio: number;
  monthly_allocatable_ratio: number;
  goal_monthly_ratios: GoalRatio[];
};
export type MonthlyAllocation = {
  monthly_net_income: number;
  monthly_allocatable: number;
  already_assigned: number;
  unassigned: number;
  goals: Array<{ goal_id: number; ratio: number; monthly_amount: number }>;
};
export type GoalAnalysis = {
  progress_percentage: number; required_monthly: number; monthly_difference: number;
  months_remaining: number; projected_completion_date: string | null; status: "on_track" | "behind" | "completed";
};
export type GoalProgressPayload = { amount: number; progress_date: string; note?: string; source?: string };
export type GoalProgress = GoalProgressPayload & { id: number; goal_id: number; new_current_amount: number; created_at: string; updated_at: string };
export type GoalChart = { actual_progress_points: Array<{ date: string; amount: number }>; expected_progress_points: Array<{ date: string; amount: number }>; target_amount: number };

export const getGoals = () => apiRequest<GoalRecord[]>("/goals", { authenticated: true });
export const getGoalSummary = () => apiRequest<GoalSummaryRecord>("/goals/summary", { authenticated: true });
export const getGoalAnalysis = (id: number) => apiRequest<GoalAnalysis>(`/goals/${id}/analysis`, { authenticated: true });
export const getGoalChart = (id: number) => apiRequest<GoalChart>(`/goals/${id}/chart`, { authenticated: true });
export const getGoalProgress = (id: number) => apiRequest<GoalProgress[]>(`/goals/${id}/progress`, { authenticated: true });
export const createGoalProgress = (id: number, input: GoalProgressPayload) => apiRequest<GoalProgress>(`/goals/${id}/progress`, { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateGoalProgress = (goalId: number, progressId: number, input: GoalProgressPayload) => apiRequest<GoalProgress>(`/goals/${goalId}/progress/${progressId}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteGoalProgress = (goalId: number, progressId: number) => apiRequest<void>(`/goals/${goalId}/progress/${progressId}`, { method: "DELETE", authenticated: true });
export const getGoalAllocationSettings = () => apiRequest<GoalAllocationSettings>("/goals/allocation-settings", { authenticated: true });
export const updateGoalAllocationSettings = (input: GoalAllocationSettings) => apiRequest<GoalAllocationSettings>("/goals/allocation-settings", { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const updateMonthlyAllocation = (monthlyAllocatableRatio: number, goalMonthlyRatios: GoalRatio[]) => apiRequest<MonthlyAllocation>("/goals/monthly-allocation", { method: "PUT", authenticated: true, body: JSON.stringify({ monthly_allocatable_ratio: monthlyAllocatableRatio, goal_monthly_ratios: goalMonthlyRatios }) });
export const createGoal = (input: GoalPayload) => apiRequest<GoalRecord>("/goals", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateGoal = (id: number, input: GoalPayload) => apiRequest<GoalRecord>(`/goals/${id}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteGoal = (id: number) => apiRequest<void>(`/goals/${id}`, { method: "DELETE", authenticated: true });
export const createGoalContribution = (goalId: number, amount: number) => apiRequest<GoalContribution>(`/goals/${goalId}/contributions`, { method: "POST", authenticated: true, body: JSON.stringify({ amount }) });
export const getGoalContributions = (goalId: number) => apiRequest<GoalContribution[]>(`/goals/${goalId}/contributions`, { authenticated: true });
