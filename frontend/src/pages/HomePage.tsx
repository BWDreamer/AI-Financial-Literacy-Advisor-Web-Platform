import { useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import MyFinancialsPanel from "../components/MyFinancialsPanel";
import { AssetType as ApiAssetType, CashFlow, Financials, FinancialSummary, createAsset, createCashFlow, getFinancials, getFinancialSummary } from "../api/financials";
import { AssetType, CashFlowEntry, FinancialEntry, assetLabels, assetTotal, cashFlowTotal, cashFlows, money, monthLabel, sameMonth, thisWeek } from "../utils/financials";

const assetColors: Record<AssetType, string> = { cash: "#3b82f6", stocks: "#10b981", bonds: "#f59e0b", property: "#f43f5e", vehicle: "#8b5cf6", others: "#64748b" };
const monthNames = Array.from({ length: 12 }, (_, index) => new Date(2026, index, 1).toLocaleDateString("en-AU", { month: "short" }));

function monthInputValue(date = new Date()) { return date.toISOString().slice(0, 7); }
function sameInputMonth(date: string, month: string) { return date.slice(0, 7) === month; }
function monthDisplay(month: string) { return monthLabel(new Date(`${month}-01T00:00:00`)); }
function previousMonth(month: string) { const date = new Date(`${month}-01T00:00:00`); date.setMonth(date.getMonth() - 1); return monthInputValue(date); }
function monthParts(month: string) { return { year: Number(month.slice(0, 4)), index: Number(month.slice(5, 7)) - 1 }; }

function useChartAnimation() {
  const [ready, setReady] = useState(false);
  useEffect(() => { setReady(false); const timer = requestAnimationFrame(() => setReady(true)); return () => cancelAnimationFrame(timer); }, []);
  return ready;
}

function toEntries(financials: Financials | null): FinancialEntry[] {
  if (!financials) return [];
  const assets = financials.assets.map((asset) => ({ id: String(asset.id), kind: "asset" as const, assetType: asset.asset_type, name: asset.name, amount: Number(asset.amount), createdAt: asset.created_at }));
  const flows = financials.cash_flows.map((flow) => ({ id: String(flow.id), kind: "cashflow" as const, flowType: flow.flow_type, name: flow.name, amount: Number(flow.amount), date: flow.date, createdAt: flow.created_at }));
  return [...assets, ...flows];
}

function cashSavingsValue(entries: FinancialEntry[]) {
  const income = cashFlowTotal(entries, "income"); const expenses = cashFlowTotal(entries, "expense");
  return assetTotal(entries, "cash") + income - expenses;
}

function dashboardNumbers(summary: FinancialSummary | null, entries: FinancialEntry[]) {
  const cashSavings = cashSavingsValue(entries); const nonCashAssets = assetTotal(entries) - assetTotal(entries, "cash");
  return { netWorth: nonCashAssets + cashSavings, cashSavings, income: Number(summary?.monthly_income || 0), expenses: Number(summary?.monthly_expenses || 0) };
}

function StatCard({ title, value, stamp }: { title: string; value: string; stamp?: string }) {
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</p><p className="mt-3 text-3xl font-bold text-slate-900">{value}</p>{stamp && <p className="mt-2 text-xs font-semibold text-blue-600">{stamp}</p>}</article>;
}

function MonthPicker({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false); const { year, index } = monthParts(value);
  const [activeYear, setActiveYear] = useState(year); const current = monthParts(monthInputValue());
  const years = Array.from({ length: 12 }, (_, item) => current.year - item);
  function choose(monthIndex: number) { onChange(`${activeYear}-${String(monthIndex + 1).padStart(2, "0")}`); setOpen(false); }
  return <div className="relative"><button type="button" onClick={() => setOpen(!open)} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 hover:border-blue-300"><span>{year} {monthNames[index]}</span><ChevronDown size={16} /></button>{open && <div className="absolute right-0 z-20 mt-2 grid w-64 grid-cols-[5rem_1fr] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"><div className="max-h-56 overflow-y-auto border-r border-slate-100 bg-slate-50 p-2">{years.map((item) => <button key={item} type="button" onClick={() => setActiveYear(item)} className={`mb-1 w-full rounded-lg px-2 py-2 text-sm font-bold ${activeYear === item ? "bg-blue-600 text-white" : "text-slate-500 hover:bg-white"}`}>{item}</button>)}</div><div className="max-h-56 overflow-y-auto p-2">{monthNames.map((name, monthIndex) => { const disabled = activeYear === current.year && monthIndex > current.index; return <button key={name} type="button" disabled={disabled} onClick={() => choose(monthIndex)} className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm font-semibold ${activeYear === year && monthIndex === index ? "bg-blue-50 text-blue-600" : "text-slate-600 hover:bg-slate-50"} disabled:cursor-not-allowed disabled:text-slate-300`}>{name}</button>; })}</div></div>}</div>;
}

function CashFlowChart({ entries }: { entries: FinancialEntry[] }) {
  const [month, setMonth] = useState(monthInputValue()); const ready = useChartAnimation();
  const predicate = (entry: CashFlowEntry) => sameInputMonth(entry.date, month);
  const income = cashFlowTotal(entries, "income", predicate); const expenses = cashFlowTotal(entries, "expense", predicate);
  const total = Math.max(income + expenses, 1); const incomePct = income / total * 100; const expensePct = expenses / total * 100;
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold text-slate-900">Monthly Cash Flow</h2><MonthPicker value={month} onChange={setMonth} /></div><div className="mt-6"><div className="mb-3 flex justify-between text-sm font-bold"><span className="text-emerald-600">{Math.round(incomePct)}% Income</span><span className="text-red-500">{Math.round(expensePct)}% Expenses</span></div><div className="flex h-4 overflow-hidden rounded-full bg-slate-100"><span className="bg-emerald-500 transition-all duration-1000 ease-out" style={{ width: ready ? `${incomePct}%` : 0 }} /><span className="bg-red-500 transition-all duration-1000 ease-out" style={{ width: ready ? `${expensePct}%` : 0 }} /></div><div className="mt-3 flex justify-between text-sm text-slate-600"><span>{money(income)}</span><span>{monthDisplay(month)}</span><span>{money(expenses)}</span></div></div></section>;
}

type AssetSlice = { type: AssetType; amount: number; percent: number };

function assetSlices(summary: FinancialSummary | null, entries: FinancialEntry[]) {
  const values = summary?.asset_allocation.map((item) => ({ type: item.asset_type as AssetType, amount: Number(item.amount) })) || [];
  const fallback = (Object.keys(assetLabels) as AssetType[]).map((type) => ({ type, amount: assetTotal(entries, type) }));
  const rows = values.length ? values : fallback; const total = rows.reduce((sum, item) => sum + item.amount, 0);
  return rows.map((item) => ({ ...item, percent: total ? item.amount / total * 100 : 0 })).filter((item) => item.amount > 0);
}

function pieBackground(slices: AssetSlice[]) {
  let cursor = 0; const parts = slices.map((slice) => { const start = cursor; cursor += slice.percent; return `${assetColors[slice.type]} ${start}% ${cursor}%`; });
  return parts.length ? `conic-gradient(${parts.join(", ")})` : "#e2e8f0";
}

function AssetAllocation({ summary, entries }: { summary: FinancialSummary | null; entries: FinancialEntry[] }) {
  const slices = assetSlices(summary, entries);
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><h2 className="text-lg font-bold text-slate-900">Asset Allocation</h2><div className="mt-6 grid items-center gap-6 sm:grid-cols-[11rem_minmax(0,1fr)]"><div className="mx-auto size-40 rounded-full sm:size-44" style={{ background: pieBackground(slices) }} /><AssetLegend slices={slices} /></div></section>;
}

function AssetLegend({ slices }: { slices: AssetSlice[] }) {
  if (!slices.length) return <p className="text-sm text-slate-500">Add assets to view allocation.</p>;
  return <div className="grid min-w-44 gap-3">{slices.map((slice) => <div key={slice.type} className="grid grid-cols-[minmax(6rem,1fr)_3.5rem] items-center gap-3"><span className="whitespace-nowrap"><span className="mr-3 inline-block size-3 rounded" style={{ background: assetColors[slice.type] }} />{assetLabels[slice.type]}</span><b className="text-right">{Math.round(slice.percent)}%</b></div>)}</div>;
}

function monthDayLabels(month: string) {
  const last = new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0).getDate();
  return [1, 5, 10, 15, 20, 25, last].filter((day, index, days) => days.indexOf(day) === index);
}

