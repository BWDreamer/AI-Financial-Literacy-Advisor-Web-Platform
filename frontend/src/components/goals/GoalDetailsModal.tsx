import { Bot, CreditCard, Home, MoreVertical, Pencil, PiggyBank, Shield, Target, TrendingUp, Umbrella } from "lucide-react";
import { useEffect, useState } from "react";
import { getGoalAnalysis, getGoalChart, getGoalProgress, type GoalAnalysis, type GoalChart, type GoalProgress } from "../../api/goals";
import Modal from "../Modal";
import PrimaryButton from "../PrimaryButton";
import type { Goal, GoalCategory } from "../../types/goalTypes";
import { formatGoalCurrency, formatGoalDate, goalProgress, goalStatus } from "../../utils/goalUtils";
import GoalProgressBar from "./GoalProgressBar";
import GoalStatusBadge from "./GoalStatusBadge";

type Props = { goal: Goal; onClose: () => void; onAskAdvisor: (goal: Goal) => void };
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

function GoalHero({ goal }: { goal: Goal }) {
  const Icon = icons[goal.category];
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
      <div className="flex gap-3">
        <button type="button" className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Pencil size={16} />Edit Goal</button>
        <button type="button" aria-label="More goal actions" className="grid size-11 place-items-center rounded-xl border border-slate-200 text-slate-500 hover:bg-slate-50"><MoreVertical size={18} /></button>
      </div>
    </header>
  );
}

function ProgressOverview({ goal, analysis }: { goal: Goal; analysis: GoalAnalysis | null }) {
  const progress = Math.round(analysis?.progress_percentage ?? goalProgress(goal));
  const required = analysis?.required_monthly ?? 0;
  const difference = analysis?.monthly_difference ?? goal.monthlyContribution - required;
  const status = analysis?.status === "completed" ? "Completed" : analysis?.status === "behind" ? "Behind" : goalStatus(goal);
  return (
    <section className="grid gap-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:grid-cols-[1.5fr_0.9fr]">
      <div>
        <h3 className="font-bold text-slate-900">Progress overview</h3>
        <div className="mt-5 flex items-end justify-between gap-4">
          <p className="text-3xl font-bold text-slate-900">{formatGoalCurrency(goal.currentAmount)} <span className="text-base text-slate-500">/ {formatGoalCurrency(goal.targetAmount)}</span></p>
          <p className={status === "Behind" ? "text-2xl font-bold text-amber-600" : "text-2xl font-bold text-emerald-600"}>{progress}%</p>
        </div>
        <div className="mt-4"><GoalProgressBar value={progress} status={status} /></div>
        <p className="mt-5 text-sm text-slate-600">{status === "Behind" ? "You may need to increase your monthly contribution." : "You're on track to reach your goal."}</p>
      </div>
      <div className="divide-y divide-slate-100">
        <Metric label="Monthly saving" value={formatGoalCurrency(goal.monthlyContribution)} />
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
        {!loading && !rows.length && <p className="py-3 text-sm text-slate-500">No contributions have been recorded yet.</p>}
        {rows.map((row) => {
          const date = new Date(`${row.progress_date}T00:00:00`);
          return <div key={row.id} className="flex justify-between py-3 text-sm"><span className="font-bold text-emerald-600">+ {formatGoalCurrency(Number(row.amount))}</span><span className="text-slate-500">{date.toLocaleDateString("en-AU", { month: "short", day: "numeric", year: "numeric" })}</span></div>;
        })}
      </div>
      {!!rows.length && <button type="button" className="mt-4 text-sm font-bold text-blue-600 hover:text-blue-700">View all</button>}
    </section>
  );
}

export default function GoalDetailsModal({ goal, onClose, onAskAdvisor }: Props) {
  const [analysis, setAnalysis] = useState<GoalAnalysis | null>(null);
  const [chart, setChart] = useState<GoalChart | null>(null);
  const [progressRows, setProgressRows] = useState<GoalProgress[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!goal.apiId) return;
    setLoading(true);
    Promise.all([getGoalAnalysis(goal.apiId), getGoalChart(goal.apiId), getGoalProgress(goal.apiId)])
      .then(([nextAnalysis, nextChart, rows]) => { setAnalysis(nextAnalysis); setChart(nextChart); setProgressRows(rows); })
      .catch(() => { setAnalysis(null); setChart(null); setProgressRows([]); })
      .finally(() => setLoading(false));
  }, [goal.apiId]);

  return (
    <Modal title="Goal Detail & Progress Tracking" onClose={onClose} wide>
      <div className="space-y-5">
        <h1 className="text-2xl font-bold text-blue-700">Goal Detail & Progress Tracking</h1>
        <GoalHero goal={goal} />
        <ProgressOverview goal={goal} analysis={analysis} />
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_17rem]">
          <ProgressChart goal={goal} chart={chart} />
          <RecentActivity rows={progressRows} loading={loading} />
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-blue-50 p-4">
            <div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-full bg-white text-blue-600"><Bot size={20} /></span><p className="text-sm text-slate-600"><b className="text-slate-900">AI insights</b><br />Ask your advisor to review this goal and suggest improvements.</p></div>
            <PrimaryButton type="button" onClick={() => onAskAdvisor(goal)} className="w-auto px-5">Ask AI Advisor</PrimaryButton>
          </div>
        </section>
        <div className="flex justify-end"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Close</button></div>
      </div>
    </Modal>
  );
}
