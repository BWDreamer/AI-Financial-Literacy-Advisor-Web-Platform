import { ArrowLeft, ArrowRight, Check, ChevronRight, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { updateOnboardingCompleted, type User } from "../api/auth";
import { createAsset, createDebt, createRecurringCashFlow, type AssetType, type DebtInput, type RecurringCashFlowInput } from "../api/financials";
import { createMemory, type MemoryCategory } from "../api/memory";

type SnapshotValues = {
  monthlyIncome: string;
  otherIncome: string;
  monthlyExpenses: string;
  cashSavings: string;
  cash: string;
  bankSavings: string;
  stocks: string;
  superannuation: string;
  property: string;
  vehicle: string;
  otherAssets: string;
  creditCardDebt: string;
  personalLoan: string;
  studentLoan: string;
  mortgage: string;
  otherDebt: string;
};

type AnswerSet = { selected: string[]; other: string };
type SingleAnswer = { selected: string; other: string };
type SnapshotAssetInput = { asset_type: AssetType; name: string; amount: number };

type OnboardingState = {
  focusAreas: AnswerSet;
  confidence: SingleAnswer;
  explanationStyle: AnswerSet;
  concerns: AnswerSet;
  planningStyle: SingleAnswer;
  advisorHelp: AnswerSet;
  advisorAvoid: AnswerSet;
  snapshot: SnapshotValues;
};

type OnboardingOverlayProps = {
  user: User;
  onFinished: (user: User) => void;
};

const emptySet: AnswerSet = { selected: [], other: "" };
const emptySingle: SingleAnswer = { selected: "", other: "" };

const initialSnapshot: SnapshotValues = {
  monthlyIncome: "",
  otherIncome: "",
  monthlyExpenses: "",
  cashSavings: "",
  cash: "",
  bankSavings: "",
  stocks: "",
  superannuation: "",
  property: "",
  vehicle: "",
  otherAssets: "",
  creditCardDebt: "",
  personalLoan: "",
  studentLoan: "",
  mortgage: "",
  otherDebt: "",
};

const initialState: OnboardingState = {
  focusAreas: emptySet,
  confidence: emptySingle,
  explanationStyle: emptySet,
  concerns: emptySet,
  planningStyle: emptySingle,
  advisorHelp: emptySet,
  advisorAvoid: emptySet,
  snapshot: initialSnapshot,
};

const focusOptions = ["Understand where my money goes", "Save more consistently", "Build a cash buffer", "Pay down debt", "Learn finance basics", "Understand tax or super", "Make better everyday money decisions", "Feel less stressed about money"];
const confidenceOptions = ["I'm just getting started", "I know the basics", "I'm comfortable but want a second opinion", "I'm not sure"];
const explanationOptions = ["Use simple language", "Give me clear next steps", "Show examples", "Use charts and summaries", "Keep it short", "Go deeper when needed", "Avoid jargon"];
const concernOptions = ["Unexpected bills", "Running out before payday", "Debt pressure", "Irregular income", "Not saving enough", "Not knowing what to do first", "Making a wrong decision"];
const planningOptions = ["Calm and low-pressure", "Balanced and realistic", "Practical and action-focused", "Detailed when needed"];
const advisorHelpOptions = ["Explain concepts in plain language", "Ask me follow-up questions", "Give me action steps", "Warn me about risks", "Use charts or numbers", "Keep answers short", "Avoid professional jargon"];
const advisorAvoidOptions = ["Too much technical language", "Aggressive saving targets", "Assuming I want to invest", "Long complicated answers", "Repeatedly asking for the same information"];
const steps = ["Welcome", "Reasons", "Guidance", "Concerns", "Snapshot", "Review"];

function parseAmount(value: string) {
  const amount = Number(value);
  return Number.isFinite(amount) && amount > 0 ? amount : 0;
}

function toggleValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function answerValues(answer: AnswerSet) {
  return [...answer.selected, answer.other.trim()].filter(Boolean);
}

function singleAnswerValue(answer: SingleAnswer) {
  return answer.selected === "Other" ? answer.other.trim() : answer.selected;
}

function isSetAnswered(answer: AnswerSet) {
  return answer.selected.length > 0 || Boolean(answer.other.trim());
}

function isSingleAnswered(answer: SingleAnswer) {
  return answer.selected && (answer.selected !== "Other" || Boolean(answer.other.trim()));
}

function sentenceList(values: string[]) {
  if (!values.length) return "";
  if (values.length === 1) return values[0].toLowerCase();
  return `${values.slice(0, -1).map((value) => value.toLowerCase()).join(", ")} and ${values[values.length - 1].toLowerCase()}`;
}

function buildMemoryFacts(state: OnboardingState) {
  const facts: { fact: string; category: MemoryCategory }[] = [];
  const focus = answerValues(state.focusAreas);
  const confidence = singleAnswerValue(state.confidence);
  const explanations = answerValues(state.explanationStyle);
  const concerns = answerValues(state.concerns);
  const planning = singleAnswerValue(state.planningStyle);
  const advisorHelp = answerValues(state.advisorHelp);
  const advisorAvoid = answerValues(state.advisorAvoid);

  if (focus.length) facts.push({ category: "preference", fact: `User is mainly interested in ${sentenceList(focus)}.` });
  if (confidence) facts.push({ category: "profile", fact: `User describes their financial confidence as: ${confidence}.` });
  if (explanations.length) facts.push({ category: "preference", fact: `User prefers ${sentenceList(explanations)} when learning about finance.` });
  if (concerns.length) facts.push({ category: "preference", fact: `User is currently concerned about ${sentenceList(concerns)}.` });
  if (planning) facts.push({ category: "preference", fact: `User prefers financial plans that feel ${planning.toLowerCase()}.` });
  if (advisorHelp.length) facts.push({ category: "preference", fact: `User wants FinanceAI to ${sentenceList(advisorHelp)}.` });
  if (advisorAvoid.length) facts.push({ category: "preference", fact: `User wants FinanceAI to avoid ${sentenceList(advisorAvoid)}.` });
  return facts;
}

function snapshotHasValues(snapshot: SnapshotValues) {
  return Object.values(snapshot).some((value) => parseAmount(value) > 0);
}

function Chip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`rounded-xl border px-3 py-2 text-left text-xs font-semibold leading-5 transition sm:rounded-2xl sm:px-4 sm:py-3 sm:text-sm ${selected ? "border-blue-600 bg-blue-600 text-white shadow-sm" : "border-slate-200 bg-white text-slate-700 hover:border-blue-200 hover:bg-blue-50"}`}>{label}</button>;
}

