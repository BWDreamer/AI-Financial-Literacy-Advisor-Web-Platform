import type { GoalStatus } from "../../types/goalTypes";

const fillStyles: Record<GoalStatus, string> = {
  "On Track": "bg-emerald-500",
  Behind: "bg-amber-400",
  Completed: "bg-blue-600",
};

export default function GoalProgressBar({ value, status }: { value: number; status: GoalStatus }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${fillStyles[status]}`}
        style={{ width: `${value}%` }}
      />
    </div>
  );
}
