import { FormEvent, useState } from "react";
import { Banknote, ChevronDown, ChevronUp, CreditCard, Grid2X2, Home, Plus } from "lucide-react";
import { AssetType, CashFlowType, DebtType, FinancialEntry, Frequency, assetLabels, debtLabels, money, todayInputValue } from "../utils/financials";
import type { FinancialSummary } from "../api/financials";
import DatePicker from "./DatePicker";
import FormInput from "./FormInput";
import PrimaryButton from "./PrimaryButton";

type Props = { summary?: FinancialSummary | null; onAdd: (entry: FinancialEntry) => void };
type AddMode = "asset" | "debt" | "cashflow";
type ActiveMode = AddMode | null;

const assetOptions: AssetType[] = ["cash", "stocks", "bonds", "property", "vehicle", "others"];
const debtOptions: DebtType[] = ["mortgage", "car_loan", "personal_loan", "credit_card", "student_loan", "bnpl", "tax_debt", "other"];
const frequencies: Frequency[] = ["once", "weekly", "fortnightly", "monthly", "yearly"];
const selectClass = "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

function modeTotal(mode: AddMode, summary?: FinancialSummary | null) {
  if (mode === "asset") return Number(summary?.total_assets ?? 0);
  if (mode === "debt") return Number(summary?.total_debts ?? 0);
  return Number(summary?.monthly_cash_flow ?? 0);
}

function SummaryCard({ mode, summary, active, onClick }: { mode: AddMode; summary?: FinancialSummary | null; active: boolean; onClick: () => void }) {
  const meta = {
    asset: { label: "Assets", helper: "Total assets", icon: Home, tone: "bg-blue-100 text-blue-600" },
    debt: { label: "Debt", helper: "Total debt", icon: CreditCard, tone: "bg-red-100 text-red-600" },
    cashflow: { label: "Cash Flow", helper: "Monthly net cash flow", icon: Banknote, tone: "bg-emerald-100 text-emerald-600" },
  }[mode];
  const Icon = meta.icon;
  return <button type="button" onClick={onClick} className={`rounded-2xl border border-dashed p-4 text-left transition ${active ? "border-blue-400 bg-blue-50" : "border-slate-300 bg-white hover:border-blue-300"}`}><div className="flex items-center justify-between"><span className="flex items-center gap-3 font-bold text-slate-900"><span className={`grid size-10 place-items-center rounded-full ${meta.tone}`}><Icon size={20} /></span>{meta.label}</span><Plus size={18} className="text-blue-600" /></div><p className="mt-3 text-2xl font-bold">{money(modeTotal(mode, summary))}</p><p className="text-xs text-slate-500">{meta.helper}</p></button>;
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

function DebtForm({ onAdd }: { onAdd: Props["onAdd"] }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    onAdd({ id: crypto.randomUUID(), kind: "debt", debtType: String(form.get("debtType")) as DebtType, name: String(form.get("name")), balance: Number(form.get("balance")) || 0, minimumPayment: Number(form.get("minimumPayment")) || undefined, interestRate: Number(form.get("interestRate")) || undefined, createdAt: new Date().toISOString() });
    event.currentTarget.reset();
  }
  return <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><label><span className="mb-2 block text-sm font-medium text-slate-700">Debt Type</span><select name="debtType" className={selectClass}>{debtOptions.map((item) => <option key={item} value={item}>{debtLabels[item]}</option>)}</select></label><FormInput id="debt-name" name="name" label="Name" required /><FormInput id="debt-balance" name="balance" type="number" min="0" step="0.01" label="Balance" required /><FormInput id="debt-payment" name="minimumPayment" type="number" min="0" step="0.01" label="Min Monthly Payment" /><FormInput id="debt-rate" name="interestRate" type="number" min="0" step="0.01" label="Interest Rate %" /><div className="flex items-end lg:col-start-5"><Actions label="Create Debt" /></div></form>;
}

