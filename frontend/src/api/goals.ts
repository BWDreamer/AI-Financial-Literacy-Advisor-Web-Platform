import { apiRequest } from "./client";

export type GoalPayload = {
  name: string;
  category: string;
  target_amount: number;
  current_amount: number;
  monthly_contribution: number;
  target_date: string;
  priority: number;
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
  completed_goals: number;
  total_target_amount: number;
  total_current_amount: number;
  total_monthly_contribution: number;
};

export const getGoals = () => apiRequest<GoalRecord[]>("/goals", { authenticated: true });
export const getGoalSummary = () => apiRequest<GoalSummaryRecord>("/goals/summary", { authenticated: true });
export const createGoal = (input: GoalPayload) => apiRequest<GoalRecord>("/goals", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateGoal = (id: number, input: GoalPayload) => apiRequest<GoalRecord>(`/goals/${id}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteGoal = (id: number) => apiRequest<void>(`/goals/${id}`, { method: "DELETE", authenticated: true });
export const createGoalContribution = (goalId: number, amount: number) => apiRequest<GoalContribution>(`/goals/${goalId}/contributions`, { method: "POST", authenticated: true, body: JSON.stringify({ amount }) });
export const getGoalContributions = (goalId: number) => apiRequest<GoalContribution[]>(`/goals/${goalId}/contributions`, { authenticated: true });
