import { Bot, CreditCard, Home, Pencil, PiggyBank, Shield, Target, Trash2, TrendingUp, Umbrella } from "lucide-react";
import { useEffect, useState } from "react";
import { deleteGoal, getGoalAnalysis, getGoalChart, getGoalProgress, updateGoal, type GoalAnalysis, type GoalChart, type GoalProgress } from "../../api/goals";
import DatePicker from "../DatePicker";
import Modal from "../Modal";
import PrimaryButton from "../PrimaryButton";
import type { Goal, GoalCategory } from "../../types/goalTypes";
import { formatGoalCurrency, formatGoalDate, goalFromApi, goalStatus, goalToPayload } from "../../utils/goalUtils";
import GoalProgressBar from "./GoalProgressBar";
import GoalStatusBadge from "./GoalStatusBadge";

type Props = { goal: Goal; onClose: () => void; onAskAdvisor: (goal: Goal) => void; onSaved?: () => void };
type Point = { x: number; y: number };

const icons: Record<GoalCategory, React.ElementType> = {
  "General Saving": PiggyBank,
  "Emergency Fund": Shield,
  "Debt Repayment": CreditCard,
  "Home Deposit": Home,
  Retirement: Umbrella,
  Budget: TrendingUp,
};

function path(points: Point[]) {
  return points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ");
}

function chartPoints(rows: Array<{ amount: number }>, target: number) {
  return rows.map((row, index) => ({
    x: 38 + (rows.length <= 1 ? 0 : index * 392 / (rows.length - 1)),
    y: 160 - Math.min(Number(row.amount) / Math.max(target, 1) * 100, 100) * 1.25,
  }));
}

function GoalHero({ goal, onEdit, onDelete }: { goal: Goal; onEdit: () => void; onDelete: () => void }) {
  const Icon = icons[goal.category];
  const canEdit = goalStatus(goal) !== "Completed";
  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        <span className="grid size-16 place-items-center rounded-2xl bg-blue-50 text-blue-600"><Icon size={30} /></span>
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-bold text-slate-900">{goal.name}</h2>
            <GoalStatusBadge status={goalStatus(goal)} />
          </div>
          <p className="mt-2 text-sm text-slate-500">Target: {formatGoalCurrency(goal.targetAmount)} <span className="mx-3 text-slate-300">|</span> Target date: {formatGoalDate(goal.targetDate)}</p>
        </div>
      </div>
      {canEdit && <div className="flex gap-3">
        <button type="button" onClick={onEdit} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Pencil size={16} />Edit Goal</button>
        <button type="button" onClick={onDelete} className="inline-flex items-center gap-2 rounded-xl border border-red-100 px-4 py-3 text-sm font-semibold text-red-600 hover:bg-red-50"><Trash2 size={16} />Delete Goal</button>
      </div>}
    </header>
  );
}

function ProgressOverview({ goal, analysis }: { goal: Goal; analysis: GoalAnalysis | null }) {
  const progress = Math.round(analysis?.progress_percentage ?? goal.progressPercentage);
  const required = analysis?.required_monthly ?? 0;
  const difference = analysis?.monthly_difference ?? 0;
  const status = analysis?.status === "completed" ? "Completed" : analysis?.status === "pending_archive" ? "Pending Archive" : analysis?.status === "behind" ? "Behind" : goalStatus(goal);
  return (
    <section className="grid gap-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:grid-cols-[1.5fr_0.9fr]">
      <div>
        <h3 className="font-bold text-slate-900">Progress overview</h3>
        <div className="mt-5 flex items-end justify-between gap-4">
          <p className="text-3xl font-bold text-slate-900">{formatGoalCurrency(goal.currentAmount)} <span className="text-base text-slate-500">/ {formatGoalCurrency(goal.targetAmount)}</span></p>
          <p className={status === "Behind" ? "text-2xl font-bold text-amber-600" : "text-2xl font-bold text-emerald-600"}>{progress}%</p>
        </div>
        <div className="mt-4"><GoalProgressBar value={progress} status={status} /></div>
        <p className="mt-5 text-sm text-slate-600">{status === "Pending Archive" ? "This goal is complete and waiting for your confirmation." : status === "Behind" ? "You may need to increase your monthly contribution." : "You're on track to reach your goal."}</p>
      </div>
      <div className="divide-y divide-slate-100">
        <Metric label="Allocated monthly" value={formatGoalCurrency(analysis?.allocated_monthly ?? goal.allocatedMonthly ?? goal.monthlyContribution)} />
        <Metric label="Required monthly" value={formatGoalCurrency(required)} />
        <Metric label="Difference" value={`${difference >= 0 ? "+" : "-"} ${formatGoalCurrency(Math.abs(difference))}`} positive={difference >= 0} />
      </div>
    </section>
  );
}