function CashFlowForm({ onAdd }: { onAdd: Props["onAdd"] }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const frequency = String(form.get("frequency")) as Frequency;
    const base = { flowType: String(form.get("flowType")) as CashFlowType, name: String(form.get("name")), amount: Number(form.get("amount")) || 0, createdAt: new Date().toISOString() };
    if (frequency === "once") onAdd({ id: crypto.randomUUID(), kind: "cashflow", ...base, date: String(form.get("date")) });
    else onAdd({ id: crypto.randomUUID(), kind: "recurring", ...base, frequency, startDate: String(form.get("date")), createdAt: new Date().toISOString() });
    event.currentTarget.reset();
  }
  return <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6"><label><span className="mb-2 block text-sm font-medium text-slate-700">Type</span><select name="flowType" className={selectClass}><option value="income">Income</option><option value="expense">Expense</option></select></label><label><span className="mb-2 block text-sm font-medium text-slate-700">Frequency</span><select name="frequency" className={selectClass}>{frequencies.map((item) => <option key={item} value={item}>{item === "once" ? "One-off" : item[0].toUpperCase() + item.slice(1)}</option>)}</select></label><FormInput id="flow-name" name="name" label="Name" required /><DatePicker id="flow-date" name="date" label="Date / Start Date" defaultValue={todayInputValue()} min="2000-01-01" max={todayInputValue()} placement="top" /><FormInput id="flow-amount" name="amount" type="number" min="0" step="0.01" label="Amount" required /><div className="flex items-end"><Actions label="Create Cash Flow" /></div></form>;
}

function ExpandedContent({ summary, onAdd, mode, setMode }: { summary?: FinancialSummary | null; onAdd: Props["onAdd"]; mode: ActiveMode; setMode: (mode: ActiveMode) => void }) {
  const toggle = (next: AddMode) => setMode(mode === next ? null : next);
  return <div className="max-h-[78vh] overflow-y-auto rounded-t-3xl border border-slate-200 bg-white p-3 shadow-2xl transition-all duration-[900ms] ease-out sm:p-5"><div className="grid gap-4 md:grid-cols-3"><SummaryCard mode="asset" summary={summary} active={mode === "asset"} onClick={() => toggle("asset")} /><SummaryCard mode="debt" summary={summary} active={mode === "debt"} onClick={() => toggle("debt")} /><SummaryCard mode="cashflow" summary={summary} active={mode === "cashflow"} onClick={() => toggle("cashflow")} /></div><div className={`transition-all duration-[900ms] ease-out ${mode ? "mt-5 max-h-[34rem] overflow-visible" : "max-h-0 overflow-hidden"}`}><div className="rounded-2xl bg-slate-50 p-3 sm:p-4">{mode === "asset" && <AssetForm onAdd={onAdd} />}{mode === "debt" && <DebtForm onAdd={onAdd} />}{mode === "cashflow" && <CashFlowForm onAdd={onAdd} />}</div></div></div>;
}

export default function MyFinancialsPanel({ summary, onAdd }: Props) {
  const [expanded, setExpanded] = useState(false); const [mode, setMode] = useState<ActiveMode>(null);
  return <section className="sticky bottom-0 z-30 mx-auto max-w-5xl px-2 sm:px-4"><button type="button" onClick={() => setExpanded((value) => !value)} className="mx-auto flex w-[min(18rem,calc(100vw-1rem))] items-center justify-center gap-3 rounded-t-2xl bg-blue-600 px-4 py-3 text-sm font-bold text-white shadow-xl ring-2 ring-blue-300 transition-colors hover:bg-blue-700"><Grid2X2 size={18} />MyFinancial{expanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}</button><div className={`overflow-hidden transition-all duration-[900ms] ease-out ${expanded ? "max-h-[82vh]" : "max-h-0"}`}><ExpandedContent summary={summary} onAdd={onAdd} mode={mode} setMode={setMode} /></div></section>;
}
