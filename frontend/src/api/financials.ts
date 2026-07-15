import { apiRequest } from "./client";

export type AssetType = "cash" | "stocks" | "bonds" | "property" | "vehicle" | "others";
export type FlowType = "income" | "expense";
export type DebtType = "mortgage" | "car_loan" | "personal_loan" | "credit_card" | "student_loan" | "bnpl" | "tax_debt" | "other";
export type Frequency = "weekly" | "fortnightly" | "monthly" | "yearly";

export type AssetInput = { asset_type: AssetType; name: string; amount: number };
export type Asset = AssetInput & { id: number; created_at: string; updated_at: string };
export type CashFlowInput = { flow_type: FlowType; name: string; amount: number; date: string };
export type CashFlow = CashFlowInput & { id: number; created_at: string; updated_at: string };
export type DebtInput = { debt_type: DebtType; name: string; balance: number; minimum_payment?: number | null; interest_rate?: number | null };
export type Debt = DebtInput & { id: number; created_at: string; updated_at: string };
export type RecurringCashFlowInput = { flow_type: FlowType; name: string; amount: number; frequency: Frequency; start_date: string; end_date?: string | null; category?: string | null };
export type RecurringCashFlow = RecurringCashFlowInput & { id: number; created_at: string; updated_at: string };
export type Financials = { assets: Asset[]; debts: Debt[]; cash_flows: CashFlow[]; recurring_cash_flows: RecurringCashFlow[] };

export type FinancialSummary = {
  total_assets: number;
  total_debts: number;
  net_worth: number;
  cash_savings: number;
  monthly_income: number;
  monthly_expenses: number;
  monthly_cash_flow: number;
  asset_allocation: { asset_type: AssetType; amount: number }[];
  debt_breakdown: { debt_type: DebtType; amount: number }[];
  cash_savings_trend: { month: string; amount: number }[];
  recent_cash_flows: CashFlow[];
};

export const getFinancials = () => apiRequest<Financials>("/financials", { authenticated: true });
export const getFinancialSummary = () => apiRequest<FinancialSummary>("/financials/summary", { authenticated: true });
export const createAsset = (input: AssetInput) => apiRequest<Asset>("/financials/assets", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateAsset = (id: number, input: AssetInput) => apiRequest<Asset>(`/financials/assets/${id}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteAsset = (id: number) => apiRequest<void>(`/financials/assets/${id}`, { method: "DELETE", authenticated: true });
export const createCashFlow = (input: CashFlowInput) => apiRequest<CashFlow>("/financials/cash-flows", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateCashFlow = (id: number, input: CashFlowInput) => apiRequest<CashFlow>(`/financials/cash-flows/${id}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteCashFlow = (id: number) => apiRequest<void>(`/financials/cash-flows/${id}`, { method: "DELETE", authenticated: true });
export const createDebt = (input: DebtInput) => apiRequest<Debt>("/financials/debts", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateDebt = (id: number, input: DebtInput) => apiRequest<Debt>(`/financials/debts/${id}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteDebt = (id: number) => apiRequest<void>(`/financials/debts/${id}`, { method: "DELETE", authenticated: true });
export const createRecurringCashFlow = (input: RecurringCashFlowInput) => apiRequest<RecurringCashFlow>("/financials/recurring-cash-flows", { method: "POST", authenticated: true, body: JSON.stringify(input) });
export const updateRecurringCashFlow = (id: number, input: RecurringCashFlowInput) => apiRequest<RecurringCashFlow>(`/financials/recurring-cash-flows/${id}`, { method: "PUT", authenticated: true, body: JSON.stringify(input) });
export const deleteRecurringCashFlow = (id: number) => apiRequest<void>(`/financials/recurring-cash-flows/${id}`, { method: "DELETE", authenticated: true });
