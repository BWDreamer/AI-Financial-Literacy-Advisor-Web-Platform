import { FormEvent, useState } from "react";
import { Bot, CreditCard, Home, PiggyBank, Shield, Target, TrendingUp, Umbrella } from "lucide-react";
import DatePicker from "../DatePicker";
import FormInput from "../FormInput";
import Modal from "../Modal";
import PrimaryButton from "../PrimaryButton";
import type { Goal, GoalCategory, GoalFormValues } from "../../types/goalTypes";
import { formatGoalCurrency, formatGoalDate, goalCategories, tomorrowValue } from "../../utils/goalUtils";

type AnswerValue = string | number;
type Answers = Record<string, AnswerValue>;
type Errors = Record<string, string>;
type Step = 0 | 1 | 2 | 3 | 4;
type Question = { id: string; label: string; type?: "text" | "number" | "date" | "select"; required?: boolean; options?: string[]; placeholder?: string };

const inputClass = "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

const categoryMeta: Record<GoalCategory, { title: string; description: string; icon: React.ElementType }> = {
  "General Saving": { title: "General Saving", description: "Car, travel, education, or other major purchase.", icon: PiggyBank },
  "Emergency Fund": { title: "Emergency Fund", description: "Build a safety buffer for unexpected costs.", icon: Shield },
  "Debt Repayment": { title: "Debt Repayment", description: "Pay down credit card, loan, or bill debt.", icon: CreditCard },
  "Home Deposit": { title: "Home Deposit", description: "Plan for a deposit and upfront housing costs.", icon: Home },
  Retirement: { title: "Retirement / Super", description: "Track long-term retirement or super progress.", icon: Umbrella },
  Budget: { title: "Budget / Cash Flow", description: "Improve monthly surplus and reduce pressure.", icon: TrendingUp },
};

const questions: Record<GoalCategory, { details: Question[]; finances: Question[] }> = {
  "General Saving": {
    details: [
      { id: "goal_title", label: "What are you saving for?", placeholder: "Buy a car", required: true },
      { id: "target_amount", label: "How much do you want to save?", type: "number", required: true },
      { id: "deadline", label: "When do you want to reach it?", type: "date", required: true },
    ],
    finances: [
      { id: "current_amount", label: "How much have you already saved?", type: "number", required: true },
      { id: "monthly_contribution", label: "How much can you save each month?", type: "number", required: true },
    ],
  },
  "Emergency Fund": {
    details: [
      { id: "essential_monthly_expenses", label: "What are your essential monthly expenses?", type: "number", required: true },
      { id: "coverage_months", label: "How many months do you want to cover?", type: "number", required: true },
      { id: "deadline", label: "When would you like to complete this buffer?", type: "date", required: true },
    ],
    finances: [
      { id: "current_amount", label: "How much do you already have saved?", type: "number", required: true },
      { id: "monthly_contribution", label: "How much can you save monthly?", type: "number", required: true },
    ],
  },
  "Debt Repayment": {
    details: [
      { id: "debt_name", label: "What debt do you want to pay off?", placeholder: "Credit card debt", required: true },
      { id: "debt_balance", label: "What is the current balance?", type: "number", required: true },
      { id: "interest_rate", label: "What is the interest rate? (optional)", type: "number" },
    ],
    finances: [
      { id: "minimum_repayment", label: "What is the minimum repayment?", type: "number", required: true },
      { id: "extra_repayment", label: "How much extra can you repay monthly?", type: "number", required: true },
      { id: "deadline", label: "Do you have a preferred payoff deadline?", type: "date", required: true },
    ],
  },
  "Home Deposit": {
    details: [
      { id: "property_price", label: "Do you know the target property price?", type: "number" },
      { id: "deposit_percent", label: "What deposit percentage do you want?", type: "number" },
      { id: "deposit_target", label: "Or enter a direct deposit target", type: "number" },
    ],
    finances: [
      { id: "cost_buffer", label: "Do you want to include an upfront cost buffer?", type: "number" },
      { id: "current_amount", label: "How much have you already saved?", type: "number", required: true },
      { id: "monthly_contribution", label: "How much can you save monthly?", type: "number", required: true },
      { id: "deadline", label: "When do you want to be ready?", type: "date", required: true },
    ],
  },
  Retirement: {
    details: [
      { id: "target_age", label: "What is your target retirement age?", type: "number", required: true },
      { id: "current_super", label: "What is your current super or retirement saving?", type: "number", required: true },
      { id: "target_amount", label: "What retirement amount do you want to track?", type: "number", required: true },
    ],
    finances: [
      { id: "regular_contribution", label: "How much is contributed regularly each month?", type: "number", required: true },
      { id: "deadline", label: "Review target date", type: "date", required: true },
    ],
  },
  Budget: {
    details: [
      { id: "monthly_income", label: "What is your monthly income?", type: "number", required: true },
      { id: "fixed_expenses", label: "What are your fixed expenses?", type: "number", required: true },
      { id: "variable_expenses", label: "What are your variable expenses?", type: "number", required: true },
    ],
    finances: [
      { id: "target_monthly_surplus", label: "How much extra do you want to save each month?", type: "number", required: true },
      { id: "adjustable_categories", label: "Which spending areas are flexible?", placeholder: "Dining out, subscriptions, transport" },
      { id: "deadline", label: "Monthly review target date", type: "date", required: true },
    ],
  },
};