function OtherInput({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <input value={value} onChange={(event) => onChange(event.target.value)} placeholder="Please tell us more..." className="mt-3 w-full rounded-xl border border-blue-200 bg-blue-50/40 px-4 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 sm:py-3" />;
}

function MultiChoice({ options, answer, onChange }: { options: string[]; answer: AnswerSet; onChange: (answer: AnswerSet) => void }) {
  const otherSelected = answer.selected.includes("Other");
  return <>
    <div className="mt-4 grid gap-2.5 sm:mt-5 sm:grid-cols-2 sm:gap-3 lg:grid-cols-3">
      {[...options, "Other"].map((option) => <Chip key={option} label={option} selected={answer.selected.includes(option)} onClick={() => onChange({ ...answer, selected: toggleValue(answer.selected, option) })} />)}
    </div>
    {otherSelected && <OtherInput value={answer.other} onChange={(other) => onChange({ ...answer, other })} />}
  </>;
}

function SingleChoice({ options, answer, onChange }: { options: string[]; answer: SingleAnswer; onChange: (answer: SingleAnswer) => void }) {
  return <>
    <div className="mt-4 grid gap-2.5 sm:mt-5 sm:grid-cols-2 sm:gap-3 lg:grid-cols-3">
      {[...options, "Other"].map((option) => <Chip key={option} label={option} selected={answer.selected === option} onClick={() => onChange({ ...answer, selected: option })} />)}
    </div>
    {answer.selected === "Other" && <OtherInput value={answer.other} onChange={(other) => onChange({ ...answer, other })} />}
  </>;
}

function AmountInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block"><span className="text-sm font-semibold text-slate-700">{label}</span><input type="number" min="0" step="1" value={value} onChange={(event) => onChange(event.target.value)} placeholder="0" className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" /></label>;
}

function PrimaryAction({ children, onClick, disabled = false }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 sm:w-auto sm:px-5 sm:py-3 sm:text-sm">{children}</button>;
}

