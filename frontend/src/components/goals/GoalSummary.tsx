import { Flag, PiggyBank, TrendingUp } from "lucide-react";
import { formatGoalCurrency } from "../../utils/goalUtils";

type SummaryProps = {
  totalGoals: number;
  onTrackGoals: number;
  behindGoals: number;
  completedGoals: number;
  cashSavings: number;
  cashAllocatable: number;
  cashAlreadyAssigned: number;
  allocatableRatio: number;
  minAllocatableRatio: number;
  monthlyAllocatableRatio: number;
  monthlyNetIncome: number;
  monthlyAllocatable: number;
  monthlyAssigned: number;
  expanded: boolean;
  onToggle: () => void;
  onAllocatableRatioChange: (value: number) => void;
  onMonthlyAllocatableRatioChange: (value: number) => void;
  onMonthlyAllocatableRatioCommit: (value: number) => void;
};

function SummaryCard({ icon, label, value, text, tone, expanded, onClick }: { icon: React.ReactNode; label: string; value: string; text: string; tone: string; expanded: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-blue-200 hover:shadow-md">
      <div className="flex items-center gap-4">
        <span className={`grid size-11 place-items-center rounded-2xl ${tone}`}>{icon}</span>
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{text}</p>
        </div>
      </div>
    </button>
  );
}

function Row({ label, value, tone = "text-slate-900" }: { label: string; value: string; tone?: string }) {
  return <p className="flex justify-between gap-3 py-1 text-sm"><span className="text-slate-500">{label}</span><b className={tone}>{value}</b></p>;
}

export default function GoalSummary({ totalGoals, onTrackGoals, behindGoals, completedGoals, cashSavings, cashAllocatable, cashAlreadyAssigned, allocatableRatio, minAllocatableRatio, monthlyAllocatableRatio, monthlyNetIncome, monthlyAllocatable, monthlyAssigned, expanded, onToggle, onAllocatableRatioChange, onMonthlyAllocatableRatioChange, onMonthlyAllocatableRatioCommit }: SummaryProps) {
  return (
    <section className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard expanded={expanded} onClick={onToggle} icon={<Flag size={20} />} label="Total Goals" value={String(totalGoals)} text="Active and completed goals" tone="bg-blue-50 text-blue-600" />
        <SummaryCard expanded={expanded} onClick={onToggle} icon={<PiggyBank size={20} />} label="Cash Savings" value={formatGoalCurrency(cashSavings)} text="Current cash source for goals" tone="bg-amber-50 text-amber-600" />
        <SummaryCard expanded={expanded} onClick={onToggle} icon={<TrendingUp size={20} />} label="Monthly Net Income" value={formatGoalCurrency(monthlyNetIncome)} text="Future monthly goal source" tone="bg-emerald-50 text-emerald-600" />
      </div>
      {expanded && (
        <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:grid-cols-3">
          <div className="rounded-2xl bg-slate-50 p-4">
            <Row label="On track" value={String(onTrackGoals)} tone="text-emerald-600" />
            <Row label="Behind" value={String(behindGoals)} tone="text-amber-600" />
            <Row label="Completed" value={String(completedGoals)} tone="text-blue-600" />
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <label className="block text-sm font-semibold text-slate-600">
              Allocatable ratio
              <input className="mt-2 w-full accent-blue-600" type="range" min={minAllocatableRatio} max="100" value={allocatableRatio} onChange={(event) => onAllocatableRatioChange(Number(event.target.value))} />
            </label>
            <Row label="Allocatable" value={`${formatGoalCurrency(cashAllocatable)} (${allocatableRatio}%)`} tone="text-blue-600" />
            <Row label="Already assigned" value={formatGoalCurrency(cashAlreadyAssigned)} tone="text-emerald-600" />
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <label className="block text-sm font-semibold text-slate-600">
              Monthly allocatable ratio
              <input
                className="mt-2 w-full accent-blue-600"
                type="range"
                min="0"
                max="100"
                value={monthlyAllocatableRatio}
                onChange={(event) => onMonthlyAllocatableRatioChange(Number(event.target.value))}
                onMouseUp={(event) => onMonthlyAllocatableRatioCommit(Number(event.currentTarget.value))}
                onTouchEnd={(event) => onMonthlyAllocatableRatioCommit(Number(event.currentTarget.value))}
                onBlur={(event) => onMonthlyAllocatableRatioCommit(Number(event.currentTarget.value))}
              />
            </label>
            <Row label="Allocatable" value={`${formatGoalCurrency(monthlyAllocatable)} (${monthlyAllocatableRatio}%)`} tone="text-blue-600" />
            <Row label="Already assigned" value={formatGoalCurrency(monthlyAssigned)} tone="text-amber-500" />
          </div>
        </div>
      )}
    </section>
  );
}
