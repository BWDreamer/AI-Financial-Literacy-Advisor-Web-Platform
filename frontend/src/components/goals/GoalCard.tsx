import { ChevronRight, CreditCard, Flag, Home, PiggyBank, Shield, TrendingUp, Umbrella } from "lucide-react";
import type { Goal, GoalCategory } from "../../types/goalTypes";
import { formatGoalCurrency, formatGoalDate, goalProgress, goalStatus } from "../../utils/goalUtils";
import GoalProgressBar from "./GoalProgressBar";
import GoalStatusBadge from "./GoalStatusBadge";

const icons: Record<GoalCategory, React.ElementType> = {
  "General Saving": PiggyBank,
  "Emergency Fund": Shield,
  "Debt Repayment": CreditCard,
  "Home Deposit": Home,
  Retirement: Umbrella,
  Budget: TrendingUp,
};

type Props = {
  goal: Goal;
  monthlyAdded?: number;
  onOpen: (goal: Goal) => void;
  onDragStart?: () => void;
  onDragOver?: () => void;
};

export default function GoalCard({ goal, monthlyAdded, onOpen, onDragStart, onDragOver }: Props) {
  const status = goalStatus(goal);
  const progress = Math.round(goalProgress(goal));
  const displayedMonthly = monthlyAdded ?? goal.monthlyContribution;
  const added = goal.targetAmount ? Math.min(displayedMonthly / goal.targetAmount * 100, 100 - progress) : 0;
  const displayedProgress = Math.min(progress + added, 100);
  const Icon = icons[goal.category] || Flag;

  return (
    <button
      type="button"
      draggable={!!onDragStart}
      onDragStart={onDragStart}
      onDragOver={(event) => { event.preventDefault(); onDragOver?.(); }}
      onClick={() => onOpen(goal)}
      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-200 hover:shadow-md focus:outline-none focus:ring-4 focus:ring-blue-100 active:cursor-grabbing"
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(12rem,1fr)_minmax(16rem,1.6fr)_12rem_9rem_1.5rem] lg:items-center">
        <div className="flex items-center gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-blue-50 text-blue-600">
            <Icon size={22} />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-bold text-slate-900">{goal.name}</h3>
              <GoalStatusBadge status={status} />
            </div>
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-bold text-slate-900">{formatGoalCurrency(goal.currentAmount)} / {formatGoalCurrency(goal.targetAmount)}</span>
            <span className="font-bold text-slate-700">{Math.round(displayedProgress)}%</span>
          </div>
          {added > 0 && <p className="mb-1 text-right text-xs font-bold text-amber-600">+{Math.round(added)}% this month</p>}
          <GoalProgressBar value={displayedProgress} status={status} added={added} />
        </div>
        <Info label="Target date" value={formatGoalDate(goal.targetDate)} />
        <Info label="Monthly" value={formatGoalCurrency(displayedMonthly)} />
        <ChevronRight className="hidden text-slate-400 lg:block" size={20} />
      </div>
    </button>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2 lg:bg-transparent lg:p-0">
      <p className="text-xs font-semibold text-slate-500">{label}</p>
      <p className="mt-1 font-bold text-slate-900">{value}</p>
    </div>
  );
}
