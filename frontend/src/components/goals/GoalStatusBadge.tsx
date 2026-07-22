import type { GoalStatus } from "../../types/goalTypes";

const styles: Record<GoalStatus, string> = {
  "On Track": "bg-emerald-50 text-emerald-700",
  Behind: "bg-amber-50 text-amber-700",
  "Pending Archive": "bg-violet-50 text-violet-700",
  Completed: "bg-blue-50 text-blue-700",
};

export default function GoalStatusBadge({ status }: { status: GoalStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${styles[status]}`}>
      {status}
    </span>
  );
}
