import { CheckCircle2, Flag, PiggyBank, TrendingUp } from "lucide-react";
import type { Goal } from "../../types/goalTypes";
import { formatGoalCurrency, goalStatus } from "../../utils/goalUtils";

function SummaryCard({ icon, label, value, text, tone }: { icon: React.ReactNode; label: string; value: string; text: string; tone: string }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-4">
        <span className={`grid size-11 place-items-center rounded-2xl ${tone}`}>
          {icon}
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{text}</p>
        </div>
      </div>
    </article>
  );
}

export default function GoalSummary({ goals, totalSaved }: { goals: Goal[]; totalSaved?: number }) {
  const active = goals.filter((goal) => goalStatus(goal) !== "Completed");
  const onTrack = goals.filter((goal) => goalStatus(goal) === "On Track").length;
  const completed = goals.filter((goal) => goalStatus(goal) === "Completed").length;
  const saved = totalSaved ?? 0;
  const percent = active.length ? Math.round(onTrack / active.length * 100) : 0;

  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <SummaryCard icon={<Flag size={20} />} label="Total Goals" value={String(goals.length)} text="Active and completed goals" tone="bg-blue-50 text-blue-600" />
      <SummaryCard icon={<TrendingUp size={20} />} label="On Track" value={String(onTrack)} text={`${percent}% of active goals`} tone="bg-emerald-50 text-emerald-600" />
      <SummaryCard icon={<PiggyBank size={20} />} label="Total Saved" value={formatGoalCurrency(saved)} text="Same as Cash Savings" tone="bg-amber-50 text-amber-600" />
      <SummaryCard icon={<CheckCircle2 size={20} />} label="Completed" value={String(completed)} text="Goals achieved" tone="bg-sky-50 text-sky-600" />
    </section>
  );
}