function cashSavingsBeforeMonth(entries: FinancialEntry[], month: string) {
  const firstDay = new Date(`${month}-01T00:00:00`).getTime();
  return assetTotal(entries, "cash") + cashFlows(entries).filter((entry) => new Date(entry.date).getTime() < firstDay).reduce((sum, entry) => sum + (entry.flowType === "income" ? entry.amount : -entry.amount), 0);
}

function cashSavingsPoints(entries: FinancialEntry[], month: string) {
  const base = cashSavingsBeforeMonth(entries, month);
  const rows = cashFlows(entries).filter((entry) => sameInputMonth(entry.date, month)).reverse();
  return monthDayLabels(month).map((day) => ({ label: new Date(`${month}-${String(day).padStart(2, "0")}T00:00:00`).toLocaleDateString("en-AU", { month: "short", day: "2-digit" }), value: rows.filter((entry) => new Date(entry.date).getDate() <= day).reduce((sum, entry) => sum + (entry.flowType === "income" ? entry.amount : -entry.amount), base) }));
}

function linePath(points: { x: number; y: number }[]) { return points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" "); }

function yAxisLabels(max: number) {
  const step = Math.max(Math.ceil(max / 3 / 100) * 100, 100);
  return [step * 3, step * 2, step, 0];
}