function SecondaryAction({ children, onClick, disabled = false }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:px-5 sm:py-3 sm:text-sm">{children}</button>;
}

async function saveMemoryFacts(state: OnboardingState) {
  const facts = buildMemoryFacts(state);
  await Promise.all(facts.map((fact) => createMemory(fact)));
}

async function saveFinancialSnapshot(snapshot: SnapshotValues) {
  const today = new Date().toISOString().slice(0, 10);
  const cashSavings = parseAmount(snapshot.cashSavings);
  const cash = parseAmount(snapshot.cash);
  const bankSavings = parseAmount(snapshot.bankSavings);
  const assets = ([
    { asset_type: "cash", name: "Cash savings", amount: cashSavings + cash + bankSavings },
    { asset_type: "stocks", name: "Stocks / ETFs", amount: parseAmount(snapshot.stocks) },
    { asset_type: "others", name: "Superannuation", amount: parseAmount(snapshot.superannuation) },
    { asset_type: "property", name: "Property", amount: parseAmount(snapshot.property) },
    { asset_type: "vehicle", name: "Vehicle", amount: parseAmount(snapshot.vehicle) },
    { asset_type: "others", name: "Other assets", amount: parseAmount(snapshot.otherAssets) },
  ] satisfies SnapshotAssetInput[]).filter((asset) => asset.amount > 0);
  const debts = ([
    { debt_type: "credit_card", name: "Credit card debt", balance: parseAmount(snapshot.creditCardDebt) },
    { debt_type: "personal_loan", name: "Personal loan", balance: parseAmount(snapshot.personalLoan) },
    { debt_type: "student_loan", name: "Student loan", balance: parseAmount(snapshot.studentLoan) },
    { debt_type: "mortgage", name: "Mortgage", balance: parseAmount(snapshot.mortgage) },
    { debt_type: "other", name: "Other debt", balance: parseAmount(snapshot.otherDebt) },
  ] satisfies DebtInput[]).filter((debt) => debt.balance > 0);
  const recurringCashFlows = ([
    { flow_type: "income", name: "Monthly income after tax", amount: parseAmount(snapshot.monthlyIncome), frequency: "monthly", start_date: today, category: "salary" },
    { flow_type: "income", name: "Other monthly income", amount: parseAmount(snapshot.otherIncome), frequency: "monthly", start_date: today, category: "other_income" },
    { flow_type: "expense", name: "Monthly expenses", amount: parseAmount(snapshot.monthlyExpenses), frequency: "monthly", start_date: today, category: "living_expenses" },
  ] satisfies RecurringCashFlowInput[]).filter((flow) => flow.amount > 0);
  await Promise.all([
    ...assets.map((asset) => createAsset(asset)),
    ...debts.map((debt) => createDebt(debt)),
    ...recurringCashFlows.map((flow) => createRecurringCashFlow(flow)),
  ]);
}

