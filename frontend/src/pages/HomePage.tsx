import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getGoals } from "../api/goals";
import MyFinancialsPanel from "../components/MyFinancialsPanel";
import { AssetType as ApiAssetType, DebtType as ApiDebtType, Frequency as ApiFrequency, CashFlow, Financials, FinancialSummary, createAsset, createCashFlow, createDebt, createRecurringCashFlow, getFinancials, getFinancialSummary } from "../api/financials";
import { AssetType, FinancialEntry, assetLabels, money, monthLabel, sameMonth, thisWeek } from "../utils/financials";
import type { Goal } from "../types/goalTypes";
import { formatGoalCurrency, formatGoalProgressPercentage, goalFromApi, goalProgress, goalStatus } from "../utils/goalUtils";
import GoalProgressBar from "../components/goals/GoalProgressBar";
import GoalStatusBadge from "../components/goals/GoalStatusBadge";

const assetColors: Record<AssetType, string> = { cash: "#3b82f6", stocks: "#10b981", bonds: "#f59e0b", property: "#f43f5e", vehicle: "#8b5cf6", others: "#64748b" };

function useChartAnimation() {
  const [ready, setReady] = useState(false);
  useEffect(() => { setReady(false); const timer = requestAnimationFrame(() => setReady(true)); return () => cancelAnimationFrame(timer); }, []);
  return ready;
}

function dashboardNumbers(summary: FinancialSummary | null) {
  return {
    netWorth: Number(summary?.net_worth ?? 0), cashSavings: Number(summary?.cash_savings ?? 0),
    debts: Number(summary?.total_debts ?? 0), income: Number(summary?.monthly_income ?? 0),
    expenses: Number(summary?.monthly_expenses ?? 0),
  };
}

function StatCard({ title, value, stamp }: { title: string; value: string; stamp?: string }) {
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</p><p className="mt-3 text-3xl font-bold text-slate-900">{value}</p>{stamp && <p className="mt-2 text-xs font-semibold text-blue-600">{stamp}</p>}</article>;
}

function CashFlowChart({ summary }: { summary: FinancialSummary | null }) {
  const ready = useChartAnimation();
  const income = Number(summary?.monthly_income ?? 0);
  const expenses = Number(summary?.monthly_expenses ?? 0);
  const total = Math.max(income + expenses, 1); const incomePct = income / total * 100; const expensePct = expenses / total * 100;
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><h2 className="text-lg font-bold text-slate-900">Monthly Cash Flow</h2><div className="mt-6"><div className="mb-3 flex justify-between text-sm font-bold"><span className="text-emerald-600">{Math.round(incomePct)}% Income</span><span className="text-red-500">{Math.round(expensePct)}% Expenses</span></div><div className="flex h-4 overflow-hidden rounded-full bg-slate-100"><span className="bg-emerald-500 transition-all duration-1000 ease-out" style={{ width: ready ? `${incomePct}%` : 0 }} /><span className="bg-red-500 transition-all duration-1000 ease-out" style={{ width: ready ? `${expensePct}%` : 0 }} /></div><div className="mt-3 flex justify-between text-sm text-slate-600"><span>{money(income)}</span><span>{monthLabel()}</span><span>{money(expenses)}</span></div></div></section>;
}

type AssetSlice = { type: AssetType; amount: number; percent: number };

function assetSlices(summary: FinancialSummary | null) {
  const rows = summary?.asset_allocation.map((item) => ({ type: item.asset_type as AssetType, amount: Number(item.amount) })) || [];
  const total = rows.reduce((sum, item) => sum + item.amount, 0);
  return rows.map((item) => ({ ...item, percent: total ? item.amount / total * 100 : 0 })).filter((item) => item.amount > 0);
}

function pieBackground(slices: AssetSlice[]) {
  let cursor = 0; const parts = slices.map((slice) => { const start = cursor; cursor += slice.percent; return `${assetColors[slice.type]} ${start}% ${cursor}%`; });
  return parts.length ? `conic-gradient(${parts.join(", ")})` : "#e2e8f0";
}

function AssetAllocation({ summary }: { summary: FinancialSummary | null }) {
  const slices = assetSlices(summary);
  const total = slices.reduce((sum, slice) => sum + slice.amount, 0);
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><h2 className="text-lg font-bold text-slate-900">Asset Allocation</h2><div className="mt-6 grid items-center gap-6 sm:grid-cols-[13rem_minmax(0,1fr)]"><AssetDonut slices={slices} total={total} /><AssetLegend slices={slices} /></div></section>;
}

function AssetDonut({ slices, total }: { slices: AssetSlice[]; total: number }) {
  return <div className="mx-auto grid size-48 place-items-center rounded-full p-3 sm:size-52" style={{ background: pieBackground(slices) }}><div className="grid size-full place-items-center rounded-full bg-white text-center shadow-inner"><div><p className="text-xs font-semibold text-slate-500">Total Assets</p><p className="mt-1 text-2xl font-bold text-slate-900">{money(total)}</p></div></div></div>;
}

