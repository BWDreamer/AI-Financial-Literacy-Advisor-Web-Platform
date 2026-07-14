import { ArrowLeft, ArrowRight, Check, ChevronRight, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { updateOnboardingCompleted, type User } from "../api/auth";
import { createAsset, createCashFlow, type AssetType } from "../api/financials";
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

const focusOptions = ["Budgeting", "Saving money", "Understanding spending", "Building an emergency fund", "Paying off debt", "Superannuation basics", "Tax basics", "Learning financial concepts", "General financial wellbeing"];
const confidenceOptions = ["Beginner - I need simple explanations", "Intermediate - I know the basics", "Confident - I want deeper analysis", "Not sure"];
const explanationOptions = ["Simple language", "Step-by-step guidance", "Examples", "Charts and summaries", "Short answers", "Detailed explanations"];
const concernOptions = ["Running out of money before payday", "Unexpected expenses", "Job loss or unstable income", "Debt pressure", "Not saving enough", "Not understanding where money goes", "Making wrong financial decisions"];
const planningOptions = ["Conservative and safe", "Balanced and realistic", "More ambitious", "Low-pressure and flexible"];
const advisorHelpOptions = ["Explain concepts in plain language", "Ask me follow-up questions", "Give me action steps", "Warn me about risks", "Use charts or numbers", "Keep answers short", "Avoid professional jargon"];
const advisorAvoidOptions = ["Too much technical language", "Aggressive saving targets", "Assuming I want to invest", "Long complicated answers", "Repeatedly asking for the same information"];
const steps = ["Welcome", "Focus", "Style", "Concerns", "Advisor", "Snapshot", "Review"];

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
  if (advisorHelp.length) facts.push({ category: "preference", fact: `User wants the AI advisor to ${sentenceList(advisorHelp)}.` });
  if (advisorAvoid.length) facts.push({ category: "preference", fact: `User wants the AI advisor to avoid ${sentenceList(advisorAvoid)}.` });
  return facts;
}

function snapshotHasValues(snapshot: SnapshotValues) {
  return Object.values(snapshot).some((value) => parseAmount(value) > 0);
}

function Chip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`rounded-2xl border px-4 py-3 text-left text-sm font-semibold transition ${selected ? "border-blue-600 bg-blue-600 text-white shadow-sm" : "border-slate-200 bg-white text-slate-700 hover:border-blue-200 hover:bg-blue-50"}`}>{label}</button>;
}

function OtherInput({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <input value={value} onChange={(event) => onChange(event.target.value)} placeholder="Please tell us more..." className="mt-3 w-full rounded-xl border border-blue-200 bg-blue-50/40 px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />;
}

function MultiChoice({ options, answer, onChange }: { options: string[]; answer: AnswerSet; onChange: (answer: AnswerSet) => void }) {
  const otherSelected = answer.selected.includes("Other");
  return <>
    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {[...options, "Other"].map((option) => <Chip key={option} label={option} selected={answer.selected.includes(option)} onClick={() => onChange({ ...answer, selected: toggleValue(answer.selected, option) })} />)}
    </div>
    {otherSelected && <OtherInput value={answer.other} onChange={(other) => onChange({ ...answer, other })} />}
  </>;
}

function SingleChoice({ options, answer, onChange }: { options: string[]; answer: SingleAnswer; onChange: (answer: SingleAnswer) => void }) {
  return <>
    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {[...options, "Other"].map((option) => <Chip key={option} label={option} selected={answer.selected === option} onClick={() => onChange({ ...answer, selected: option })} />)}
    </div>
    {answer.selected === "Other" && <OtherInput value={answer.other} onChange={(other) => onChange({ ...answer, other })} />}
  </>;
}

function AmountInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block"><span className="text-sm font-semibold text-slate-700">{label}</span><input type="number" min="0" step="1" value={value} onChange={(event) => onChange(event.target.value)} placeholder="0" className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" /></label>;
}

function PrimaryAction({ children, onClick, disabled = false }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400">{children}</button>;
}

