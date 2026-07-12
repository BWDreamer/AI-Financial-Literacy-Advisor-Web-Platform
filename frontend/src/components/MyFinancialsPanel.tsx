import { FormEvent, useState } from "react";
import { Banknote, ChevronDown, ChevronUp, Grid2X2, Home, Plus } from "lucide-react";
import { AssetType, CashFlowType, FinancialEntry, assetLabels, assetTotal, cashFlowTotal, money, sameMonth, todayInputValue } from "../utils/financials";
import DatePicker from "./DatePicker";
import FormInput from "./FormInput";
import PrimaryButton from "./PrimaryButton";

type Props = { entries: FinancialEntry[]; onAdd: (entry: FinancialEntry) => void };
type AddMode = "asset" | "cashflow";
type ActiveMode = AddMode | null;

const assetOptions: AssetType[] = ["cash", "stocks", "bonds", "property", "vehicle", "others"];
const selectClass = "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

function cashSavingsTotal(entries: FinancialEntry[]) {
  return assetTotal(entries, "cash") + cashFlowTotal(entries, "income") - cashFlowTotal(entries, "expense");
}

function SummaryCard({ mode, entries, active, onClick }: { mode: AddMode; entries: FinancialEntry[]; active: boolean; onClick: () => void }) {
  const isAsset = mode === "asset"; const Icon = isAsset ? Home : Banknote;
  const total = isAsset ? assetTotal(entries) - assetTotal(entries, "cash") + cashSavingsTotal(entries) : cashFlowTotal(entries, "income", (entry) => sameMonth(entry.date)) - cashFlowTotal(entries, "expense", (entry) => sameMonth(entry.date));
  return <button type="button" onClick={onClick} className={`rounded-2xl border border-dashed p-4 text-left transition ${active ? "border-blue-400 bg-blue-50" : "border-slate-300 bg-white hover:border-blue-300"}`}><div className="flex items-center justify-between"><span className="flex items-center gap-3 font-bold text-slate-900"><span className={`grid size-10 place-items-center rounded-full ${isAsset ? "bg-blue-100 text-blue-600" : "bg-emerald-100 text-emerald-600"}`}><Icon size={20} /></span>{isAsset ? "Assets" : "Cash Flow"}</span><Plus size={18} className="text-blue-600" /></div><p className="mt-3 text-2xl font-bold">{money(total)}</p><p className="text-xs text-slate-500">{isAsset ? "Total assets" : "This month net cash flow"}</p></button>;
}

function Actions({ label }: { label: string }) {
  return <div className="flex justify-end"><PrimaryButton className="w-full sm:w-auto">{label}</PrimaryButton></div>;
}

function AssetForm({ onAdd }: { onAdd: Props["onAdd"] }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    onAdd({ id: crypto.randomUUID(), kind: "asset", assetType: String(form.get("assetType")) as AssetType, name: String(form.get("name")), amount: Number(form.get("amount")) || 0, createdAt: new Date().toISOString() });
    event.currentTarget.reset();
  }
  return <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><label><span className="mb-2 block text-sm font-medium text-slate-700">Asset Type</span><select name="assetType" className={selectClass}>{assetOptions.map((item) => <option key={item} value={item}>{assetLabels[item]}</option>)}</select></label><FormInput id="asset-name" name="name" label="Name" required /><FormInput id="asset-amount" name="amount" type="number" min="0" step="0.01" label="Amount" required /><div className="flex items-end"><Actions label="Create Asset" /></div></form>;
}

function CashFlowForm({ onAdd }: { onAdd: Props["onAdd"] }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    onAdd({ id: crypto.randomUUID(), kind: "cashflow", flowType: String(form.get("flowType")) as CashFlowType, name: String(form.get("name")), date: String(form.get("date")), amount: Number(form.get("amount")) || 0, createdAt: new Date().toISOString() });
    event.currentTarget.reset();
  }
  return <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><label><span className="mb-2 block text-sm font-medium text-slate-700">Type</span><select name="flowType" className={selectClass}><option value="income">Income</option><option value="expense">Expense</option></select></label><FormInput id="flow-name" name="name" label="Name" required /><DatePicker id="flow-date" name="date" label="Date" defaultValue={todayInputValue()} max={todayInputValue()} placement="top" /><FormInput id="flow-amount" name="amount" type="number" min="0" step="0.01" label="Amount" required /><div className="flex items-end"><Actions label="Create Cash Flow" /></div></form>;
}

function ExpandedContent({ entries, onAdd, mode, setMode }: { entries: FinancialEntry[]; onAdd: Props["onAdd"]; mode: ActiveMode; setMode: (mode: ActiveMode) => void }) {
  const toggle = (next: AddMode) => setMode(mode === next ? null : next);
  return <div className="max-h-[78vh] overflow-y-auto rounded-t-3xl border border-slate-200 bg-white p-3 shadow-2xl transition-all duration-[900ms] ease-out sm:p-5"><div className="grid gap-4 md:grid-cols-2"><SummaryCard mode="asset" entries={entries} active={mode === "asset"} onClick={() => toggle("asset")} /><SummaryCard mode="cashflow" entries={entries} active={mode === "cashflow"} onClick={() => toggle("cashflow")} /></div><div className={`transition-all duration-[900ms] ease-out ${mode ? "mt-5 max-h-[34rem] overflow-visible" : "max-h-0 overflow-hidden"}`}><div className="rounded-2xl bg-slate-50 p-3 sm:p-4">{mode === "cashflow" ? <CashFlowForm onAdd={onAdd} /> : <AssetForm onAdd={onAdd} />}</div></div></div>;
}

export default function MyFinancialsPanel({ entries, onAdd }: Props) {
  const [expanded, setExpanded] = useState(false); const [mode, setMode] = useState<ActiveMode>(null);
  return <section className="sticky bottom-0 z-30 mx-auto max-w-5xl px-2 sm:px-4"><button type="button" onClick={() => setExpanded((value) => !value)} className="mx-auto flex w-[min(18rem,calc(100vw-1rem))] items-center justify-center gap-3 rounded-t-2xl bg-slate-900 px-4 py-3 text-sm font-bold text-white shadow-xl ring-2 ring-slate-700 transition-colors hover:bg-slate-800"><Grid2X2 size={18} />MyFinancial{expanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}</button><div className={`overflow-hidden transition-all duration-[900ms] ease-out ${expanded ? "max-h-[82vh]" : "max-h-0"}`}><ExpandedContent entries={entries} onAdd={onAdd} mode={mode} setMode={setMode} /></div></section>;
}
