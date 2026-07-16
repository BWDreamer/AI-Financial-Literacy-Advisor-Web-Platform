export type GoalCategory =
  | "General Saving"
  | "Emergency Fund"
  | "Debt Repayment"
  | "Home Deposit"
  | "Retirement"
  | "Budget";

export type GoalPriority = "High" | "Medium" | "Low";
export type GoalStatus = "On Track" | "Behind" | "Completed";
export type GoalFilter = "All" | GoalStatus;
export type GoalSort = "Recent" | "Priority" | "Target Date" | "Progress";

export type Goal = {
  id: string;
  apiId?: number;
  name: string;
  category: GoalCategory;
  targetAmount: number;
  currentAmount: number;
  monthlyContribution: number;
  createdAt: string;
  targetDate: string;
  priority: GoalPriority;
  categoryDetails?: Record<string, string | number>;
};

export type GoalFormValues = Omit<Goal, "id" | "createdAt">;

export type GoalAllocation = {
  goalId: string;
  ratio: number;
  monthlyAmount: number;
  currentAllocation: number;
};