function initialAnswers(category: GoalCategory): Answers {
  return { deadline: tomorrowValue(), priority: "Medium", ...(category === "Emergency Fund" ? { coverage_months: 3 } : {}) };
}

function money(value: AnswerValue | undefined) {
  return Number(value || 0);
}

function derivedValues(category: GoalCategory, answers: Answers): GoalFormValues {
  const common = { category, priority: answers.priority as GoalFormValues["priority"] || "Medium", targetDate: String(answers.deadline || tomorrowValue()) };
  if (category === "Emergency Fund") return { ...common, name: "Emergency Fund", targetAmount: money(answers.essential_monthly_expenses) * money(answers.coverage_months), currentAmount: money(answers.current_amount), monthlyContribution: money(answers.monthly_contribution) };
  if (category === "Debt Repayment") return { ...common, name: String(answers.debt_name || "Debt Repayment"), targetAmount: money(answers.debt_balance), currentAmount: 0, monthlyContribution: money(answers.minimum_repayment) + money(answers.extra_repayment) };
  if (category === "Home Deposit") return { ...common, name: "Home Deposit", targetAmount: homeDepositTarget(answers), currentAmount: money(answers.current_amount), monthlyContribution: money(answers.monthly_contribution) };
  if (category === "Retirement") return { ...common, name: "Retirement Plan", targetAmount: money(answers.target_amount), currentAmount: money(answers.current_super), monthlyContribution: money(answers.regular_contribution) };
  if (category === "Budget") return { ...common, name: "Improve Monthly Cash Flow", targetAmount: money(answers.target_monthly_surplus) * 12, currentAmount: 0, monthlyContribution: money(answers.target_monthly_surplus) };
  return { ...common, name: String(answers.goal_title || "General Saving"), targetAmount: money(answers.target_amount), currentAmount: money(answers.current_amount), monthlyContribution: money(answers.monthly_contribution) };
}

function homeDepositTarget(answers: Answers) {
  const direct = money(answers.deposit_target);
  const calculated = money(answers.property_price) * money(answers.deposit_percent) / 100;
  return Math.max(direct, calculated) + money(answers.cost_buffer);
}

function requiredMonthly(values: GoalFormValues) {
  const target = new Date(`${values.targetDate}T00:00:00`); const now = new Date();
  const months = Math.max((target.getFullYear() - now.getFullYear()) * 12 + target.getMonth() - now.getMonth(), 1);
  return Math.ceil(Math.max(values.targetAmount - values.currentAmount, 0) / months);
}

function validateStep(step: Step, category: GoalCategory, answers: Answers) {
  const next: Errors = {};
  if (step === 0) return next;
  const scope = step === 1 ? questions[category].details : questions[category].finances;
  scope.forEach((question) => validateQuestion(question, answers, next));
  if (step >= 2) validateGoalMath(derivedValues(category, answers), next);
  return next;
}

function validateQuestion(question: Question, answers: Answers, errors: Errors) {
  const value = answers[question.id];
  if (question.required && (value === undefined || value === "")) errors[question.id] = "This field is required.";
  if (question.type === "number" && value !== undefined && value !== "" && Number(value) < 0) errors[question.id] = "Value cannot be negative.";
}

function validateGoalMath(values: GoalFormValues, errors: Errors) {
  if (values.targetAmount <= 0) errors.targetAmount = "Goal target must be greater than zero.";
  if (values.targetDate <= new Date().toISOString().slice(0, 10)) errors.deadline = "Target date must be in the future.";
}

