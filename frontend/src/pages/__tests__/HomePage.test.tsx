import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import HomePage from "../HomePage";
import {
  createAsset,
  createCashFlow,
  getFinancials,
  getFinancialSummary,
  type FinancialSummary,
} from "../../api/financials";

jest.mock("../../api/financials", () => ({
  createAsset: jest.fn(),
  createCashFlow: jest.fn(),
  createDebt: jest.fn(),
  createRecurringCashFlow: jest.fn(),
  getFinancials: jest.fn(),
  getFinancialSummary: jest.fn(),
}));

jest.mock("../../components/MyFinancialsPanel", () => ({
  __esModule: true,
  default: ({ onAdd }: {
    onAdd: (entry: {
      kind: "asset" | "cashflow";
      assetType?: string;
      flowType?: "income" | "expense";
      name: string;
      amount: number;
      date?: string;
    }) => void;
  }) => (
    <section>
      <button
        type="button"
        onClick={() => onAdd({
          kind: "asset",
          assetType: "cash",
          name: "Emergency cash",
          amount: 1000,
        })}
      >
        Add asset entry
      </button>
      <button
        type="button"
        onClick={() => onAdd({
          kind: "cashflow",
          flowType: "expense",
          name: "Rent",
          amount: 2000,
          date: "2026-07-22",
        })}
      >
        Add cash flow entry
      </button>
    </section>
  ),
}));

const mockedGetFinancialSummary = jest.mocked(getFinancialSummary);
const mockedGetFinancials = jest.mocked(getFinancials);
const mockedCreateAsset = jest.mocked(createAsset);
const mockedCreateCashFlow = jest.mocked(createCashFlow);

const summary: FinancialSummary = {
  total_assets: 15000,
  total_debts: 4000,
  net_worth: 11000,
  cash_savings: 6000,
  monthly_income: 5000,
  monthly_expenses: 2200,
  monthly_cash_flow: 2800,
  asset_allocation: [
    { asset_type: "cash", amount: 6000 },
    { asset_type: "stocks", amount: 9000 },
  ],
  debt_breakdown: [{ debt_type: "car_loan", amount: 4000 }],
  cash_savings_trend: [
    { month: "2026-02", amount: 3000 },
    { month: "2026-03", amount: 3500 },
    { month: "2026-04", amount: 4000 },
    { month: "2026-05", amount: 4500 },
    { month: "2026-06", amount: 5000 },
    { month: "2026-07", amount: 6000 },
  ],
  recent_cash_flows: [
    {
      id: 1,
      flow_type: "income",
      name: "Salary",
      amount: 5000,
      date: new Date().toISOString().slice(0, 10),
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
    },
  ],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetFinancialSummary.mockResolvedValue(summary);
  mockedGetFinancials.mockResolvedValue({
    assets: [],
    debts: [],
    cash_flows: summary.recent_cash_flows,
    recurring_cash_flows: [],
  });
  mockedCreateAsset.mockResolvedValue({
    id: 1,
    asset_type: "cash",
    name: "Emergency cash",
    amount: 1000,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  });
  mockedCreateCashFlow.mockResolvedValue({
    id: 2,
    flow_type: "expense",
    name: "Rent",
    amount: 2000,
    date: "2026-07-22",
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  });
});

test("loads and displays the financial dashboard summary", async () => {
  render(<HomePage />);

  expect(screen.getByText("Loading your financial dashboard...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: /insights overview/i })).toBeInTheDocument();
  expect(screen.getByText("Net Worth")).toBeInTheDocument();
  expect(screen.getByText("$11,000")).toBeInTheDocument();
  expect(screen.getByText("Cash Savings")).toBeInTheDocument();
  expect(screen.getAllByText("$6,000").length).toBeGreaterThan(0);
  expect(screen.getByText("Monthly Cash Flow")).toBeInTheDocument();
  expect(screen.getByText("Asset Allocation")).toBeInTheDocument();
  expect(screen.getByText("Salary")).toBeInTheDocument();
  expect(mockedGetFinancialSummary).toHaveBeenCalledTimes(1);
  expect(mockedGetFinancials).toHaveBeenCalledTimes(1);
});

test("shows an error when financial data cannot load", async () => {
  mockedGetFinancialSummary.mockRejectedValueOnce(new Error("Unable to load financial data."));

  render(<HomePage />);

  expect(await screen.findByText("Unable to load financial data.")).toBeInTheDocument();
});

test("adds an asset entry and refreshes financial data", async () => {
  const user = userEvent.setup();
  render(<HomePage />);

  await screen.findByRole("heading", { name: /insights overview/i });
  await user.click(screen.getByRole("button", { name: "Add asset entry" }));

  await waitFor(() => expect(mockedCreateAsset).toHaveBeenCalledWith({
    asset_type: "cash",
    name: "Emergency cash",
    amount: 1000,
  }));
  await waitFor(() => expect(mockedGetFinancialSummary).toHaveBeenCalledTimes(2));
});

test("adds a cash flow entry and refreshes financial data", async () => {
  const user = userEvent.setup();
  render(<HomePage />);

  await screen.findByRole("heading", { name: /insights overview/i });
  await user.click(screen.getByRole("button", { name: "Add cash flow entry" }));

  await waitFor(() => expect(mockedCreateCashFlow).toHaveBeenCalledWith({
    flow_type: "expense",
    name: "Rent",
    amount: 2000,
    date: "2026-07-22",
  }));
  await waitFor(() => expect(mockedGetFinancials).toHaveBeenCalledTimes(2));
});