function Metric({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return <div className="flex items-center justify-between py-3 text-sm"><span className="font-semibold text-slate-500">{label}</span><span className={`font-bold ${positive === undefined ? "text-slate-900" : positive ? "text-emerald-600" : "text-amber-600"}`}>{value}</span></div>;
}

function ProgressChart({ goal, chart }: { goal: Goal; chart: GoalChart | null }) {
  const actual = chartPoints(chart?.actual_progress_points ?? [], chart?.target_amount ?? goal.targetAmount);
  const expected = chartPoints(chart?.expected_progress_points ?? [], chart?.target_amount ?? goal.targetAmount);
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between"><h3 className="font-bold text-slate-900">Progress chart</h3><Legend /></div>
      <svg viewBox="0 0 470 200" className="mt-4 h-56 w-full">
        {[35, 75, 115, 155].map((y) => <line key={y} x1="38" x2="430" y1={y} y2={y} stroke="#e5e7eb" />)}
        <path d={path(expected)} fill="none" stroke="#3b82f6" strokeDasharray="4 5" strokeLinecap="round" strokeWidth="2" />
        <path d={path(actual)} fill="none" stroke="#22c55e" strokeLinecap="round" strokeWidth="2.5" />
        {actual.map((point) => <circle key={`${point.x}-${point.y}`} cx={point.x} cy={point.y} r="3.5" fill="#22c55e" />)}
        {["$0", "$5k", "$10k", "$15k"].map((label, index) => <text key={label} x="4" y={165 - index * 42} fill="#64748b" fontSize="12">{label}</text>)}
        {["Now", "Midway", formatGoalDate(goal.targetDate)].map((label, index) => <text key={label} x={38 + index * 180} y="192" fill="#64748b" fontSize="12">{label}</text>)}
      </svg>
    </section>
  );
}

function Legend() {
  return <div className="flex gap-4 text-xs font-semibold text-slate-500"><span><b className="mr-1 inline-block h-0.5 w-5 bg-emerald-500" />Actual</span><span><b className="mr-1 inline-block h-0.5 w-5 border-t-2 border-dashed border-blue-500" />Expected</span></div>;
}

function RecentActivity({ rows, loading }: { rows: GoalProgress[]; loading: boolean }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="font-bold text-slate-900">Recent activity</h3>
      <div className="mt-4 divide-y divide-slate-100">
        {loading && <p className="py-3 text-sm text-slate-500">Loading activity...</p>}
        {!loading && !rows.length && <p className="py-3 text-sm text-slate-500">No progress has been recorded yet.</p>}
        {rows.map((row) => {
          const date = new Date(`${row.progress_date}T00:00:00`);
          return <div key={row.id} className="flex justify-between py-3 text-sm"><span className="font-bold text-emerald-600">+ {formatGoalCurrency(Number(row.amount))}</span><span className="text-slate-500">{date.toLocaleDateString("en-AU", { month: "short", day: "numeric", year: "numeric" })}</span></div>;
        })}
      </div>
      {!!rows.length && <button type="button" className="mt-4 text-sm font-bold text-blue-600 hover:text-blue-700">View all</button>}
    </section>
  );
}

export default function GoalDetailsModal({ goal, onClose, onAskAdvisor, onSaved }: Props) {
  const [currentGoal, setCurrentGoal] = useState(goal);
  const [analysis, setAnalysis] = useState<GoalAnalysis | null>(null);
  const [chart, setChart] = useState<GoalChart | null>(null);
  const [progressRows, setProgressRows] = useState<GoalProgress[]>([]);
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [loading, setLoading] = useState(true);
  const canEdit = goalStatus(currentGoal) !== "Completed";

  useEffect(() => {
    if (!currentGoal.apiId) return;
    setLoading(true);
    Promise.all([getGoalAnalysis(currentGoal.apiId), getGoalChart(currentGoal.apiId), getGoalProgress(currentGoal.apiId)])
      .then(([nextAnalysis, nextChart, rows]) => { setAnalysis(nextAnalysis); setChart(nextChart); setProgressRows(rows); })
      .catch(() => { setAnalysis(null); setChart(null); setProgressRows([]); })
      .finally(() => setLoading(false));
  }, [currentGoal.apiId]);

  return (
    <Modal title="Goal Detail & Progress Tracking" onClose={onClose} wide>
      <div className="space-y-5">
        <h1 className="text-2xl font-bold text-blue-700">Goal Detail & Progress Tracking</h1>
        <GoalHero goal={currentGoal} onEdit={() => setEditing(true)} onDelete={() => setConfirmingDelete(true)} />
        {editing && canEdit && <EditGoalForm goal={currentGoal} allocatedMonthly={analysis?.allocated_monthly} onCancel={() => setEditing(false)} onSaved={(next) => { setCurrentGoal(next); setEditing(false); onSaved?.(); }} />}
        {confirmingDelete && <DeleteGoalConfirm goal={currentGoal} onCancel={() => setConfirmingDelete(false)} onDeleted={() => { onSaved?.(); onClose(); }} />}
        <ProgressOverview goal={currentGoal} analysis={analysis} />
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_17rem]">
          <ProgressChart goal={currentGoal} chart={chart} />
          <RecentActivity rows={progressRows} loading={loading} />
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-blue-50 p-4">
            <div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-full bg-white text-blue-600"><Bot size={20} /></span><p className="text-sm text-slate-600"><b className="text-slate-900">AI insights</b><br />Ask your advisor to review this goal and suggest improvements.</p></div>
            <PrimaryButton type="button" onClick={() => onAskAdvisor(currentGoal)} className="w-auto px-5">Ask AI Advisor</PrimaryButton>
          </div>
        </section>
        <div className="flex justify-end"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Close</button></div>
      </div>
    </Modal>
  );
}

