import { useEffect, useState } from "react";
import { Financials, FinancialSummary, getFinancials, getFinancialSummary } from "../api/financials";

const money = (value: number) => new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" }).format(value);

export default function HomePage() {
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [financials, setFinancials] = useState<Financials | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getFinancialSummary(), getFinancials()])
      .then(([nextSummary, nextFinancials]) => { setSummary(nextSummary); setFinancials(nextFinancials); })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load financial data."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <main className="p-10 text-slate-500">Loading your financial dashboard...</main>;
  if (error) return <main className="p-10"><p className="rounded-xl bg-red-50 p-4 text-red-700">{error}</p></main>;
  if (!summary || !financials) return null;

  const cards = [
    ["Net worth", summary.net_worth], ["Cash savings", summary.cash_savings],
    ["Monthly income", summary.monthly_income], ["Monthly expenses", summary.monthly_expenses],
  ] as const;

  return <main className="space-y-8 p-10">
    <div><h1 className="text-3xl font-bold tracking-tight">Financial Dashboard</h1><p className="mt-2 text-slate-500">A summary of your saved financial records.</p></div>
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value]) => <article key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{money(Number(value))}</p></article>)}</section>
    <section className="grid gap-6 lg:grid-cols-2">
      <article className="rounded-2xl border border-slate-200 bg-white p-6"><h2 className="text-lg font-bold">Assets</h2>{financials.assets.length === 0 ? <p className="mt-4 text-sm text-slate-500">No assets have been added yet.</p> : <ul className="mt-4 divide-y divide-slate-100">{financials.assets.map((asset) => <li key={asset.id} className="flex justify-between py-3"><span>{asset.name}<small className="ml-2 text-slate-400">{asset.asset_type}</small></span><strong>{money(Number(asset.amount))}</strong></li>)}</ul>}</article>
      <article className="rounded-2xl border border-slate-200 bg-white p-6"><h2 className="text-lg font-bold">Recent cash flows</h2>{summary.recent_cash_flows.length === 0 ? <p className="mt-4 text-sm text-slate-500">No income or expenses have been added yet.</p> : <ul className="mt-4 divide-y divide-slate-100">{summary.recent_cash_flows.map((flow) => <li key={flow.id} className="flex justify-between py-3"><span>{flow.name}<small className="ml-2 text-slate-400">{flow.date}</small></span><strong className={flow.flow_type === "income" ? "text-emerald-600" : "text-red-600"}>{flow.flow_type === "income" ? "+" : "-"}{money(Number(flow.amount))}</strong></li>)}</ul>}</article>
    </section>
  </main>;
}
