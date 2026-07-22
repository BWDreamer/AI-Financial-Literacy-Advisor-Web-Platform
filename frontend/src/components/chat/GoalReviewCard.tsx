import { Calendar, Target, Wallet } from "lucide-react";

export type GoalReviewCardData = {
  kind: "goal_review";
  version: 1;
  goal_id: number;
  name: string;
  category: string;
  target_amount: string | number;
  current_amount: string | number;
  monthly_contribution: string | number;
  target_date: string;
  priority: string;
  status: "on_track" | "behind" | "completed";
  progress_percentage: string | number;
  required_monthly?: string | number;
  monthly_difference?: string | number;
  months_remaining?: number;
  projected_completion_date?: string | null;
  category_details?: Record<string, unknown>;
};

const GOAL_REVIEW_MESSAGE_PREFIX = "[FinanceAI goal review card:v1]";
const GOAL_REVIEW_MESSAGE_SUFFIX = "[/FinanceAI goal review card]";

function numberValue(value: string | number | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrency(value: string | number | undefined) {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 0,
  }).format(numberValue(value));
}

function formatDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function isGoalReviewCardData(value: unknown): value is GoalReviewCardData {
  if (!value || typeof value !== "object") return false;
  const card = value as Record<string, unknown>;
  return (
    card.kind === "goal_review"
    && card.version === 1
    && typeof card.goal_id === "number"
    && typeof card.name === "string"
    && typeof card.category === "string"
    && typeof card.target_date === "string"
    && typeof card.priority === "string"
    && ["on_track", "behind", "completed"].includes(String(card.status))
    && ["string", "number"].includes(typeof card.target_amount)
    && ["string", "number"].includes(typeof card.current_amount)
    && ["string", "number"].includes(typeof card.monthly_contribution)
    && ["string", "number"].includes(typeof card.progress_percentage)
  );
}

export function parseGoalReviewMessage(
  content: string,
): GoalReviewCardData | null {
  const start = `${GOAL_REVIEW_MESSAGE_PREFIX}\n`;
  const end = `\n${GOAL_REVIEW_MESSAGE_SUFFIX}`;
  if (!content.startsWith(start) || !content.endsWith(end)) return null;
  try {
    const payload = JSON.parse(
      content.slice(start.length, -end.length),
    ) as unknown;
    return isGoalReviewCardData(payload) ? payload : null;
  } catch {
    return null;
  }
}

function statusStyle(status: GoalReviewCardData["status"]) {
  if (status === "completed") {
    return {
      label: "Completed",
      badge: "bg-emerald-50 text-emerald-700",
      bar: "bg-emerald-500",
    };
  }
  if (status === "behind") {
    return {
      label: "Behind",
      badge: "bg-amber-50 text-amber-700",
      bar: "bg-amber-500",
    };
  }
  return {
    label: "On track",
    badge: "bg-blue-50 text-blue-700",
    bar: "bg-blue-600",
  };
}

function Metric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex min-w-0 items-center gap-3 py-3">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-500">
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-xs font-semibold text-slate-500">
          {label}
        </span>
        <span className="mt-0.5 block truncate text-sm font-bold text-slate-900">
          {value}
        </span>
      </span>
    </div>
  );
}

export default function GoalReviewCard({
  goal,
  pending = false,
}: {
  goal: GoalReviewCardData;
  pending?: boolean;
}) {
  const progress = Math.min(
    Math.max(numberValue(goal.progress_percentage), 0),
    100,
  );
  const style = statusStyle(goal.status);
  const difference = numberValue(goal.monthly_difference);
  const hasAnalysis = goal.required_monthly !== undefined;

  return (
    <article
      aria-label={`Goal review for ${goal.name}`}
      className="w-full overflow-hidden rounded-2xl border border-blue-200 bg-white text-left shadow-sm"
    >
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-blue-100 bg-blue-50/70 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-blue-600 text-white">
            <Target size={22} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase text-blue-700">
              Goal sent for review
            </p>
            <h3 className="mt-1 truncate text-lg font-bold text-slate-950">
              {goal.name}
            </h3>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
            {goal.category}
          </span>
          <span className={`rounded-full px-3 py-1 text-xs font-bold ${style.badge}`}>
            {pending ? "Sending..." : style.label}
          </span>
        </div>
      </header>

      <div className="px-5 py-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-slate-500">Progress</p>
            <p className="mt-1 text-xl font-bold text-slate-950">
              {formatCurrency(goal.current_amount)}
              <span className="text-sm font-semibold text-slate-500">
                {" "}/ {formatCurrency(goal.target_amount)}
              </span>
            </p>
          </div>
          <p className="text-lg font-bold text-slate-900">
            {Math.round(progress)}%
          </p>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full ${style.bar}`}
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mt-3 grid divide-y divide-slate-100 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <Metric
            label="Monthly contribution"
            value={formatCurrency(goal.monthly_contribution)}
            icon={<Wallet size={17} aria-hidden="true" />}
          />
          <div className="sm:px-4">
            <Metric
              label="Target date"
              value={formatDate(goal.target_date)}
              icon={<Calendar size={17} aria-hidden="true" />}
            />
          </div>
          <div className="sm:pl-4">
            <Metric
              label="Priority"
              value={goal.priority}
              icon={<Target size={17} aria-hidden="true" />}
            />
          </div>
        </div>

        {hasAnalysis && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs">
            <span className="font-semibold text-slate-500">
              Required monthly:{" "}
              <b className="text-slate-800">
                {formatCurrency(goal.required_monthly)}
              </b>
            </span>
            <span className={`font-bold ${difference < 0 ? "text-amber-700" : "text-emerald-700"}`}>
              Monthly difference: {difference >= 0 ? "+" : "-"}
              {formatCurrency(Math.abs(difference))}
            </span>
          </div>
        )}
      </div>
    </article>
  );
}
