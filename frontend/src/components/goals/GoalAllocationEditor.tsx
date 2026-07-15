import { ChevronDown, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import type { Goal, GoalAllocation } from "../../types/goalTypes";
import { formatGoalCurrency } from "../../utils/goalUtils";

type Props = {
  goals: Goal[];
  allocations: GoalAllocation[];
  monthlyAllocatable: number;
  onApply: (ratios: number[]) => void;
};

function cleanRatio(value: string) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.min(Math.max(parsed, 0), 100);
}

export default function GoalAllocationEditor({ goals, allocations, monthlyAllocatable, onApply }: Props) {
  const [open, setOpen] = useState(false);
  const [drafts, setDrafts] = useState<string[]>([]);
  const [error, setError] = useState("");
  const ratios = drafts.map(cleanRatio);
  const total = ratios.reduce((sum, value) => sum + value, 0);

  useEffect(() => {
    setDrafts(allocations.map((item) => String(Number((item?.ratio ?? 0).toFixed(1)))));
  }, [allocations]);

  function apply() {
    if (total > 100) {
      setError("Monthly allocation cannot exceed 100% of allocatable income.");
      return;
    }
    setError("");
    onApply(ratios);
    setOpen(false);
  }

  if (!goals.length) return null;

  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen((value) => !value)} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-600 shadow-sm hover:border-blue-200 hover:text-blue-600">
        <SlidersHorizontal size={16} /> Monthly Allocation <ChevronDown className={`transition ${open ? "rotate-180" : ""}`} size={16} />
      </button>
      {open && <AllocationPanel error={error} goals={goals} drafts={drafts} total={total} monthlyAllocatable={monthlyAllocatable} setDrafts={setDrafts} onApply={apply} />}
    </div>
  );
}

function AllocationPanel({ error, goals, drafts, total, monthlyAllocatable, setDrafts, onApply }: { error: string; goals: Goal[]; drafts: string[]; total: number; monthlyAllocatable: number; setDrafts: React.Dispatch<React.SetStateAction<string[]>>; onApply: () => void }) {
  return (
    <div className="absolute right-0 z-20 mt-2 w-[min(30rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-4 shadow-xl">
      <div className="mb-3 flex items-center justify-between text-sm font-bold">
        <span className={total > 100 ? "text-red-600" : "text-slate-500"}>{Number(total.toFixed(1))}% allocated</span>
        <span className="text-slate-400">Max 100%</span>
      </div>
      {error && <p className="mb-3 rounded-xl bg-red-50 p-3 text-xs font-semibold text-red-600">{error}</p>}
      <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
        {goals.map((goal, index) => <AllocationRow key={goal.id} goal={goal} index={index} value={drafts[index] ?? "0"} monthlyAllocatable={monthlyAllocatable} setDrafts={setDrafts} />)}
      </div>
      <button type="button" onClick={onApply} className="mt-4 w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white hover:bg-blue-700">
        Apply
      </button>
    </div>
  );
}

function AllocationRow({ goal, index, value, monthlyAllocatable, setDrafts }: { goal: Goal; index: number; value: string; monthlyAllocatable: number; setDrafts: React.Dispatch<React.SetStateAction<string[]>> }) {
  const amount = monthlyAllocatable * cleanRatio(value) / 100;
  return (
    <label className="grid grid-cols-[1fr_5.5rem] items-center gap-3 rounded-xl bg-slate-50 p-3">
      <span className="min-w-0">
        <b className="block truncate text-sm text-slate-900">{index + 1}. {goal.name}</b>
        <span className="mt-1 block text-xs font-semibold text-slate-400">{formatGoalCurrency(amount)}</span>
      </span>
      <input
        type="number"
        min="0"
        max="100"
        step="0.1"
        value={value}
        onChange={(event) => setDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item))}
        className="rounded-xl border border-slate-200 px-3 py-2 text-right text-sm font-bold outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
      />
    </label>
  );
}
