import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MyGoals from "../MyGoals";
import {
  createGoal,
  getGoalAllocationSettings,
  getGoals,
  getGoalSummary,
  updateGoalAllocationSettings,
  type GoalRecord,
} from "../../api/goals";
import type { Goal } from "../../types/goalTypes";

const navigate = jest.fn();

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => navigate,
}));

jest.mock("../../api/goals", () => ({
  createGoal: jest.fn(),
  getGoalAllocationSettings: jest.fn(),
  getGoals: jest.fn(),
  getGoalSummary: jest.fn(),
  updateGoalAllocationSettings: jest.fn(),
}));

jest.mock("../../components/goals/GoalSummary", () => ({
  __esModule: true,
  default: ({ totalGoals, onToggle, onAllocatableRatioChange }: {
    totalGoals: number;
    onToggle: () => void;
    onAllocatableRatioChange: (value: number) => void;
  }) => (
    <section>
      <p>Total goals: {totalGoals}</p>
      <button type="button" onClick={onToggle}>Toggle summary</button>
      <button type="button" onClick={() => onAllocatableRatioChange(60)}>Set cash ratio</button>
    </section>
  ),
}));

jest.mock("../../components/goals/GoalFilters", () => ({
  __esModule: true,
  default: ({ onFilterChange }: { onFilterChange: (filter: string) => void }) => (
    <div>
      <button type="button" onClick={() => onFilterChange("All")}>All goals</button>
      <button type="button" onClick={() => onFilterChange("Behind")}>Behind goals</button>
    </div>
  ),
}));

jest.mock("../../components/goals/GoalAllocationEditor", () => ({
  __esModule: true,
  default: ({ onApply }: { onApply: (ratios: number[]) => void }) => (
    <button type="button" onClick={() => onApply([80, 20])}>Apply allocation</button>
  ),
}));

jest.mock("../../components/goals/GoalList", () => ({
  __esModule: true,
  default: ({ goals, onCreate, onOpen }: {
    goals: Goal[];
    onCreate: () => void;
    onOpen: (goal: Goal) => void;
  }) => (
    <section>
      {goals.length === 0 && <p>No goals found</p>}
      {goals.map((goal) => (
        <button key={goal.id} type="button" onClick={() => onOpen(goal)}>
          {goal.name}
        </button>
      ))}
      <button type="button" onClick={onCreate}>Create from list</button>
    </section>
  ),
}));

jest.mock("../../components/goals/CreateGoalModal", () => ({
  __esModule: true,
  default: ({ onCreate, onClose }: {
    onCreate: (goal: Goal) => void;
    onClose: () => void;
  }) => (
    <div role="dialog" aria-label="Create Goal">
      <button
        type="button"
        onClick={() => onCreate({
          id: "draft-goal",
          name: "New Emergency Fund",
          category: "Emergency Fund",
          targetAmount: 6000,
          currentAmount: 500,
          monthlyContribution: 300,
          progressPercentage: 8,
          createdAt: "2026-07-01",
          targetDate: "2027-07-01",
          priority: "Medium",
          status: "On Track",
        })}
      >
        Submit new goal
      </button>
      <button type="button" onClick={onClose}>Close create modal</button>
    </div>
  ),
}));

jest.mock("../../components/goals/GoalDetailsModal", () => ({
  __esModule: true,
  default: ({ goal, onAskAdvisor, onClose }: {
    goal: Goal;
    onAskAdvisor: (goal: Goal) => void;
    onClose: () => void;
  }) => (
    <div role="dialog" aria-label="Goal Details">
      <p>Selected goal: {goal.name}</p>
      <button type="button" onClick={() => onAskAdvisor(goal)}>Ask AI Advisor</button>
      <button type="button" onClick={onClose}>Close details</button>
    </div>
  ),
}));

const mockedGetGoals = jest.mocked(getGoals);
const mockedGetGoalAllocationSettings = jest.mocked(getGoalAllocationSettings);
const mockedGetGoalSummary = jest.mocked(getGoalSummary);
const mockedUpdateGoalAllocationSettings = jest.mocked(updateGoalAllocationSettings);
const mockedCreateGoal = jest.mocked(createGoal);

const goalRecords: GoalRecord[] = [
  {
    id: 1,
    name: "Emergency Fund",
    category: "Emergency Fund",
    target_amount: 10000,
    current_amount: 2500,
    monthly_contribution: 500,
    target_date: "2027-07-01",
    priority: 1,
    category_details: {},
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
    status: "on_track",
    progress_percentage: 25,
  },
  {
    id: 2,
    name: "Car Loan",
    category: "Debt Repayment",
    target_amount: 8000,
    current_amount: 1000,
    monthly_contribution: 100,
    target_date: "2026-12-01",
    priority: 3,
    category_details: {},
    created_at: "2026-07-02T00:00:00Z",
    updated_at: "2026-07-02T00:00:00Z",
    status: "behind",
    progress_percentage: 12.5,
  },
];

