import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { createGoal, getGoalAllocationSettings, getGoals, getGoalSummary, updateGoalAllocationSettings, type GoalSummaryRecord, type MonthlyAllocation } from "../api/goals";
import CreateGoalModal from "../components/goals/CreateGoalModal";
import GoalAllocationEditor from "../components/goals/GoalAllocationEditor";
import GoalDetailsModal from "../components/goals/GoalDetailsModal";
import GoalFilters from "../components/goals/GoalFilters";
import GoalList from "../components/goals/GoalList";
import GoalSummary from "../components/goals/GoalSummary";
import PrimaryButton from "../components/PrimaryButton";
import type { Goal, GoalAllocation, GoalFilter } from "../types/goalTypes";
import { filterGoals, goalFromApi, goalStatus, goalToPayload } from "../utils/goalUtils";

const emptyGoalSummary: GoalSummaryRecord = {
  total_goals: 0, on_track_goals: 0, behind_goals: 0, completed_goals: 0,
  cash_savings: 0, cash_allocatable: 0, cash_already_assigned: 0,
  cash_unassigned: 0,
  monthly_net_income: 0, monthly_allocatable: 0, monthly_already_assigned: 0,
  monthly_unassigned: 0,
  total_target_amount: 0, total_current_amount: 0, total_monthly_contribution: 0,
};

function roundMoney(value: number) {
  return Math.round((Number.isFinite(value) ? value : 0) * 100) / 100;
}

const emptyMonthlyAllocation: MonthlyAllocation = {
  monthly_net_income: 0, monthly_allocatable: 0, already_assigned: 0,
  unassigned: 0, goals: [],
};

function allocations(goals: Goal[], monthly: MonthlyAllocation): GoalAllocation[] {
  const byGoal = new Map(monthly.goals.map((item) => [item.goal_id, item]));
  return goals.map((goal) => {
    const row = byGoal.get(Number(goal.id));
    return { goalId: goal.id, ratio: Number(row?.ratio ?? 0), monthlyAmount: Number(row?.monthly_amount ?? 0) };
  });
}

function ratiosByGoal(goals: Goal[], ratios: Map<number, number>) {
  return goals.map((goal) => ratios.get(Number(goal.id)) ?? 0);
}

function monthlyFromRatios(netIncome: number, monthlyRatio: number, goals: Goal[], ratios: number[]): MonthlyAllocation {
  const monthly_allocatable = roundMoney(Math.max(netIncome, 0) * monthlyRatio / 100);
  const rows = goals.map((goal, index) => {
    const ratio = roundMoney(ratios[index] ?? 0);
    return { goal_id: Number(goal.id), ratio, monthly_amount: roundMoney(monthly_allocatable * ratio / 100) };
  });
  const already_assigned = roundMoney(rows.reduce((sum, item) => sum + item.monthly_amount, 0));
  return { monthly_net_income: netIncome, monthly_allocatable, already_assigned, unassigned: roundMoney(Math.max(monthly_allocatable - already_assigned, 0)), goals: rows };
}

function minCashRatio(summary: GoalSummaryRecord) {
  if (summary.cash_savings <= 0 || summary.cash_already_assigned <= 0) return 0;
  return Math.min(100, Math.ceil((summary.cash_already_assigned / summary.cash_savings) * 10000) / 100);
}