function StepShell({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-bold text-slate-900">{title}</h3>
      {subtitle && <p className="mt-2 text-sm text-slate-500">{subtitle}</p>}
      <div className="mt-5 space-y-4">{children}</div>
    </section>
  );
}

function CategoryStep({ value, onChange }: { value: GoalCategory; onChange: (value: GoalCategory) => void }) {
  return (
    <StepShell title="What is your goal?" subtitle="Choose the planning template that best matches your goal.">
      <div className="grid gap-3 sm:grid-cols-2">
        {goalCategories.map((category) => <CategoryCard key={category} category={category} active={value === category} onClick={() => onChange(category)} />)}
      </div>
    </StepShell>
  );
}

function CategoryCard({ category, active, onClick }: { category: GoalCategory; active: boolean; onClick: () => void }) {
  const Icon = categoryMeta[category].icon;
  return (
    <button type="button" onClick={onClick} className={`flex items-center gap-4 rounded-xl border p-4 text-left transition ${active ? "border-blue-400 bg-blue-50 ring-2 ring-blue-100" : "border-slate-200 hover:bg-slate-50"}`}>
      <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-white text-blue-600"><Icon size={21} /></span>
      <span><b className="block text-sm text-slate-900">{categoryMeta[category].title}</b><span className="text-xs text-slate-500">{categoryMeta[category].description}</span></span>
    </button>
  );
}

function QuestionsStep({ title, category, scope, answers, errors, update }: { title: string; category: GoalCategory; scope: "details" | "finances"; answers: Answers; errors: Errors; update: (id: string, value: AnswerValue) => void }) {
  return (
    <StepShell title={title} subtitle={scope === "details" ? "These questions define the goal draft." : "These answers help calculate feasibility and progress."}>
      {questions[category][scope].map((question) => <QuestionField key={question.id} question={question} value={answers[question.id]} error={errors[question.id]} onChange={update} />)}
    </StepShell>
  );
}

function QuestionField({ question, value, error, onChange }: { question: Question; value: AnswerValue | undefined; error?: string; onChange: (id: string, value: AnswerValue) => void }) {
  if (question.type === "date") return <Field error={error}><DatePicker id={question.id} label={question.label} value={String(value || tomorrowValue())} min={tomorrowValue()} max="2100-12-31" placement="top" onChange={(next) => onChange(question.id, next)} /></Field>;
  if (question.type === "select") return <SelectField question={question} value={String(value || "")} error={error} onChange={onChange} />;
  return <Field error={error}><FormInput id={question.id} label={question.label} type={question.type || "text"} min={question.type === "number" ? "0" : undefined} placeholder={question.placeholder} value={value || ""} onChange={(event) => onChange(question.id, question.type === "number" ? Number(event.target.value) : event.target.value)} /></Field>;
}

function SelectField({ question, value, error, onChange }: { question: Question; value: string; error?: string; onChange: (id: string, value: AnswerValue) => void }) {
  return (
    <Field error={error}>
      <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">{question.label}</span><select value={value} onChange={(event) => onChange(question.id, event.target.value)} className={inputClass}>{question.options?.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
    </Field>
  );
}

function AnalysisStep({ values }: { values: GoalFormValues }) {
  const required = requiredMonthly(values); const diff = values.monthlyContribution - required;
  return (
    <StepShell title="Here's your personalized plan" subtitle="This is a draft analysis. Later, AI chat can explain or adjust this plan.">
      <div className="rounded-2xl bg-blue-50 p-4 text-sm text-slate-600"><Bot className="mb-2 text-blue-600" size={22} />Backend calculation should own final feasibility checks; this preview prepares the goal draft.</div>
      <div className="rounded-2xl bg-emerald-50 p-4">
        <h4 className="font-bold text-emerald-700">{diff >= 0 ? "You are on track! 🎉" : "You may need a small adjustment"}</h4>
        <p className="mt-2 text-sm text-slate-600">Required monthly saving <b>{formatGoalCurrency(required)}</b></p>
        <p className="text-sm text-slate-600">Your monthly saving <b>{formatGoalCurrency(values.monthlyContribution)}</b></p>
        <p className={diff >= 0 ? "text-sm font-bold text-emerald-600" : "text-sm font-bold text-amber-600"}>Difference {diff >= 0 ? "+" : "-"} {formatGoalCurrency(Math.abs(diff))}</p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 text-sm"><PlanRow name="Comfortable" amount={Math.max(required - 200, 0)} /><PlanRow name="Balanced (Recommended)" amount={required} active /><PlanRow name="Faster" amount={required + 200} /></div>
    </StepShell>
  );
}

