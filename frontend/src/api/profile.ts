import { apiRequest } from "./client";

export type FinancialProfileInput = {
  region: string;
  monthly_income: number;
  fixed_expenses: number;
  current_savings: number;
  initial_savings_target: number;
};

export type FinancialProfile = FinancialProfileInput & {
  id: number;
  user_id: number;
  created_at: string;
};

export function getFinancialProfile() {
  return apiRequest<FinancialProfile>("/profile", { authenticated: true });
}

export function saveFinancialProfile(profile: FinancialProfileInput) {
  return apiRequest<FinancialProfile>("/profile", {
    method: "PUT", authenticated: true, body: JSON.stringify(profile),
  });
}
