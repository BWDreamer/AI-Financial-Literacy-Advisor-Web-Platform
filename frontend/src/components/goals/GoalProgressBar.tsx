import type { GoalStatus } from "../../types/goalTypes";

const fillStyles: Record<GoalStatus, string> = {
  "On Track": "bg-emerald-500",
  Behind: "bg-amber-400",
  "Pending Archive": "bg-violet-500",
  Completed: "bg-blue-600",
};

export default function GoalProgressBar({ value, status, added = 0 }: { value: number; status: GoalStatus; added?: number }) {
  const safeValue = Math.min(Math.max(value, 0), 100);
  const safeAdded = Math.min(Math.max(added, 0), safeValue);
  return (
    <div
      role="progressbar"
      aria-label="Goal progress"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={safeValue}
      className="relative h-2 overflow-hidden rounded-full bg-slate-100"
    >
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${fillStyles[status]}`}
        style={{
          width: `${safeValue}%`,
          minWidth: safeValue > 0 ? "0.25rem" : undefined,
        }}
      />
      {safeAdded > 0 && (
        <div
          className="absolute top-0 h-full rounded-full bg-amber-400 transition-all duration-700 ease-out"
          style={{ left: `${Math.max(safeValue - safeAdded, 0)}%`, width: `${safeAdded}%` }}
        />
      )}
    </div>
  );
}
