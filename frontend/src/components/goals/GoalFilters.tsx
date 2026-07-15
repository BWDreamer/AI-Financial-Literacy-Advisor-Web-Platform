import type { GoalFilter } from "../../types/goalTypes";
import { goalFilters } from "../../utils/goalUtils";

type Props = {
  filter: GoalFilter;
  onFilterChange: (filter: GoalFilter) => void;
};

export default function GoalFilters({ filter, onFilterChange }: Props) {
  return (
    <section className="flex gap-2 overflow-x-auto pb-1">
      {goalFilters.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onFilterChange(item)}
          className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${filter === item ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-100"}`}
        >
          {item}
        </button>
      ))}
    </section>
  );
}
