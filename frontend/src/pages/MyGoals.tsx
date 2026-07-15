import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getFinancialSummary, type FinancialSummary } from "../api/financials";
import { createGoal, getGoals, updateGoal } from "../api/goals";
import CreateGoalModal from "../components/goals/CreateGoalModal";
import GoalAllocationEditor from "../components/goals/GoalAllocationEditor";
import GoalDetailsModal from "../components/goals/GoalDetailsModal";
import GoalFilters from "../components/goals/GoalFilters";
import GoalList from "../components/goals/GoalList";
import GoalSummary from "../components/goals/GoalSummary";
import PrimaryButton from "../components/PrimaryButton";
import type { Goal, GoalAllocation, GoalFilter } from "../types/goalTypes";
import { filterGoals, goalFromApi, goalToPayload } from "../utils/goalUtils";

const emptySummary: FinancialSummary = {
  total_assets: 0, total_debts: 0, net_worth: 0, cash_savings: 0, monthly_income: 0, monthly_expenses: 0, monthly_cash_flow: 0,
  asset_allocation: [], debt_breakdown: [], cash_savings_trend: [], recent_cash_flows: [],
};

function roundMoney(value: number) {
  return Math.round((Number.isFinite(value) ? value : 0) * 100) / 100;
}

function ratiosFromGoals(goals: Goal[], monthlyAllocatable: number) {
  return goals.map((goal) => monthlyAllocatable > 0 ? Math.min(goal.monthlyContribution / monthlyAllocatable * 100, 100) : 0);
}

function allocations(goals: Goal[], monthlyRatios: number[], cashSavings: number, allocatedRatio: number, monthlyAllocatable: number): GoalAllocation[] {
  const cashPool = cashSavings * allocatedRatio / 100;
  const monthlyAmounts = goals.map((_, index) => roundMoney(monthlyAllocatable * (monthlyRatios[index] ?? 0) / 100));
  const totalAssigned = monthlyAmounts.reduce((sum, value) => sum + value, 0);
  return goals.map((goal, index) => {
    const monthlyAmount = monthlyAmounts[index] ?? goal.monthlyContribution;
    const ratio = Math.min(Math.max(monthlyRatios[index] ?? 0, 0), 100);
    const currentAllocation = totalAssigned > 0 ? cashPool * monthlyAmount / totalAssigned : 0;
    return { goalId: goal.id, ratio, currentAllocation, monthlyAmount };
  });
}