export default function MyGoals() {
  const navigate = useNavigate();
  const location = useLocation();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [filter, setFilter] = useState<GoalFilter>("In Progress");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Goal | null>(null);
  const [goalSummary, setGoalSummary] = useState<GoalSummaryRecord>(emptyGoalSummary);
  const [allocatableRatio, setAllocatableRatio] = useState(50);
  const [monthlyAllocatableRatio, setMonthlyAllocatableRatio] = useState(50);
  const [monthlyRatios, setMonthlyRatios] = useState<number[]>([]);
  const [monthlyAllocation, setMonthlyAllocation] = useState<MonthlyAllocation>(emptyMonthlyAllocation);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const orderedGoals = goals;
  const allocationGoals = useMemo(() => orderedGoals.filter((goal) => goalStatus(goal) !== "Completed"), [orderedGoals]);
  const visibleGoals = useMemo(() => filterGoals(orderedGoals, filter), [filter, orderedGoals]);
  const monthlyAllocatable = monthlyAllocation.monthly_allocatable;
  const goalAllocations = useMemo(() => allocations(orderedGoals, monthlyAllocation), [monthlyAllocation, orderedGoals]);
  const allocationGoalAllocations = useMemo(() => allocations(allocationGoals, monthlyAllocation), [allocationGoals, monthlyAllocation]);
  const monthlyAmounts = Object.fromEntries(goalAllocations.map((item) => [item.goalId, item.monthlyAmount]));
  const monthlyAssigned = monthlyAllocation.already_assigned;
  const minimumCashRatio = minCashRatio(goalSummary);
  const displayedCashAllocatable = Math.max(goalSummary.cash_allocatable, goalSummary.cash_already_assigned);

  useEffect(() => { void loadPage(); }, []);

  useEffect(() => {
    const goalId = Number((location.state as { goalId?: number } | null)?.goalId);
    if (!goalId || !goals.length) return;
    const goal = goals.find((item) => item.apiId === goalId);
    if (goal) setSelected(goal);
    navigate(location.pathname, { replace: true });
  }, [goals, location.pathname, location.state, navigate]);

  async function loadPage() {
    setLoading(true); setError("");
    try {
      const [goalRows, settings, goalsSummary] = await Promise.all([getGoals(), getGoalAllocationSettings(), getGoalSummary()]);
      const mappedGoals = goalRows.map(goalFromApi);
      const activeGoals = mappedGoals.filter((goal) => goalStatus(goal) !== "Completed");
      const ratioMap = new Map(settings.goal_monthly_ratios.map((item) => [item.goal_id, item.ratio]));
      const ratioList = ratiosByGoal(activeGoals, ratioMap);
      const cashRatio = Math.max(settings.cash_allocatable_ratio, minCashRatio(goalsSummary));
      setGoals(mappedGoals);
      setGoalSummary(goalsSummary);
      setAllocatableRatio(cashRatio);
      setMonthlyAllocatableRatio(settings.monthly_allocatable_ratio);
      setMonthlyAllocation(settings.monthly_allocation);
      setMonthlyRatios(ratioList);
      window.dispatchEvent(new Event("financeai:goals-updated"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load goals.");
    } finally {
      setLoading(false);
    }
  }

  async function addGoal(goal: Goal) {
    await createGoal(goalToPayload({ ...goal, priority: "Medium" }, Math.min(goals.length + 1, 5)));
    await loadPage();
  }

  function applyMonthlyRatios(ratios: number[]) {
    const normalized = ratios.map((ratio) => Math.min(Math.max(ratio || 0, 0), 100));
    setMonthlyRatios(normalized);
    void saveAllocationSettings(allocatableRatio, monthlyAllocatableRatio, normalized, allocationGoals);
  }

  async function saveAllocationSettings(cashRatio: number, monthlyRatio: number, ratios: number[], ratioGoals = allocationGoals) {
    setError("");
    try {
      if (ratioGoals.length && !ratios.length) return;
      const goalRatios = ratioGoals.map((goal, index) => ({ goal_id: Number(goal.id), ratio: roundMoney(ratios[index] ?? 0) }));
      const settings = await updateGoalAllocationSettings({
        cash_allocatable_ratio: cashRatio,
        monthly_allocatable_ratio: monthlyRatio,
        goal_monthly_ratios: goalRatios,
      });
      const [records, nextSummary] = await Promise.all([getGoals(), getGoalSummary()]);
      setGoals(records.map(goalFromApi)); setGoalSummary(nextSummary);
      setMonthlyAllocation(settings.monthly_allocation);
      const ratioMap = new Map(goalRatios.map((item) => [item.goal_id, item.ratio]));
      setMonthlyRatios(ratiosByGoal(records.map(goalFromApi).filter((goal) => goalStatus(goal) !== "Completed"), ratioMap));
      window.dispatchEvent(new Event("financeai:goals-updated"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save allocation.");
    }
  }

  function changeCashRatio(value: number) {
    const safeValue = Math.max(value, minimumCashRatio);
    setAllocatableRatio(safeValue);
    void saveAllocationSettings(safeValue, monthlyAllocatableRatio, monthlyRatios, allocationGoals);
  }

  function changeMonthlyRatio(value: number) {
    setMonthlyAllocatableRatio(value);
    setMonthlyAllocation(monthlyFromRatios(goalSummary.monthly_net_income, value, allocationGoals, monthlyRatios));
  }

  function commitMonthlyRatio() {
    void saveAllocationSettings(allocatableRatio, monthlyAllocatableRatio, monthlyRatios, allocationGoals);
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
            totalGoals={goalSummary.total_goals}
            onTrackGoals={goalSummary.on_track_goals}
            behindGoals={goalSummary.behind_goals}
            completedGoals={goalSummary.completed_goals}
            cashSavings={goalSummary.cash_savings}
            cashAllocatable={displayedCashAllocatable}
            cashAlreadyAssigned={goalSummary.cash_already_assigned}
            allocatableRatio={allocatableRatio}
            minAllocatableRatio={minimumCashRatio}
            monthlyAllocatableRatio={monthlyAllocatableRatio}
            monthlyNetIncome={goalSummary.monthly_net_income}
            monthlyAllocatable={goalSummary.monthly_allocatable}
            monthlyAssigned={monthlyAssigned}
            expanded={summaryExpanded}
            onToggle={() => setSummaryExpanded((value) => !value)}
            onAllocatableRatioChange={changeCashRatio}
            onMonthlyAllocatableRatioChange={changeMonthlyRatio}
            onMonthlyAllocatableRatioCommit={commitMonthlyRatio}
          />
          <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <GoalFilters filter={filter} onFilterChange={setFilter} />
            <GoalAllocationEditor goals={allocationGoals} allocations={allocationGoalAllocations} onApply={applyMonthlyRatios} />
          </section>
          <GoalList goals={visibleGoals} monthlyAmounts={monthlyAmounts} onOpen={setSelected} />
        </>
      )}
      {creating && <CreateGoalModal onClose={() => setCreating(false)} onCreate={addGoal} />}
      {selected && <GoalDetailsModal goal={selected} onClose={() => setSelected(null)} onAskAdvisor={askAdvisor} onSaved={loadPage} />}
    </main>
  );
}
