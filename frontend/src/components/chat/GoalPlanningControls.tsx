import {
  CreditCard,
  House,
  PiggyBank,
  ShieldCheck,
  Target,
  TrendingUp,
  Umbrella,
  type LucideIcon,
} from "lucide-react";
import type { ChatMessage } from "../../api/chat";

export type GoalCategoryId =
  | "general_saving"
  | "emergency_fund"
  | "debt_repayment"
  | "home_deposit"
  | "retirement"
  | "budget";

type GoalCategory = {
  id: GoalCategoryId;
  label: string;
  description: string;
  icon: LucideIcon;
};

type GoalPlanningUiState = {
  startMessageId: number | null;
  selectedCategory: GoalCategoryId | null;
  showCategoryOptions: boolean;
};

const GOAL_PLANNING_START_METADATA =
  "[Financial goal planning mode: choose_category]";
const GOAL_CATEGORY_METADATA_PATTERN =
  /\[Financial goal planning mode: category=([a-z_]+)\]/;
const GOAL_PLANNING_METADATA_PATTERN =
  /\s*\[Financial goal planning mode: (?:choose_category|category=[a-z_]+)\]\s*/g;

export const GOAL_PLANNING_START_MESSAGE =
  `What goal would you like to set today?\n\n${GOAL_PLANNING_START_METADATA}`;

export const goalCategories: GoalCategory[] = [
  {
    id: "general_saving",
    label: "General Saving",
    description: "Car, travel, education, or another major purchase.",
    icon: PiggyBank,
  },
  {
    id: "emergency_fund",
    label: "Emergency Fund",
    description: "Build a safety buffer for unexpected costs.",
    icon: ShieldCheck,
  },
  {
    id: "debt_repayment",
    label: "Debt Repayment",
    description: "Pay down credit card, loan, or bill debt.",
    icon: CreditCard,
  },
  {
    id: "home_deposit",
    label: "Home Deposit",
    description: "Plan for a deposit and upfront housing costs.",
    icon: House,
  },
  {
    id: "retirement",
    label: "Retirement / Super",
    description: "Track long-term retirement or super progress.",
    icon: Umbrella,
  },
  {
    id: "budget",
    label: "Budget / Cash Flow",
    description: "Improve monthly surplus and reduce pressure.",
    icon: TrendingUp,
  },
];

const goalCategoryIds = new Set(
  goalCategories.map((category) => category.id),
);

export function visibleChatMessage(content: string) {
  return content.replace(GOAL_PLANNING_METADATA_PATTERN, "").trim();
}

export function goalCategoryPrompt(categoryId: GoalCategoryId) {
  const category = goalCategories.find((item) => item.id === categoryId);
  if (!category) {
    throw new Error(`Unknown goal category: ${categoryId}`);
  }
  return [
    `What ${category.label} goal would you like to set?`,
    `[Financial goal planning mode: category=${category.id}]`,
  ].join("\n\n");
}

export function getGoalPlanningUiState(
  messages: ChatMessage[],
): GoalPlanningUiState {
  let startIndex = -1;
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].content.includes(GOAL_PLANNING_START_METADATA)) {
      startIndex = index;
      break;
    }
  }
  if (startIndex < 0) {
    return {
      startMessageId: null,
      selectedCategory: null,
      showCategoryOptions: false,
    };
  }

  let categoryIndex = -1;
  let selectedCategory: GoalCategoryId | null = null;
  for (let index = startIndex + 1; index < messages.length; index += 1) {
    const match = messages[index].content.match(GOAL_CATEGORY_METADATA_PATTERN);
    const categoryId = match?.[1] as GoalCategoryId | undefined;
    if (categoryId && goalCategoryIds.has(categoryId)) {
      categoryIndex = index;
      selectedCategory = categoryId;
    }
  }

  const inputStartIndex = categoryIndex >= 0 ? categoryIndex : startIndex;
  const userSubmittedGoal = messages
    .slice(inputStartIndex + 1)
    .some((message) => message.role === "user");

  return {
    startMessageId: messages[startIndex].id,
    selectedCategory,
    showCategoryOptions: !userSubmittedGoal,
  };
}

export function GoalPlanningEntryButton({
  disabled,
  onClick,
}: {
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-blue-200 bg-white px-4 py-2.5 text-sm font-bold text-blue-700 shadow-sm transition hover:border-blue-400 hover:bg-blue-50 focus:outline-none focus:ring-4 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <Target size={18} aria-hidden="true" />
      Set a Goal
    </button>
  );
}

export function GoalCategoryGrid({
  disabled,
  selectedCategory,
  onSelect,
}: {
  disabled: boolean;
  selectedCategory: GoalCategoryId | null;
  onSelect: (categoryId: GoalCategoryId) => void;
}) {
  return (
    <section
      aria-label="Goal categories"
      className="mt-4 grid w-full gap-3 lg:grid-cols-2"
    >
      {goalCategories.map((category) => {
        const Icon = category.icon;
        const selected = selectedCategory === category.id;
        return (
          <button
            key={category.id}
            type="button"
            disabled={disabled}
            aria-pressed={selected}
            onClick={() => onSelect(category.id)}
            className={`flex min-h-24 items-center gap-5 rounded-2xl border p-5 text-left transition focus:outline-none focus:ring-4 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-60 ${
              selected
                ? "border-blue-400 bg-blue-50 ring-2 ring-blue-100"
                : "border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/50"
            }`}
          >
            <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-white text-blue-600 shadow-sm ring-1 ring-slate-100">
              <Icon size={25} aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block text-base font-bold text-slate-900">
                {category.label}
              </span>
              <span className="mt-1 block text-sm leading-5 text-slate-500">
                {category.description}
              </span>
            </span>
          </button>
        );
      })}
    </section>
  );
}