export default function MyGoals() {
  const navigate = useNavigate();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [filter, setFilter] = useState<GoalFilter>("All");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Goal | null>(null);
  const [summary, setSummary] = useState<FinancialSummary>(emptySummary);
  const [allocatableRatio, setAllocatableRatio] = useState(50);
  const [monthlyAllocatableRatio, setMonthlyAllocatableRatio] = useState(50);
  const [monthlyRatios, setMonthlyRatios] = useState<number[]>([]);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const orderedGoals = goals;
  const visibleGoals = useMemo(() => filterGoals(orderedGoals, filter), [filter, orderedGoals]);
  const monthlyNetIncome = summary.monthly_income - summary.monthly_expenses;
  const monthlyAllocatable = Math.max(monthlyNetIncome, 0) * monthlyAllocatableRatio / 100;
  const goalAllocations = useMemo(() => allocations(orderedGoals, monthlyRatios, summary.cash_savings, allocatableRatio, monthlyAllocatable), [allocatableRatio, monthlyAllocatable, monthlyRatios, orderedGoals, summary.cash_savings]);
  const monthlyAdditions = Object.fromEntries(goalAllocations.map((item) => [item.goalId, item.monthlyAmount]));
  const monthlyAssigned = goalAllocations.reduce((sum, item) => sum + item.monthlyAmount, 0);

  useEffect(() => { void loadPage(); }, []);
  useEffect(() => {
    setMonthlyRatios((current) => current.length === orderedGoals.length ? current : ratiosFromGoals(orderedGoals, monthlyAllocatable));
  }, [monthlyAllocatable, orderedGoals]);
  useEffect(() => {
    const changed = orderedGoals.some((goal, index) => Math.round(goal.monthlyContribution) !== Math.round(goalAllocations[index]?.monthlyAmount ?? 0));
    if (!changed || goalAllocations.length !== orderedGoals.length) return;
    const timer = window.setTimeout(() => { void saveMonthlyAmounts(); }, 700);
    return () => window.clearTimeout(timer);
  }, [goalAllocations, orderedGoals]);

  async function loadPage() {
    setLoading(true); setError("");
    try {
      const [goalRows, finance] = await Promise.all([getGoals(), getFinancialSummary()]);
      setGoals(goalRows.map(goalFromApi));
      setSummary(finance);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load goals.");
    } finally {
      setLoading(false);
    }
  }

  async function addGoal(goal: Goal) {
    const record = await createGoal(goalToPayload({ ...goal, priority: "Medium" }, Math.min(goals.length + 1, 5)));
    setGoals((current) => [goalFromApi(record), ...current]);
  }

  function applyMonthlyRatios(ratios: number[]) {
    setMonthlyRatios(ratios.map((ratio) => Math.min(Math.max(ratio || 0, 0), 100)));
  }

  async function saveMonthlyAmounts() {
    setError("");
    try {
      const updates = orderedGoals.map((goal, index) => {
        const monthlyContribution = roundMoney(goalAllocations[index]?.monthlyAmount ?? goal.monthlyContribution);
        return updateGoal(Number(goal.id), goalToPayload({ ...goal, monthlyContribution }));
      });
      const records = await Promise.all(updates);
      setGoals(records.map(goalFromApi));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save allocation.");
    }
  }

  function askAdvisor(goal: Goal) {
    setSelected(null);
    navigate("/advisor-chat", { state: { goalId: goal.id, goalName: goal.name, mode: "goal-review" } });
  }

  return (
    <main className="min-h-screen space-y-6 bg-slate-50 p-4 sm:p-6 lg:p-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">My Goals</h1>
          <p className="mt-2 text-slate-500">Allocate current cash savings and future monthly net income toward your goals.</p>
        </div>
        <PrimaryButton type="button" onClick={() => setCreating(true)} className="w-full sm:w-auto">
          <span className="inline-flex items-center justify-center gap-2"><Plus size={18} />Create Goal</span>
        </PrimaryButton>
      </header>
      {error && <p className="rounded-2xl bg-red-50 p-4 text-sm font-semibold text-red-600">{error}</p>}
      {loading ? <p className="rounded-2xl bg-white p-6 text-slate-500 shadow-sm">Loading goals...</p> : (
        <>
          <GoalSummary
            goals={goals}
            cashSavings={summary.cash_savings}
            allocatableRatio={allocatableRatio}
            monthlyAllocatableRatio={monthlyAllocatableRatio}
            monthlyIncome={summary.monthly_income}
            monthlyExpenses={summary.monthly_expenses}
            monthlyAssigned={monthlyAssigned}
            expanded={summaryExpanded}
            onToggle={() => setSummaryExpanded((value) => !value)}
            onAllocatableRatioChange={setAllocatableRatio}
            onMonthlyAllocatableRatioChange={setMonthlyAllocatableRatio}
          />
          <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <GoalFilters filter={filter} onFilterChange={setFilter} />
            <GoalAllocationEditor goals={orderedGoals} allocations={goalAllocations} monthlyAllocatable={monthlyAllocatable} onApply={applyMonthlyRatios} />
          </section>
          <GoalList goals={visibleGoals} monthlyAdditions={monthlyAdditions} onCreate={() => setCreating(true)} onOpen={setSelected} />
        </>
      )}
      {creating && <CreateGoalModal onClose={() => setCreating(false)} onCreate={addGoal} />}
      {selected && <GoalDetailsModal goal={selected} onClose={() => setSelected(null)} onAskAdvisor={askAdvisor} />}
    </main>
  );
}