function SecondaryAction({ children, onClick, disabled = false }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60">{children}</button>;
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
  const cashFlows = [
    { flow_type: "income" as const, name: "Monthly income after tax", amount: parseAmount(snapshot.monthlyIncome), date: today },
    { flow_type: "income" as const, name: "Other monthly income", amount: parseAmount(snapshot.otherIncome), date: today },
    { flow_type: "expense" as const, name: "Monthly expenses", amount: parseAmount(snapshot.monthlyExpenses), date: today },
  ].filter((flow) => flow.amount > 0);
  await Promise.all([...assets.map((asset) => createAsset(asset)), ...cashFlows.map((flow) => createCashFlow(flow))]);
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
    advisor: [...answerValues(state.advisorHelp), ...answerValues(state.advisorAvoid).map((item) => `Avoid: ${item}`)].join(", ") || "Skipped",
    snapshot: snapshotHasValues(state.snapshot) ? "Financial snapshot added" : "Skipped",
  }), [state]);

  const canContinue = step === 0
    || step === 5
    || step === 6
    || (step === 1 && isSetAnswered(state.focusAreas))
    || (step === 2 && isSingleAnswered(state.confidence) && isSetAnswered(state.explanationStyle))
    || (step === 3 && isSetAnswered(state.concerns) && isSingleAnswered(state.planningStyle))
    || (step === 4 && isSetAnswered(state.advisorHelp) && isSetAnswered(state.advisorAvoid));

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

  return <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/20 px-4 py-6 backdrop-blur-sm">
    <section className="mx-auto max-w-4xl animate-[slideDownFade_420ms_ease-out] rounded-3xl border border-slate-200 bg-white shadow-2xl">
      <header className="rounded-t-3xl bg-slate-950 p-5 text-white sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-blue-500/20 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-blue-100"><Sparkles size={14} /> FinanceAI Setup</p>
            <h1 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">Welcome to FinanceAI</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">We will ask a few quick questions to personalise your dashboard and AI advisor.</p>
          </div>
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-bold text-slate-200">{step === 0 ? "Welcome" : `Step ${step} of 6`}</span>
        </div>
        <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} /></div>
      </header>

      <div className="max-h-[calc(100vh-12rem)] overflow-y-auto p-5 sm:p-7">
        {error && <p className="mb-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {step === 0 && <section><p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-600">Quick start</p><h2 className="mt-3 text-2xl font-bold text-slate-950">Make FinanceAI feel more like yours.</h2><p className="mt-4 max-w-2xl leading-7 text-slate-600">This setup covers advisor preferences and a lightweight financial snapshot. It does not create goals or ask for target dates.</p><div className="mt-8 flex justify-end"><PrimaryAction onClick={() => setStep(1)}>Start Setup <ArrowRight size={18} /></PrimaryAction></div></section>}
        {step === 1 && <section><h2 className="text-2xl font-bold text-slate-950">What would you like help with?</h2><MultiChoice options={focusOptions} answer={state.focusAreas} onChange={(focusAreas) => setState({ ...state, focusAreas })} /></section>}
        {step === 2 && <section><h2 className="text-2xl font-bold text-slate-950">Financial confidence and explanation style</h2><h3 className="mt-5 font-bold text-slate-900">How confident do you feel?</h3><SingleChoice options={confidenceOptions} answer={state.confidence} onChange={(confidence) => setState({ ...state, confidence })} /><h3 className="mt-7 font-bold text-slate-900">What type of explanations do you prefer?</h3><MultiChoice options={explanationOptions} answer={state.explanationStyle} onChange={(explanationStyle) => setState({ ...state, explanationStyle })} /></section>}
        {step === 3 && <section><h2 className="text-2xl font-bold text-slate-950">Concerns and planning style</h2><h3 className="mt-5 font-bold text-slate-900">What are you most concerned about?</h3><MultiChoice options={concernOptions} answer={state.concerns} onChange={(concerns) => setState({ ...state, concerns })} /><h3 className="mt-7 font-bold text-slate-900">How would you like financial plans to feel?</h3><SingleChoice options={planningOptions} answer={state.planningStyle} onChange={(planningStyle) => setState({ ...state, planningStyle })} /></section>}
        {step === 4 && <section><h2 className="text-2xl font-bold text-slate-950">AI Advisor preferences</h2><h3 className="mt-5 font-bold text-slate-900">How should the AI advisor help you?</h3><MultiChoice options={advisorHelpOptions} answer={state.advisorHelp} onChange={(advisorHelp) => setState({ ...state, advisorHelp })} /><h3 className="mt-7 font-bold text-slate-900">What should the AI avoid?</h3><MultiChoice options={advisorAvoidOptions} answer={state.advisorAvoid} onChange={(advisorAvoid) => setState({ ...state, advisorAvoid })} /></section>}
        {step === 5 && <section><h2 className="text-2xl font-bold text-slate-950">Set up your financial snapshot</h2><p className="mt-2 text-slate-500">Amounts are saved as structured financial records, not long-term memory.</p><div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><AmountInput label="Monthly income after tax" value={state.snapshot.monthlyIncome} onChange={(value) => updateSnapshot("monthlyIncome", value)} /><AmountInput label="Other monthly income" value={state.snapshot.otherIncome} onChange={(value) => updateSnapshot("otherIncome", value)} /><AmountInput label="Monthly expenses" value={state.snapshot.monthlyExpenses} onChange={(value) => updateSnapshot("monthlyExpenses", value)} /><AmountInput label="Cash savings" value={state.snapshot.cashSavings} onChange={(value) => updateSnapshot("cashSavings", value)} /><AmountInput label="Cash" value={state.snapshot.cash} onChange={(value) => updateSnapshot("cash", value)} /><AmountInput label="Bank savings" value={state.snapshot.bankSavings} onChange={(value) => updateSnapshot("bankSavings", value)} /><AmountInput label="Stocks / ETFs" value={state.snapshot.stocks} onChange={(value) => updateSnapshot("stocks", value)} /><AmountInput label="Superannuation" value={state.snapshot.superannuation} onChange={(value) => updateSnapshot("superannuation", value)} /><AmountInput label="Property" value={state.snapshot.property} onChange={(value) => updateSnapshot("property", value)} /><AmountInput label="Vehicle" value={state.snapshot.vehicle} onChange={(value) => updateSnapshot("vehicle", value)} /><AmountInput label="Other assets" value={state.snapshot.otherAssets} onChange={(value) => updateSnapshot("otherAssets", value)} /></div><div className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4"><p className="text-sm font-bold text-slate-700">Debts / liabilities</p><p className="mt-1 text-sm leading-6 text-slate-500">Current Homepage APIs do not include debts yet, so these fields are collected visually but not saved until a debts backend exists.</p><div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><AmountInput label="Credit card debt" value={state.snapshot.creditCardDebt} onChange={(value) => updateSnapshot("creditCardDebt", value)} /><AmountInput label="Personal loan" value={state.snapshot.personalLoan} onChange={(value) => updateSnapshot("personalLoan", value)} /><AmountInput label="Student loan" value={state.snapshot.studentLoan} onChange={(value) => updateSnapshot("studentLoan", value)} /><AmountInput label="Mortgage" value={state.snapshot.mortgage} onChange={(value) => updateSnapshot("mortgage", value)} /><AmountInput label="Other debt" value={state.snapshot.otherDebt} onChange={(value) => updateSnapshot("otherDebt", value)} /></div></div></section>}
        {step === 6 && <section><h2 className="text-2xl font-bold text-slate-950">Review and finish</h2><div className="mt-5 grid gap-4 md:grid-cols-2">{[["Focus areas", review.focus], ["Explanation style", review.style], ["Main concerns", review.concerns], ["Advisor preferences", review.advisor], ["Financial snapshot", review.snapshot]].map(([label, value]) => <article key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-5"><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{label}</p><p className="mt-3 text-sm leading-6 text-slate-700">{value}</p></article>)}</div></section>}
      </div>

      {step > 0 && <footer className="flex flex-col-reverse gap-3 border-t border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6"><div className="flex flex-col gap-3 sm:flex-row"><SecondaryAction onClick={() => setStep((current) => Math.max(current - 1, 0))} disabled={saving}><ArrowLeft size={18} /> Back</SecondaryAction>{step < 6 && <SecondaryAction onClick={() => setStep((current) => Math.min(current + 1, 6))} disabled={saving}>Skip this step</SecondaryAction>}</div>{step < 6 ? <PrimaryAction onClick={() => setStep((current) => Math.min(current + 1, 6))} disabled={!canContinue || saving}>Next <ChevronRight size={18} /></PrimaryAction> : <PrimaryAction onClick={() => void finishSetup()} disabled={saving}>{saving ? "Saving..." : "Finish Setup"} <Check size={18} /></PrimaryAction>}</footer>}
    </section>
  </div>;
}
