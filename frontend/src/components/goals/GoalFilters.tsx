import type { GoalFilter, GoalSort } from "../../types/goalTypes";
import { goalFilters, goalSortOptions } from "../../utils/goalUtils";

type Props = {
  filter: GoalFilter;
  sort: GoalSort;
  onFilterChange: (filter: GoalFilter) => void;
  onSortChange: (sort: GoalSort) => void;
};

export default function GoalFilters({ filter, sort, onFilterChange, onSortChange }: Props) {
  return (
    <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-2 overflow-x-auto pb-1">
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
      </div>
      <label className="flex items-center gap-3 text-sm font-semibold text-slate-500">
        <span>Sort by</span>
        <select
          value={sort}
          onChange={(event) => onSortChange(event.target.value as GoalSort)}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        >
          {goalSortOptions.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
    </section>
  );
}