const summary = {
  total_goals: 2,
  on_track_goals: 1,
  behind_goals: 1,
  completed_goals: 0,
  cash_savings: 5000,
  cash_allocatable: 2500,
  cash_already_assigned: 500,
  monthly_net_income: 4000,
  monthly_allocatable: 2000,
  monthly_already_assigned: 800,
  total_target_amount: 18000,
  total_current_amount: 3500,
  total_monthly_contribution: 600,
};

const allocationSettings = {
  cash_allocatable_ratio: 50,
  monthly_allocatable_ratio: 50,
  goal_monthly_ratios: [
    { goal_id: 1, ratio: 60 },
    { goal_id: 2, ratio: 40 },
  ],
  monthly_allocation: {
    monthly_net_income: 4000,
    monthly_allocatable: 2000,
    already_assigned: 800,
    unassigned: 1200,
    goals: [
      { goal_id: 1, ratio: 60, monthly_amount: 1200 },
      { goal_id: 2, ratio: 40, monthly_amount: 800 },
    ],
  },
};

beforeEach(() => {
  jest.clearAllMocks();
  navigate.mockClear();
  mockedGetGoals.mockResolvedValue(goalRecords);
  mockedGetGoalSummary.mockResolvedValue(summary);
  mockedGetGoalAllocationSettings.mockResolvedValue(allocationSettings);
  mockedUpdateGoalAllocationSettings.mockResolvedValue({
    ...allocationSettings,
    cash_allocatable_ratio: 60,
  });
  mockedCreateGoal.mockResolvedValue(goalRecords[0]);
});

test("loads goals, summary and allocation settings", async () => {
  render(<MyGoals />);

  expect(screen.getByText("Loading goals...")).toBeInTheDocument();
  expect(await screen.findByText("Total goals: 2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Emergency Fund" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Car Loan" })).toBeInTheDocument();
  expect(mockedGetGoals).toHaveBeenCalledTimes(1);
  expect(mockedGetGoalAllocationSettings).toHaveBeenCalledTimes(1);
  expect(mockedGetGoalSummary).toHaveBeenCalledTimes(1);
});

test("filters goals by backend-derived status", async () => {
  const user = userEvent.setup();
  render(<MyGoals />);

  await screen.findByRole("button", { name: "Emergency Fund" });
  await user.click(screen.getByRole("button", { name: "Behind goals" }));

  expect(screen.queryByRole("button", { name: "Emergency Fund" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Car Loan" })).toBeInTheDocument();
});

test("creates a goal and reloads page data", async () => {
  const user = userEvent.setup();
  render(<MyGoals />);

  await screen.findByRole("button", { name: "Emergency Fund" });
  await user.click(screen.getByRole("button", { name: /create goal/i }));
  await user.click(screen.getByRole("button", { name: "Submit new goal" }));

  await waitFor(() => expect(mockedCreateGoal).toHaveBeenCalledWith(
    expect.objectContaining({
      name: "New Emergency Fund",
      category: "Emergency Fund",
      priority: 3,
    })
  ));
  await waitFor(() => expect(mockedGetGoals).toHaveBeenCalledTimes(2));
});

test("saves allocation settings from allocation controls", async () => {
  const user = userEvent.setup();
  render(<MyGoals />);

  await screen.findByRole("button", { name: "Emergency Fund" });
  await user.click(screen.getByRole("button", { name: "Apply allocation" }));

  await waitFor(() => expect(mockedUpdateGoalAllocationSettings).toHaveBeenCalledWith({
    cash_allocatable_ratio: 50,
    monthly_allocatable_ratio: 50,
    goal_monthly_ratios: [
      { goal_id: 1, ratio: 80 },
      { goal_id: 2, ratio: 20 },
    ],
  }));
});

test("navigates to advisor chat for a selected goal", async () => {
  const user = userEvent.setup();
  render(<MyGoals />);

  await screen.findByRole("button", { name: "Emergency Fund" });
  await user.click(screen.getByRole("button", { name: "Emergency Fund" }));
  await user.click(screen.getByRole("button", { name: /ask ai advisor/i }));

  expect(navigate).toHaveBeenCalledWith("/advisor-chat", {
    state: {
      goalId: "1",
      goalName: "Emergency Fund",
      mode: "goal-review",
    },
  });
});

test("shows an error when goal data cannot load", async () => {
  mockedGetGoals.mockRejectedValueOnce(new Error("Unable to load goals."));

  render(<MyGoals />);

  expect(await screen.findByText("Unable to load goals.")).toBeInTheDocument();
});
