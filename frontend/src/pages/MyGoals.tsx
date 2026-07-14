import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import CreateGoalModal from "../components/goals/CreateGoalModal";
import GoalDetailsModal from "../components/goals/GoalDetailsModal";
import GoalFilters from "../components/goals/GoalFilters";
import GoalList from "../components/goals/GoalList";
import GoalSummary from "../components/goals/GoalSummary";
import PrimaryButton from "../components/PrimaryButton";
import { getFinancialSummary } from "../api/financials";
import type { Goal, GoalFilter, GoalSort } from "../types/goalTypes";
import { filterGoals, mockGoals, sortGoals } from "../utils/goalUtils";

export default function MyGoals() {
  const navigate = useNavigate();
  const [goals, setGoals] = useState<Goal[]>(mockGoals);
  const [filter, setFilter] = useState<GoalFilter>("All");
  const [sort, setSort] = useState<GoalSort>("Recent");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Goal | null>(null);
  const [cashSavings, setCashSavings] = useState(0);
  const visibleGoals = useMemo(() => sortGoals(filterGoals(goals, filter), sort), [filter, goals, sort]);

  useEffect(() => {
    getFinancialSummary().then((summary) => setCashSavings(Number(summary.cash_savings || 0))).catch(() => setCashSavings(0));
  }, []);

  function askAdvisor(goal: Goal) {
    setSelected(null);
    navigate("/advisor-chat", { state: { goalId: goal.id, goalName: goal.name, mode: "goal-review" } });
  }

  return (
    <main className="min-h-screen space-y-6 bg-slate-50 p-4 sm:p-6 lg:p-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">My Goals</h1>
          <p className="mt-2 text-slate-500">Track your progress and achieve your financial goals</p>
        </div>
        <PrimaryButton type="button" onClick={() => setCreating(true)} className="w-full sm:w-auto">
          <span className="inline-flex items-center justify-center gap-2"><Plus size={18} />Create Goal</span>
        </PrimaryButton>
      </header>
      <GoalSummary goals={goals} totalSaved={cashSavings} />
      <GoalFilters filter={filter} sort={sort} onFilterChange={setFilter} onSortChange={setSort} />
      <GoalList goals={visibleGoals} onCreate={() => setCreating(true)} onOpen={setSelected} />
      {creating && <CreateGoalModal onClose={() => setCreating(false)} onCreate={(goal) => setGoals((current) => [goal, ...current])} />}
      {selected && <GoalDetailsModal goal={selected} onClose={() => setSelected(null)} onAskAdvisor={askAdvisor} />}
    </main>
  );
}