function AssetLegend({ slices }: { slices: AssetSlice[] }) {
  if (!slices.length) return <p className="text-sm text-slate-500">Add assets to view allocation.</p>;
  return <div className="grid min-w-44 gap-3">{slices.map((slice) => <div key={slice.type} className="grid grid-cols-[minmax(6rem,1fr)_3.5rem] items-center gap-3"><span className="whitespace-nowrap"><span className="mr-3 inline-block size-3 rounded" style={{ background: assetColors[slice.type] }} />{assetLabels[slice.type]}</span><b className="text-right">{Math.round(slice.percent)}%</b></div>)}</div>;
}

function linePath(points: { x: number; y: number }[]) { return points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" "); }

function CashSavingsLine({ summary }: { summary: FinancialSummary | null }) {
  const ready = useChartAnimation();
  const points = (summary?.cash_savings_trend ?? []).map((point) => ({ label: point.month, value: Number(point.amount) }));
  const values = points.map((point) => point.value);
  const top = Math.max(...values, 100); const bottom = Math.min(...values, 0); const range = Math.max(top - bottom, 1);
  const labels = [top, top - range / 3, top - range * 2 / 3, bottom];
  const coords = points.map((point, index) => ({ x: 70 + index * (420 / Math.max(points.length - 1, 1)), y: 190 - ((point.value - bottom) / range) * 145 }));
  const path = linePath(coords); const area = `${path} L ${coords[coords.length - 1]?.x ?? 490} 205 L ${coords[0]?.x ?? 70} 205 Z`;
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><h2 className="text-lg font-bold text-slate-900">Cash Savings Trend</h2>{points.length ? <svg viewBox="0 0 540 235" className="mt-5 h-56 w-full sm:h-72"><defs><linearGradient id="savingArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#2aa198" stopOpacity="0.32" /><stop offset="100%" stopColor="#2aa198" stopOpacity="0" /></linearGradient><clipPath id="savingReveal"><rect x="0" y="0" width={ready ? "540" : "0"} height="235" className="transition-all duration-[1400ms] ease-out" /></clipPath></defs>{coords.map((point) => <line key={point.x} x1={point.x} x2={point.x} y1="30" y2="205" stroke="#e5e7eb" />)}{labels.map((label, index) => <text key={index} x="8" y={45 + index * 55} fill="#a3a3a3" fontSize="12">{money(label)}</text>)}<g clipPath="url(#savingReveal)"><path d={area} fill="url(#savingArea)" /><path d={path} fill="none" stroke="#2aa198" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.25" /></g>{points.map((point, index) => <text key={point.label} x={coords[index].x - 18} y="230" fill="#a3a3a3" fontSize="12">{point.label.slice(5)}</text>)}</svg> : <p className="mt-4 text-sm text-slate-500">No savings history is available.</p>}</section>;
}

function RecentCashFlow({ flows }: { flows: CashFlow[] }) {
  const [unit, setUnit] = useState<"month" | "week">("month"); const [page, setPage] = useState(0);
  const entries = flows.map((flow) => ({ id: String(flow.id), kind: "cashflow" as const, flowType: flow.flow_type, name: flow.name, amount: Number(flow.amount), date: flow.date, createdAt: flow.created_at }));
  const rows = entries.filter((entry) => unit === "month" ? sameMonth(entry.date) : thisWeek(entry.date));
  const totalPages = Math.max(Math.ceil(rows.length / 8), 1); const visible = rows.slice(page * 8, page * 8 + 8);
  function changeUnit(next: "month" | "week") { setUnit(next); setPage(0); }
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold text-slate-900">Recent Cash Flow</h2><div className="flex rounded-xl bg-slate-100 p-1">{(["month", "week"] as const).map((item) => <button key={item} type="button" onClick={() => changeUnit(item)} className={`rounded-lg px-3 py-1.5 text-xs font-bold capitalize ${unit === item ? "bg-white text-blue-600 shadow-sm" : "text-slate-500"}`}>{item}</button>)}</div></div><div className="mt-4 h-[32rem] space-y-3 sm:h-[40rem]">{visible.map((entry) => <div key={entry.id} className="flex justify-between rounded-xl bg-slate-50 px-4 py-3 text-sm"><div><p className="font-semibold">{entry.name}</p><p className="text-slate-500">{new Date(entry.date).toLocaleDateString("en-AU")}</p></div><p className={entry.flowType === "expense" ? "font-bold text-red-600" : "font-bold text-emerald-600"}>{entry.flowType === "expense" ? "-" : ""}{money(entry.amount)}</p></div>)}{!rows.length && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No cash flow records for this period.</p>}</div>{totalPages > 1 && <div className="mt-4 flex items-center justify-between text-sm text-slate-500"><button type="button" disabled={!page} onClick={() => setPage(page - 1)} className="rounded-lg px-3 py-2 font-bold disabled:text-slate-300">Previous</button><span>Page {page + 1} of {totalPages}</span><button type="button" disabled={page + 1 >= totalPages} onClick={() => setPage(page + 1)} className="rounded-lg px-3 py-2 font-bold disabled:text-slate-300">Next</button></div>}</section>;
}

type HomeGoalFilter = "On Track" | "Behind" | "Completed";

function MyGoalsCard({ goals, onOpen }: { goals: Goal[]; onOpen: (goal: Goal) => void }) {
  const [filter, setFilter] = useState<HomeGoalFilter>("On Track");
  const filteredGoals = goals.filter((goal) => goalStatus(goal) === filter).slice(0, 4);
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold text-slate-900">My Goals</h2><GoalMiniFilters filter={filter} onChange={setFilter} /></div><div className="mt-4 space-y-3">{filteredGoals.map((goal) => <GoalPreviewRow key={goal.id} goal={goal} onOpen={onOpen} />)}{!filteredGoals.length && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No goals found</p>}</div></section>;
}

function GoalMiniFilters({ filter, onChange }: { filter: HomeGoalFilter; onChange: (filter: HomeGoalFilter) => void }) {
  return <div className="flex rounded-xl bg-slate-100 p-1">{(["On Track", "Behind", "Completed"] as HomeGoalFilter[]).map((item) => <button key={item} type="button" onClick={() => onChange(item)} className={`rounded-lg px-3 py-1.5 text-xs font-bold ${filter === item ? "bg-white text-blue-600 shadow-sm" : "text-slate-500"}`}>{item}</button>)}</div>;
}

function GoalPreviewRow({ goal, onOpen }: { goal: Goal; onOpen: (goal: Goal) => void }) {
  const progress = goalProgress(goal);
  return <button type="button" onClick={() => onOpen(goal)} className="w-full rounded-xl border border-slate-100 bg-slate-50 p-4 text-left transition hover:border-blue-200 hover:bg-blue-50/40"><div className="flex flex-wrap items-center justify-between gap-3"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="truncate font-bold text-slate-900">{goal.name}</h3><GoalStatusBadge status={goalStatus(goal)} /></div><p className="mt-1 text-xs font-semibold text-slate-500">{formatGoalCurrency(goal.currentAmount)} / {formatGoalCurrency(goal.targetAmount)}</p></div><span className="text-sm font-bold text-slate-700">{formatGoalProgressPercentage(progress)}%</span></div><div className="mt-3"><GoalProgressBar value={progress} status={goalStatus(goal)} /></div></button>;
}

export default function HomePage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<FinancialSummary | null>(null); const [financials, setFinancials] = useState<Financials | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  const numbers = dashboardNumbers(summary);

  async function refreshFinancials() {
    const [nextSummary, nextFinancials, goalRows] = await Promise.all([getFinancialSummary(), getFinancials(), getGoals()]);
    setSummary(nextSummary); setFinancials(nextFinancials); setGoals(goalRows.map(goalFromApi));
  }

  useEffect(() => { refreshFinancials().catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load financial data.")).finally(() => setLoading(false)); }, []);

  async function addEntry(entry: FinancialEntry) {
    setError("");
    try {
      if (entry.kind === "asset") await createAsset({ asset_type: entry.assetType as ApiAssetType, name: entry.name, amount: entry.amount });
      else if (entry.kind === "debt") await createDebt({ debt_type: entry.debtType as ApiDebtType, name: entry.name, balance: entry.balance, minimum_payment: entry.minimumPayment, interest_rate: entry.interestRate });
      else if (entry.kind === "recurring") await createRecurringCashFlow({ flow_type: entry.flowType, name: entry.name, amount: entry.amount, frequency: entry.frequency as ApiFrequency, start_date: entry.startDate, end_date: entry.endDate, category: entry.category });
      else await createCashFlow({ flow_type: entry.flowType, name: entry.name, amount: entry.amount, date: entry.date });
      await refreshFinancials();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to save financial data."); }
  }

  if (loading) return <main className="p-10 text-slate-500">Loading your financial dashboard...</main>;
  const flows = summary?.recent_cash_flows || financials?.cash_flows || [];
  const openGoal = (goal: Goal) => navigate("/goals", { state: { goalId: goal.apiId ?? Number(goal.id) } });
  return <main className="min-h-screen space-y-6 bg-slate-50 p-4 sm:p-6 lg:p-8"><header><h1 className="text-3xl font-bold tracking-tight text-slate-900">Insights Overview</h1>{error && <p className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}</header><section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5"><StatCard title="Net Worth" value={money(numbers.netWorth)} /><StatCard title="Cash Savings" value={money(numbers.cashSavings)} /><StatCard title="Debt" value={money(numbers.debts)} /><StatCard title="Income" value={money(numbers.income)} stamp={monthLabel()} /><StatCard title="Expenses" value={money(numbers.expenses)} stamp={monthLabel()} /></section>
    <section className="grid items-start gap-6 xl:grid-cols-[minmax(24rem,0.95fr)_minmax(0,1.35fr)]"><div className="grid self-start gap-6"><AssetAllocation summary={summary} /><RecentCashFlow flows={flows} /></div><div className="grid self-start gap-6"><CashFlowChart summary={summary} /><CashSavingsLine summary={summary} /><MyGoalsCard goals={goals} onOpen={openGoal} /></div></section><MyFinancialsPanel summary={summary} onAdd={(entry) => void addEntry(entry)} /></main>;
}