function CashSavingsLine({ entries }: { entries: FinancialEntry[] }) {
  const ready = useChartAnimation(); const [month, setMonth] = useState(monthInputValue());
  const points = cashSavingsPoints(entries, month); const lastPoints = cashSavingsPoints(entries, previousMonth(month));
  const max = Math.max(...points.map((point) => point.value), ...lastPoints.map((point) => point.value), 100); const labels = yAxisLabels(max); const top = labels[0]; const min = 0;
  const coords = points.map((point, index) => ({ x: 70 + index * (420 / (points.length - 1)), y: 190 - ((point.value - min) / (top - min)) * 145 }));
  const lastCoords = lastPoints.map((point, index) => ({ x: 70 + index * (420 / (lastPoints.length - 1)), y: 190 - ((point.value - min) / (top - min)) * 145 }));
  const path = linePath(coords); const previous = linePath(lastCoords); const area = `${path} L 490 205 L 70 205 Z`;
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex flex-wrap items-center justify-between gap-4"><div className="flex flex-wrap items-center gap-4 sm:gap-8"><h2 className="text-lg font-bold text-slate-900">Saving Summary</h2><MonthPicker value={month} onChange={setMonth} /></div><div className="flex flex-wrap gap-4 text-sm text-slate-600 sm:gap-8"><span><b className="mr-2 inline-block h-2 w-5 rounded bg-teal-600" />This month</span><span><b className="mr-2 inline-block h-2 w-5 rounded bg-slate-300" />Same period last month</span></div></div><svg viewBox="0 0 540 235" className="mt-5 h-56 w-full sm:h-72"><defs><linearGradient id="savingArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#2aa198" stopOpacity="0.32" /><stop offset="100%" stopColor="#2aa198" stopOpacity="0" /></linearGradient><clipPath id="savingReveal"><rect x="0" y="0" width={ready ? "540" : "0"} height="235" className="transition-all duration-[1400ms] ease-out" /></clipPath></defs>{[70, 140, 210, 280, 350, 420, 490].map((x) => <line key={x} x1={x} x2={x} y1="30" y2="205" stroke="#e5e7eb" />)}{labels.map((label, index) => <text key={label} x="20" y={45 + index * 55} fill="#a3a3a3" fontSize="13">{money(label)}</text>)}<g clipPath="url(#savingReveal)"><path d={previous} fill="none" stroke="#d1d5db" strokeDasharray="5 5" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" /><path d={area} fill="url(#savingArea)" /><path d={path} fill="none" stroke="#2aa198" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.25" /></g>{points.filter((_, index) => index % 2 === 0).map((point, index) => <text key={point.label} x={70 + index * 84} y="230" fill="#a3a3a3" fontSize="13">{point.label}</text>)}</svg></section>;
}

