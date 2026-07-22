import { apiRequest } from "./client";

export type GoalPayload = {
  name: string;
  category: string;
  target_amount: number;
  current_amount: number;
  monthly_contribution: number;
  target_date: string;
  priority: number;
  category_details?: Record<string, unknown>;
};

export type GoalRecord = GoalPayload & {
  id: number;
  created_at: string;
  updated_at: string;
  status: "on_track" | "behind" | "pending_archive" | "completed";
  progress_percentage: number;
  allocated_monthly: number;
  cash_allocation: number;
  archived: boolean;
};

export type GoalSummaryRecord = {
  total_goals: number;
  on_track_goals: number;
  behind_goals: number;
  completed_goals: number;
  cash_savings: number;
  cash_allocatable: number;
  cash_already_assigned: number;
  cash_unassigned: number;
  monthly_net_income: number;
  monthly_allocatable: number;
  monthly_already_assigned: number;
  monthly_unassigned: number;
  total_target_amount: number;
  total_current_amount: number;
  total_monthly_contribution: number;
};

export type GoalRatio = { goal_id: number; ratio: number };
export type GoalAllocationSettings = {
  cash_allocatable_ratio: number;
  monthly_allocatable_ratio: number;
  goal_monthly_ratios: GoalRatio[];
  monthly_allocation: MonthlyAllocation;
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
  allocated_monthly: number; cash_allocation: number;
  months_remaining: number; projected_completion_date: string | null; status: "on_track" | "behind" | "pending_archive" | "completed";
};
type GoalAnalysisRecord = Omit<
  GoalAnalysis,
  | "progress_percentage"
  | "required_monthly"
  | "monthly_difference"
  | "allocated_monthly"
  | "cash_allocation"
> & {
  progress_percentage: number | string;
  required_monthly: number | string;
  monthly_difference: number | string;
  allocated_monthly: number | string;
  cash_allocation: number | string;
};
export type GoalNotification = {
  id: number; goal_id: number; notification_type: string; title: string; message: string;
  read: boolean; archived: boolean; created_at: string; updated_at: string;
};
export type GoalProgressPayload = { amount: number; progress_date: string; note?: string; source?: string };
export type GoalProgress = GoalProgressPayload & { id: number; goal_id: number; new_current_amount: number; created_at: string; updated_at: string };
export type GoalChart = { actual_progress_points: Array<{ date: string; amount: number }>; expected_progress_points: Array<{ date: string; amount: number }>; target_amount: number };
export type GoalPreview = { goal: GoalPayload; analysis: GoalAnalysis };
export type GoalPreviewInput = { category: string; target_date: string; priority: "High" | "Medium" | "Low"; category_details: Record<string, string | number> };

export const getGoals = () => apiRequest<GoalRecord[]>("/goals", { authenticated: true });
export const previewGoal = (input: GoalPreviewInput) => apiRequest<GoalPreview>("/goals/preview", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const getGoalSummary = () => apiRequest<GoalSummaryRecord>("/goals/summary", { authenticated: true });
export async function getGoalAnalysis(id: number): Promise<GoalAnalysis> {
  const record = await apiRequest<GoalAnalysisRecord>(
    `/goals/${id}/analysis`,
    { authenticated: true },
  );
  return {
    ...record,
    progress_percentage: Number(record.progress_percentage),
    required_monthly: Number(record.required_monthly),
    monthly_difference: Number(record.monthly_difference),
    allocated_monthly: Number(record.allocated_monthly),
    cash_allocation: Number(record.cash_allocation),
  };
}
export const getGoalChart = (id: number) => apiRequest<GoalChart>(`/goals/${id}/chart`, { authenticated: true });
export const getGoalProgress = (id: number) => apiRequest<GoalProgress[]>(`/goals/${id}/progress`, { authenticated: true });
export const createGoalProgress = (id: number, input: GoalProgressPayload) => apiRequest<GoalProgress>(`/goals/${id}/progress`, { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateGoalProgress = (goalId: number, progressId: number, input: GoalProgressPayload) => apiRequest<GoalProgress>(`/goals/${goalId}/progress/${progressId}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteGoalProgress = (goalId: number, progressId: number) => apiRequest<void>(`/goals/${goalId}/progress/${progressId}`, { method: "DELETE", authenticated: true });
export const getGoalAllocationSettings = () => apiRequest<GoalAllocationSettings>("/goals/allocation-settings", { authenticated: true });
export type GoalAllocationSettingsInput = Omit<GoalAllocationSettings, "monthly_allocation">;
export const updateGoalAllocationSettings = (input: GoalAllocationSettingsInput) => apiRequest<GoalAllocationSettings>("/goals/allocation-settings", { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const createGoal = (input: GoalPayload) => apiRequest<GoalRecord>("/goals", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateGoal = (id: number, input: GoalPayload) => apiRequest<GoalRecord>(`/goals/${id}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteGoal = (id: number) => apiRequest<void>(`/goals/${id}`, { method: "DELETE", authenticated: true });
export const getGoalNotifications = () => apiRequest<GoalNotification[]>("/goals/notifications", { authenticated: true });
export const readGoalNotification = (id: number) => apiRequest<GoalNotification>(`/goals/notifications/${id}/read`, { method: "POST", authenticated: true });
export const archiveGoal = (id: number) => apiRequest<GoalRecord>(`/goals/${id}/archive`, { method: "POST", authenticated: true });