export default function OnboardingOverlay({ user, onFinished }: OnboardingOverlayProps) {
  const [step, setStep] = useState(0);
  const [state, setState] = useState<OnboardingState>(initialState);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const progress = Math.round((step / (steps.length - 1)) * 100);
  const review = useMemo(() => ({
    focus: answerValues(state.focusAreas).join(", ") || "Skipped",
    style: [singleAnswerValue(state.confidence), ...answerValues(state.explanationStyle)].filter(Boolean).join(", ") || "Skipped",
    concerns: answerValues(state.concerns).join(", ") || "Skipped",
    advisor: [...answerValues(state.explanationStyle), singleAnswerValue(state.planningStyle) ? `Plans should feel ${singleAnswerValue(state.planningStyle).toLowerCase()}` : ""].filter(Boolean).join(", ") || "Skipped",
    snapshot: snapshotHasValues(state.snapshot) ? "Financial snapshot added" : "Skipped",
  }), [state]);

  const canContinue = step === 0
    || step === 4
    || step === 5
    || (step === 1 && isSetAnswered(state.focusAreas))
    || (step === 2 && isSingleAnswered(state.confidence) && isSetAnswered(state.explanationStyle))
    || (step === 3 && isSetAnswered(state.concerns) && isSingleAnswered(state.planningStyle))
    ;

  function updateSnapshot(key: keyof SnapshotValues, value: string) {
    setState((current) => ({ ...current, snapshot: { ...current.snapshot, [key]: value } }));
  }

  async function finishSetup() {
    setSaving(true);
    setError("");
    try {
      await saveMemoryFacts(state);
      if (snapshotHasValues(state.snapshot)) await saveFinancialSnapshot(state.snapshot);
      const updatedUser = await updateOnboardingCompleted(true);
      onFinished(updatedUser);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save setup. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function skipSetup() {
    setSaving(true);
    setError("");
    try {
      const updatedUser = await updateOnboardingCompleted(true);
      onFinished(updatedUser);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to skip setup. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return <div className="fixed inset-0 z-[80] grid place-items-center overflow-hidden bg-slate-950/20 px-3 py-3 backdrop-blur-sm sm:px-4 sm:py-6">
    <section className="mx-auto flex h-[calc(100dvh-1.5rem)] w-full max-w-4xl animate-[slideDownFade_420ms_ease-out] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl sm:h-auto sm:max-h-[calc(100dvh-3rem)]">
      <header className="shrink-0 rounded-t-3xl bg-slate-950 p-3.5 text-white sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-blue-500/20 px-3 py-1 text-[0.65rem] font-bold uppercase tracking-[0.2em] text-blue-100 sm:text-xs"><Sparkles size={13} /> FinanceAI Setup</p>
            <h1 className="mt-3 text-xl font-bold tracking-tight sm:mt-4 sm:text-3xl">Welcome to FinanceAI</h1>
            <p className="mt-1.5 max-w-2xl text-xs leading-5 text-slate-300 sm:mt-2 sm:text-sm sm:leading-6">A few quick questions help us make your dashboard and advisor feel more useful from the start.</p>
          </div>
          <div className="flex shrink-0 items-center justify-between gap-3 sm:flex-col sm:items-end sm:gap-2">
            <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-bold text-slate-200">{step === 0 ? "Welcome" : `Step ${step} of 5`}</span>
            <button type="button" onClick={() => void skipSetup()} disabled={saving} className="text-xs font-semibold text-slate-300 underline-offset-4 hover:text-white hover:underline disabled:cursor-not-allowed disabled:opacity-60">
              Skip setup
            </button>
          </div>
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10 sm:mt-5 sm:h-2"><div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} /></div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-7">
        {error && <p className="mb-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {step === 0 && <section><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600 sm:text-sm">Quick start</p><h2 className="mt-3 text-xl font-bold leading-snug text-slate-950 sm:text-2xl">Let's make FinanceAI useful for your real life.</h2><p className="mt-4 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">You can share rough preferences and estimates. We will not ask you to set goals or deadlines here.</p><div className="mt-8 flex justify-end"><button type="button" onClick={() => setStep(1)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-700">Start Setup <ArrowRight size={16} /></button></div></section>}
        {step === 1 && <section><h2 className="text-2xl font-bold text-slate-950">What brings you to FinanceAI?</h2><p className="mt-2 text-slate-500">Pick the reasons that feel closest to what you need right now.</p><MultiChoice options={focusOptions} answer={state.focusAreas} onChange={(focusAreas) => setState({ ...state, focusAreas })} /></section>}
        {step === 2 && <section><h2 className="text-2xl font-bold text-slate-950">How should FinanceAI explain things?</h2><h3 className="mt-5 font-bold text-slate-900">How familiar do you feel with money topics?</h3><SingleChoice options={confidenceOptions} answer={state.confidence} onChange={(confidence) => setState({ ...state, confidence })} /><h3 className="mt-7 font-bold text-slate-900">What makes advice easier to use?</h3><MultiChoice options={explanationOptions} answer={state.explanationStyle} onChange={(explanationStyle) => setState({ ...state, explanationStyle })} /></section>}
        {step === 3 && <section><h2 className="text-2xl font-bold text-slate-950">What feels most pressing?</h2><p className="mt-2 text-slate-500">This helps the advisor avoid generic advice and focus on what matters.</p><h3 className="mt-5 font-bold text-slate-900">What is on your mind right now?</h3><MultiChoice options={concernOptions} answer={state.concerns} onChange={(concerns) => setState({ ...state, concerns })} /><h3 className="mt-7 font-bold text-slate-900">How should plans feel?</h3><SingleChoice options={planningOptions} answer={state.planningStyle} onChange={(planningStyle) => setState({ ...state, planningStyle })} /></section>}
        {step === 4 && <section><h2 className="text-2xl font-bold text-slate-950">Add a quick financial snapshot</h2><p className="mt-2 text-slate-500">Rough estimates are fine. These numbers update your homepage, not your long-term memory. Monthly amounts are stored as ongoing cash flow so they stay separate from one-off transactions.</p><div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><AmountInput label="Monthly income after tax" value={state.snapshot.monthlyIncome} onChange={(value) => updateSnapshot("monthlyIncome", value)} /><AmountInput label="Other monthly income" value={state.snapshot.otherIncome} onChange={(value) => updateSnapshot("otherIncome", value)} /><AmountInput label="Monthly expenses" value={state.snapshot.monthlyExpenses} onChange={(value) => updateSnapshot("monthlyExpenses", value)} /><AmountInput label="Cash savings" value={state.snapshot.cashSavings} onChange={(value) => updateSnapshot("cashSavings", value)} /><AmountInput label="Cash" value={state.snapshot.cash} onChange={(value) => updateSnapshot("cash", value)} /><AmountInput label="Bank savings" value={state.snapshot.bankSavings} onChange={(value) => updateSnapshot("bankSavings", value)} /><AmountInput label="Stocks / ETFs" value={state.snapshot.stocks} onChange={(value) => updateSnapshot("stocks", value)} /><AmountInput label="Superannuation" value={state.snapshot.superannuation} onChange={(value) => updateSnapshot("superannuation", value)} /><AmountInput label="Property" value={state.snapshot.property} onChange={(value) => updateSnapshot("property", value)} /><AmountInput label="Vehicle" value={state.snapshot.vehicle} onChange={(value) => updateSnapshot("vehicle", value)} /><AmountInput label="Other assets" value={state.snapshot.otherAssets} onChange={(value) => updateSnapshot("otherAssets", value)} /></div><div className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4"><p className="text-sm font-bold text-slate-700">Debts / liabilities</p><p className="mt-1 text-sm leading-6 text-slate-500">Any balances you add here are included in your homepage debt total and net worth.</p><div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><AmountInput label="Credit card debt" value={state.snapshot.creditCardDebt} onChange={(value) => updateSnapshot("creditCardDebt", value)} /><AmountInput label="Personal loan" value={state.snapshot.personalLoan} onChange={(value) => updateSnapshot("personalLoan", value)} /><AmountInput label="Student loan" value={state.snapshot.studentLoan} onChange={(value) => updateSnapshot("studentLoan", value)} /><AmountInput label="Mortgage" value={state.snapshot.mortgage} onChange={(value) => updateSnapshot("mortgage", value)} /><AmountInput label="Other debt" value={state.snapshot.otherDebt} onChange={(value) => updateSnapshot("otherDebt", value)} /></div></div></section>}
        {step === 5 && <section><h2 className="text-2xl font-bold text-slate-950">Review and finish</h2><div className="mt-5 grid gap-4 md:grid-cols-2">{[["Why you're here", review.focus], ["Guidance style", review.style], ["What's pressing", review.concerns], ["Plan preferences", review.advisor], ["Financial snapshot", review.snapshot]].map(([label, value]) => <article key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-5"><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{label}</p><p className="mt-3 text-sm leading-6 text-slate-700">{value}</p></article>)}</div></section>}
      </div>

      {step > 0 && <footer className="shrink-0 border-t border-slate-100 bg-white p-2.5 sm:p-6"><div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between"><div className="flex flex-col gap-2 sm:flex-row sm:gap-3"><SecondaryAction onClick={() => setStep((current) => Math.max(current - 1, 0))} disabled={saving}><ArrowLeft size={16} /> Back</SecondaryAction>{step < 5 && <SecondaryAction onClick={() => setStep((current) => Math.min(current + 1, 5))} disabled={saving}>Skip this step</SecondaryAction>}</div>{step < 5 ? <PrimaryAction onClick={() => setStep((current) => Math.min(current + 1, 5))} disabled={!canContinue || saving}>Next <ChevronRight size={16} /></PrimaryAction> : <PrimaryAction onClick={() => void finishSetup()} disabled={saving}>{saving ? "Saving..." : "Finish Setup"} <Check size={16} /></PrimaryAction>}</div></footer>}
    </section>
  </div>;
}