function DeleteGoalConfirm({ goal, onCancel, onDeleted }: { goal: Goal; onCancel: () => void; onDeleted: () => void }) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  async function remove() {
    if (!goal.apiId) return;
    setDeleting(true); setError("");
    try { await deleteGoal(goal.apiId); onDeleted(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to delete goal."); }
    finally { setDeleting(false); }
  }
  return <section className="rounded-2xl border border-red-100 bg-red-50 p-4">
    <h3 className="text-lg font-bold text-red-700">Delete this goal?</h3>
    <p className="mt-2 text-sm text-red-600">This will permanently remove “{goal.name}” and its goal progress records.</p>
    {error && <p className="mt-3 rounded-xl bg-white p-3 text-sm font-semibold text-red-600">{error}</p>}
    <div className="mt-4 flex justify-end gap-3">
      <button type="button" onClick={onCancel} className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700">Cancel</button>
      <button type="button" disabled={deleting} onClick={() => void remove()} className="rounded-xl bg-red-600 px-5 py-3 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-60">{deleting ? "Deleting..." : "Delete Goal"}</button>
    </div>
  </section>;
}

function EditGoalForm({ goal, allocatedMonthly, onCancel, onSaved }: { goal: Goal; allocatedMonthly?: number; onCancel: () => void; onSaved: (goal: Goal) => void }) {
  const [draft, setDraft] = useState({ ...goal, monthlyContribution: allocatedMonthly ?? goal.allocatedMonthly ?? goal.monthlyContribution });
  const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  function change<K extends keyof Goal>(key: K, value: Goal[K]) { setDraft((item) => ({ ...item, [key]: value })); }
  async function save() {
    if (!goal.apiId) return;
    setSaving(true); setError("");
    try {
      onSaved(goalFromApi(await updateGoal(goal.apiId, goalToPayload(draft))));
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to update goal."); }
    finally { setSaving(false); }
  }
  return <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
    {error && <p className="mb-3 rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-600">{error}</p>}
    <div className="grid gap-3 md:grid-cols-2">
      <EditInput label="Goal name" value={draft.name} onChange={(value) => change("name", value)} />
      <EditInput label="Target amount" type="number" value={draft.targetAmount} onChange={(value) => change("targetAmount", Number(value))} />
      <EditInput label="Current amount" type="number" value={draft.currentAmount} onChange={(value) => change("currentAmount", Number(value))} />
      <EditInput label="Allocated monthly" type="number" value={draft.monthlyContribution} onChange={(value) => change("monthlyContribution", Number(value))} />
      <DatePicker id="goal-edit-target-date" label="Target date" value={draft.targetDate} min={new Date().toISOString().slice(0, 10)} max="2046-12-31" placement="bottom" onChange={(value) => change("targetDate", value)} />
    </div>
    <div className="mt-4 flex justify-end gap-3"><button type="button" onClick={onCancel} className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700">Cancel</button><PrimaryButton type="button" disabled={saving} onClick={() => void save()} className="w-auto px-6">{saving ? "Saving..." : "Save Goal"}</PrimaryButton></div>
  </section>;
}

function EditInput({ label, value, onChange, type = "text" }: { label: string; value: string | number; onChange: (value: string) => void; type?: string }) {
  return <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">{label}</span><input type={type} value={value} min={type === "number" ? 0 : undefined} onChange={(event) => onChange(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" /></label>;
}
