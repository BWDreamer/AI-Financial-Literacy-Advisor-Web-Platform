export type AssetType = "cash" | "stocks" | "bonds" | "property" | "vehicle" | "others";
export type CashFlowType = "income" | "expense";
export type DebtType = "mortgage" | "car_loan" | "personal_loan" | "credit_card" | "student_loan" | "bnpl" | "tax_debt" | "other";
export type Frequency = "once" | "weekly" | "fortnightly" | "monthly" | "yearly";

export type AssetEntry = { id: string; kind: "asset"; assetType: AssetType; name: string; amount: number; createdAt: string };
export type CashFlowEntry = { id: string; kind: "cashflow"; flowType: CashFlowType; name: string; amount: number; date: string; createdAt: string };
export type DebtEntry = { id: string; kind: "debt"; debtType: DebtType; name: string; balance: number; minimumPayment?: number; interestRate?: number; createdAt: string };
export type RecurringCashFlowEntry = { id: string; kind: "recurring"; flowType: CashFlowType; name: string; amount: number; frequency: Exclude<Frequency, "once">; startDate: string; endDate?: string; category?: string; createdAt: string };
export type FinancialEntry = AssetEntry | CashFlowEntry | DebtEntry | RecurringCashFlowEntry;

export const assetLabels: Record<AssetType, string> = { cash: "Cash", stocks: "Stocks", bonds: "Bonds", property: "Property", vehicle: "Vehicle", others: "Others" };
export const debtLabels: Record<DebtType, string> = { mortgage: "Mortgage", car_loan: "Car Loan", personal_loan: "Personal Loan", credit_card: "Credit Card", student_loan: "Student Loan", bnpl: "BNPL", tax_debt: "Tax Debt", other: "Other" };

export function money(value: number) {
  return new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 }).format(value || 0);
}


export function monthLabel(date = new Date()) {
  return date.toLocaleDateString("en-AU", { year: "numeric", month: "short" });
}

export function sameMonth(date: string, now = new Date()) {
  const value = new Date(date); return value.getFullYear() === now.getFullYear() && value.getMonth() === now.getMonth();
}

export function thisWeek(date: string) {
  const value = new Date(date).setHours(0, 0, 0, 0);
  const start = new Date().setHours(0, 0, 0, 0) - 6 * 24 * 60 * 60 * 1000;
  return value >= start && value <= new Date().setHours(23, 59, 59, 999);
}

export function todayInputValue() {
  return new Date().toISOString().slice(0, 10);
}