function ReviewStep({ values, answers }: { values: GoalFormValues; answers: Answers }) {
  const Icon = categoryMeta[values.category].icon;
  return (
    <StepShell title="Review and save your goal">
      <div className="rounded-2xl border border-slate-200 p-5 text-center"><Icon className="mx-auto text-blue-600" size={34} /><h4 className="mt-3 text-lg font-bold">{values.name}</h4><p className="font-bold">{formatGoalCurrency(values.targetAmount)}</p><ReviewRow label="Category" value={categoryMeta[values.category].title} /><ReviewRow label="Target date" value={formatGoalDate(values.targetDate)} /><ReviewRow label="Current progress" value={formatGoalCurrency(values.currentAmount)} /><ReviewRow label="Monthly amount" value={formatGoalCurrency(values.monthlyContribution)} /></div>
      <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">This draft includes {Object.keys(answers).length} collected fields for future AI review.</div>
    </StepShell>
  );
}

export default function CreateGoalModal({ onClose, onCreate }: { onClose: () => void; onCreate: (goal: Goal) => void | Promise<void> }) {
  const [category, setCategory] = useState<GoalCategory>("General Saving");
  const [answers, setAnswers] = useState<Answers>(() => initialAnswers("General Saving"));
  const [errors, setErrors] = useState<Errors>({});
  const [step, setStep] = useState<Step>(0);
  const [submitError, setSubmitError] = useState("");
  const [saving, setSaving] = useState(false);
  const values = derivedValues(category, answers);

  function changeCategory(next: GoalCategory) { setCategory(next); setAnswers(initialAnswers(next)); setErrors({}); }
  function update(id: string, value: AnswerValue) { setAnswers((current) => ({ ...current, [id]: value })); }
  function next() { const nextErrors = validateStep(step, category, answers); setErrors(nextErrors); if (!Object.keys(nextErrors).length) setStep((current) => Math.min(current + 1, 4) as Step); }
  async function submit(event: FormEvent) {
    event.preventDefault(); const nextErrors = validateStep(4, category, answers); setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setSaving(true); setSubmitError("");
    try {
      await onCreate({ ...values, id: crypto.randomUUID(), name: values.name.trim(), categoryDetails: answers, createdAt: new Date().toISOString().slice(0, 10) });
      onClose();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Unable to save goal.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Create a New Goal" onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-6">
        {step === 0 && <CategoryStep value={category} onChange={changeCategory} />}
        {step === 1 && <QuestionsStep title={`${categoryMeta[category].title} details`} category={category} scope="details" answers={answers} errors={errors} update={update} />}
        {step === 2 && <QuestionsStep title="Financial inputs" category={category} scope="finances" answers={answers} errors={errors} update={update} />}
        {step === 3 && <AnalysisStep values={values} />}
        {step === 4 && <ReviewStep values={values} answers={answers} />}
        {submitError && <p className="rounded-2xl bg-red-50 p-4 text-sm font-semibold text-red-600">{submitError}</p>}
        <div className="flex justify-end gap-3"><button type="button" onClick={step === 0 ? onClose : () => setStep((current) => Math.max(current - 1, 0) as Step)} className="w-36 rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">{step === 0 ? "Cancel" : "Back"}</button>{step < 4 ? <PrimaryButton type="button" onClick={next} className="w-36 px-6">Next</PrimaryButton> : <PrimaryButton disabled={saving} className="w-36 px-6">{saving ? "Saving..." : "Save Goal"}</PrimaryButton>}</div>
      </form>
    </Modal>
  );
}

function Field({ children, error }: { children: React.ReactNode; error?: string }) {
  return <div>{children}{error && <p className="mt-1 text-xs font-semibold text-red-600">{error}</p>}</div>;
}

function PlanRow({ name, amount, active = false }: { name: string; amount: number; active?: boolean }) {
  return <div className={`flex justify-between px-4 py-3 ${active ? "bg-blue-50 text-blue-700" : "bg-white"}`}><span>{name}</span><b>{formatGoalCurrency(amount)}/month</b></div>;
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return <div className="mt-3 flex justify-between border-t border-slate-100 pt-3 text-sm"><span className="text-slate-500">{label}</span><b>{value}</b></div>;
}
