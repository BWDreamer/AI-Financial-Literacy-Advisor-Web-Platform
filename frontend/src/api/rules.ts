import { apiRequest } from "./client";

export type FinancialRule = {
  id: number;
  region: string;
  category: string;
  rule_year: string;
  rule_key: string;
  rule_value: string;
  source_name: string | null;
  source_url: string | null;
  created_at: string;
};

export type RuleFilters = Partial<Pick<FinancialRule, "region" | "category" | "rule_year">>;

export function getRules(filters: RuleFilters = {}) {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => value && query.set(key, value));
  const suffix = query.size ? `?${query}` : "";
  return apiRequest<FinancialRule[]>(`/rules${suffix}`, { authenticated: true });
}

export function getRule(ruleId: number) {
  return apiRequest<FinancialRule>(`/rules/${ruleId}`, { authenticated: true });
}
