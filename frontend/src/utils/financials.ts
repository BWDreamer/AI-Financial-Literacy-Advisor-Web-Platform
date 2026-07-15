export type AssetType = "cash" | "stocks" | "bonds" | "property" | "vehicle" | "others";
export type CashFlowType = "income" | "expense";
export type DebtType = "mortgage" | "car_loan" | "personal_loan" | "credit_card" | "student_loan" | "bnpl" | "tax_debt" | "other";
export type Frequency = "once" | "weekly" | "fortnightly" | "monthly" | "yearly";
export type TimeUnit = "year" | "month" | "week";

export type AssetEntry = { id: string; kind: "asset"; assetType: AssetType; name: string; amount: number; createdAt: string };
export type CashFlowEntry = { id: string; kind: "cashflow"; flowType: CashFlowType; name: string; amount: number; date: string; createdAt: string };
export type DebtEntry = { id: string; kind: "debt"; debtType: DebtType; name: string; balance: number; minimumPayment?: number; interestRate?: number; createdAt: string };
export type RecurringCashFlowEntry = { id: string; kind: "recurring"; flowType: CashFlowType; name: string; amount: number; frequency: Exclude<Frequency, "once">; startDate: string; endDate?: string; category?: string; createdAt: string };
export type FinancialEntry = AssetEntry | CashFlowEntry | DebtEntry | RecurringCashFlowEntry;

const STORAGE_PREFIX = "financeai_financials";
export const assetLabels: Record<AssetType, string> = { cash: "Cash", stocks: "Stocks", bonds: "Bonds", property: "Property", vehicle: "Vehicle", others: "Others" };
export const debtLabels: Record<DebtType, string> = { mortgage: "Mortgage", car_loan: "Car Loan", personal_loan: "Personal Loan", credit_card: "Credit Card", student_loan: "Student Loan", bnpl: "BNPL", tax_debt: "Tax Debt", other: "Other" };

const keyFor = (userId?: number) => `${STORAGE_PREFIX}:${userId || "anonymous"}`;
const isAsset = (entry: FinancialEntry): entry is AssetEntry => entry.kind === "asset";
const isCashFlow = (entry: FinancialEntry): entry is CashFlowEntry => entry.kind === "cashflow";
const isDebt = (entry: FinancialEntry): entry is DebtEntry => entry.kind === "debt";
const isRecurring = (entry: FinancialEntry): entry is RecurringCashFlowEntry => entry.kind === "recurring";

export function loadFinancialEntries(userId?: number) {
  // TODO: Replace localStorage with backend financial-card APIs when available.
  const stored = localStorage.getItem(keyFor(userId));
  return stored ? JSON.parse(stored) as FinancialEntry[] : [];
}

export function saveFinancialEntries(userId: number | undefined, entries: FinancialEntry[]) {
  // TODO: Replace localStorage with backend financial-card APIs when available.
  localStorage.setItem(keyFor(userId), JSON.stringify(entries));
}

export function money(value: number) {
  return new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 }).format(value || 0);
}

export function assetTotal(entries: FinancialEntry[], type?: AssetType) {
  return entries.filter(isAsset).filter((entry) => !type || entry.assetType === type).reduce((sum, entry) => sum + entry.amount, 0);
}

export function cashFlowTotal(entries: FinancialEntry[], type: CashFlowType, predicate: (entry: CashFlowEntry) => boolean = () => true) {
  return entries.filter(isCashFlow).filter((entry) => entry.flowType === type && predicate(entry)).reduce((sum, entry) => sum + entry.amount, 0);
}

export function debtTotal(entries: FinancialEntry[], type?: DebtType) {
  return entries.filter(isDebt).filter((entry) => !type || entry.debtType === type).reduce((sum, entry) => sum + entry.balance, 0);
}

export function recurringMonthlyTotal(entries: FinancialEntry[], type: CashFlowType) {
  return entries.filter(isRecurring).filter((entry) => entry.flowType === type).reduce((sum, entry) => sum + monthlyRecurringAmount(entry), 0);
}

export function monthlyRecurringAmount(entry: RecurringCashFlowEntry) {
  if (entry.frequency === "weekly") return entry.amount * 52 / 12;
  if (entry.frequency === "fortnightly") return entry.amount * 26 / 12;
  if (entry.frequency === "yearly") return entry.amount / 12;
  return entry.amount;
}

export function cashFlows(entries: FinancialEntry[]) {
  return entries.filter(isCashFlow).sort((a, b) => b.date.localeCompare(a.date));
}

export function monthLabel(date = new Date()) {
  return date.toLocaleDateString("en-AU", { year: "numeric", month: "short" });
}

export function sameMonth(date: string, now = new Date()) {
  const value = new Date(date); return value.getFullYear() === now.getFullYear() && value.getMonth() === now.getMonth();
}

export function withinRecentDays(date: string, days: number) {
  return Date.now() - new Date(date).getTime() <= days * 24 * 60 * 60 * 1000;
}

export function thisWeek(date: string) {
  const value = new Date(date).setHours(0, 0, 0, 0);
  const start = new Date().setHours(0, 0, 0, 0) - 6 * 24 * 60 * 60 * 1000;
  return value >= start && value <= new Date().setHours(23, 59, 59, 999);
}

export function todayInputValue() {
  return new Date().toISOString().slice(0, 10);
}

export function signedCashFlow(entry: CashFlowEntry) {
  return entry.flowType === "expense" ? -entry.amount : entry.amount;
}
