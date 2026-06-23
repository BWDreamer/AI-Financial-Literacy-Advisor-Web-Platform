import { FormEvent, useState } from "react";
import { calculateCompoundInterest } from "../api/calculators";
import { BudgetInput, calculateAustralianTax, calculateBudget, calculateLoan } from "../utils/calculators";
import Modal from "./Modal";
import PrimaryButton from "./PrimaryButton";

export type CalculatorType = "budget" | "compound" | "loan" | "tax";
type ResultItem = { label: string; value: string };

const titles: Record<CalculatorType, string> = {
  budget: "Budget Calculator",
  compound: "Compound Interest Calculator",
  loan: "Loan Repayment Calculator",
  tax: "Australian Tax Estimator",
};

const budgetFields = [
  ["income", "Monthly take-home income"], ["housing", "Housing"],
  ["utilities", "Utilities"], ["groceries", "Groceries"],
  ["transport", "Transport"], ["insurance", "Insurance and healthcare"],
  ["debt", "Debt repayments"], ["savings", "Savings allocation"],
  ["other", "Other expenses"],
] as const;

const money = (value: number) => new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" }).format(value);
const numberFrom = (form: FormData, key: string) => Number(form.get(key)) || 0;

function NumberField({ name, label, defaultValue = 0, step = "0.01" }: { name: string; label: string; defaultValue?: number; step?: string }) {
  return <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>
    <input name={name} type="number" min="0" step={step} defaultValue={defaultValue} required className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />
  </label>;
}

function Results({ items }: { items: ResultItem[] }) {
  return <dl className="mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-slate-50 p-4">
    {items.map((item) => <div key={item.label}><dt className="text-xs text-slate-500">{item.label}</dt><dd className="mt-1 font-semibold text-slate-900">{item.value}</dd></div>)}
  </dl>;
}

function BudgetCalculator() {
  const [results, setResults] = useState<ResultItem[]>([]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const input = Object.fromEntries(budgetFields.map(([key]) => [key, numberFrom(form, key)])) as BudgetInput;
    const value = calculateBudget(input);
    setResults([
      { label: "Total allocated", value: money(value.totalAllocated) },
      { label: "Remaining balance", value: money(value.remaining) },
      { label: "Expense ratio", value: `${value.expenseRatio.toFixed(1)}%` },
      { label: "Savings rate", value: `${value.savingsRate.toFixed(1)}%` },
    ]);
  }
  return <form onSubmit={submit}><div className="grid grid-cols-2 gap-4">{budgetFields.map(([name, label]) => <NumberField key={name} name={name} label={label} />)}</div>
    <PrimaryButton className="mt-5" type="submit">Calculate Budget</PrimaryButton>{results.length > 0 && <Results items={results} />}
  </form>;
}

function CompoundCalculator() {
  const [results, setResults] = useState<ResultItem[]>([]);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    setLoading(true); setError("");
    try {
      const value = await calculateCompoundInterest({ principal: numberFrom(form, "principal"), annual_interest_rate: numberFrom(form, "rate"), years: numberFrom(form, "years"), compounds_per_year: numberFrom(form, "frequency") });
      setResults([{ label: "Principal", value: money(value.principal) }, { label: "Final amount", value: money(value.final_amount) }, { label: "Interest earned", value: money(value.interest_earned) }]);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to calculate compound interest."); }
    finally { setLoading(false); }
  }
  return <form onSubmit={submit} className="space-y-4"><NumberField name="principal" label="Principal" /><NumberField name="rate" label="Annual interest rate (%)" /><NumberField name="years" label="Investment period (years)" /><NumberField name="frequency" label="Compounds per year" defaultValue={12} step="1" />
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}<PrimaryButton type="submit" disabled={loading}>{loading ? "Calculating..." : "Calculate Interest"}</PrimaryButton>{results.length > 0 && <Results items={results} />}
  </form>;
}

function LoanCalculator() {
  const [results, setResults] = useState<ResultItem[]>([]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const value = calculateLoan(numberFrom(form, "principal"), numberFrom(form, "rate"), numberFrom(form, "years"));
    setResults([{ label: "Monthly repayment", value: money(value.monthlyPayment) }, { label: "Total repayment", value: money(value.totalRepayment) }, { label: "Total interest", value: money(value.totalInterest) }, { label: "Payment count", value: String(value.payments) }]);
  }
  return <form onSubmit={submit} className="space-y-4"><NumberField name="principal" label="Loan amount" /><NumberField name="rate" label="Annual interest rate (%)" /><NumberField name="years" label="Loan term (years)" />
    <PrimaryButton type="submit">Calculate Repayment</PrimaryButton>{results.length > 0 && <Results items={results} />}
  </form>;
}

function TaxCalculator() {
  const [results, setResults] = useState<ResultItem[]>([]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const value = calculateAustralianTax(numberFrom(form, "income"), numberFrom(form, "deductions"));
    setResults([{ label: "Taxable income", value: money(value.taxableIncome) }, { label: "Income Tax", value: money(value.incomeTax) }, { label: "Medicare Levy", value: money(value.medicare) }, { label: "Total Tax", value: money(value.totalTax) }, { label: "After-tax income", value: money(value.afterTaxIncome) }, { label: "Effective rate", value: `${value.effectiveRate.toFixed(1)}%` }]);
  }
  return <form onSubmit={submit} className="space-y-4"><NumberField name="income" label="Annual gross income" /><NumberField name="deductions" label="Allowable deductions" />
    <p className="text-xs leading-5 text-slate-500">Estimate for a full-year Australian resident, single with no dependants, for 2025–26. Medicare Levy Surcharge is excluded. This is not tax advice.</p>
    <PrimaryButton type="submit">Estimate Tax</PrimaryButton>{results.length > 0 && <Results items={results} />}
  </form>;
}

export default function CalculatorModal({ type, onClose }: { type: CalculatorType; onClose: () => void }) {
  const calculators = { budget: <BudgetCalculator />, compound: <CompoundCalculator />, loan: <LoanCalculator />, tax: <TaxCalculator /> };
  return <Modal title={titles[type]} onClose={onClose} wide={type === "budget"}>{calculators[type]}</Modal>;
}
