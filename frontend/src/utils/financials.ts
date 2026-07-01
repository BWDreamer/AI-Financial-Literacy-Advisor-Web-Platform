export type AssetType = "cash" | "stocks" | "bonds" | "property" | "vehicle" | "others";
export type CashFlowType = "income" | "expense";
export type TimeUnit = "year" | "month" | "week";

export type AssetEntry = { id: string; kind: "asset"; assetType: AssetType; name: string; amount: number; createdAt: string };
export type CashFlowEntry = { id: string; kind: "cashflow"; flowType: CashFlowType; name: string; amount: number; date: string; createdAt: string };
export type FinancialEntry = AssetEntry | CashFlowEntry;

const STORAGE_PREFIX = "financeai_financials";
export const assetLabels: Record<AssetType, string> = { cash: "Cash", stocks: "Stocks", bonds: "Bonds", property: "Property", vehicle: "Vehicle", others: "Others" };

const keyFor = (userId?: number) => `${STORAGE_PREFIX}:${userId || "anonymous"}`;
const isAsset = (entry: FinancialEntry): entry is AssetEntry => entry.kind === "asset";
const isCashFlow = (entry: FinancialEntry): entry is CashFlowEntry => entry.kind === "cashflow";

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