function RecentCashFlow({ flows }: { flows: CashFlow[] }) {
  const [unit, setUnit] = useState<"month" | "week">("month"); const [page, setPage] = useState(0);
  const entries = flows.map((flow) => ({ id: String(flow.id), kind: "cashflow" as const, flowType: flow.flow_type, name: flow.name, amount: Number(flow.amount), date: flow.date, createdAt: flow.created_at }));
  const rows = entries.filter((entry) => unit === "month" ? sameMonth(entry.date) : thisWeek(entry.date));
  const totalPages = Math.max(Math.ceil(rows.length / 8), 1); const visible = rows.slice(page * 8, page * 8 + 8);
  function changeUnit(next: "month" | "week") { setUnit(next); setPage(0); }
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold text-slate-900">Recent Cash Flow</h2><div className="flex rounded-xl bg-slate-100 p-1">{(["month", "week"] as const).map((item) => <button key={item} type="button" onClick={() => changeUnit(item)} className={`rounded-lg px-3 py-1.5 text-xs font-bold capitalize ${unit === item ? "bg-white text-blue-600 shadow-sm" : "text-slate-500"}`}>{item}</button>)}</div></div><div className="mt-4 h-[32rem] space-y-3 sm:h-[40rem]">{visible.map((entry) => <div key={entry.id} className="flex justify-between rounded-xl bg-slate-50 px-4 py-3 text-sm"><div><p className="font-semibold">{entry.name}</p><p className="text-slate-500">{new Date(entry.date).toLocaleDateString("en-AU")}</p></div><p className={entry.flowType === "expense" ? "font-bold text-red-600" : "font-bold text-emerald-600"}>{entry.flowType === "expense" ? "-" : ""}{money(entry.amount)}</p></div>)}{!rows.length && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No cash flow records for this period.</p>}</div>{totalPages > 1 && <div className="mt-4 flex items-center justify-between text-sm text-slate-500"><button type="button" disabled={!page} onClick={() => setPage(page - 1)} className="rounded-lg px-3 py-2 font-bold disabled:text-slate-300">Previous</button><span>Page {page + 1} of {totalPages}</span><button type="button" disabled={page + 1 >= totalPages} onClick={() => setPage(page + 1)} className="rounded-lg px-3 py-2 font-bold disabled:text-slate-300">Next</button></div>}</section>;
}

function GoalsPlaceholder() { return <section className="min-h-72 rounded-2xl border border-dashed border-blue-200 bg-blue-50/40 p-4 sm:p-6"><h2 className="text-lg font-bold text-slate-900">My Goals</h2></section>; }

export default function HomePage() {
  const [summary, setSummary] = useState<FinancialSummary | null>(null); const [financials, setFinancials] = useState<Financials | null>(null);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  const entries = useMemo(() => toEntries(financials), [financials]);
  const numbers = useMemo(() => dashboardNumbers(summary, entries), [summary, entries]);

  async function refreshFinancials() {
    const [nextSummary, nextFinancials] = await Promise.all([getFinancialSummary(), getFinancials()]);
    setSummary(nextSummary); setFinancials(nextFinancials);
  }

  useEffect(() => { refreshFinancials().catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load financial data.")).finally(() => setLoading(false)); }, []);

  async function addEntry(entry: FinancialEntry) {
    setError("");
    try {
      if (entry.kind === "asset") await createAsset({ asset_type: entry.assetType as ApiAssetType, name: entry.name, amount: entry.amount });
      else await createCashFlow({ flow_type: entry.flowType, name: entry.name, amount: entry.amount, date: entry.date });
      await refreshFinancials();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to save financial data."); }
  }

  if (loading) return <main className="p-10 text-slate-500">Loading your financial dashboard...</main>;
  const flows = summary?.recent_cash_flows || financials?.cash_flows || [];
  return <main className="min-h-screen space-y-6 bg-slate-50 p-4 sm:p-6 lg:p-8"><header><h1 className="text-3xl font-bold tracking-tight text-slate-900">Insights Overview</h1>{error && <p className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}</header><section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard title="Net Worth" value={money(numbers.netWorth)} /><StatCard title="Cash Savings" value={money(numbers.cashSavings)} /><StatCard title="Income" value={money(numbers.income)} stamp={monthLabel()} /><StatCard title="Expenses" value={money(numbers.expenses)} stamp={monthLabel()} /></section>
    <section className="grid items-start gap-6 xl:grid-cols-[minmax(24rem,0.95fr)_minmax(0,1.35fr)]"><div className="grid self-start gap-6"><AssetAllocation summary={summary} entries={entries} /><RecentCashFlow flows={flows} /></div><div className="grid self-start gap-6"><CashFlowChart entries={entries} /><CashSavingsLine entries={entries} /><GoalsPlaceholder /></div></section><MyFinancialsPanel entries={entries} onAdd={(entry) => void addEntry(entry)} /></main>;
}
