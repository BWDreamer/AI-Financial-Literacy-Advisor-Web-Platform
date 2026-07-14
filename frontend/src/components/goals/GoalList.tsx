import { Target } from "lucide-react";
import { useState } from "react";
import type { Goal } from "../../types/goalTypes";
import PrimaryButton from "../PrimaryButton";
import GoalCard from "./GoalCard";

type Props = {
  goals: Goal[];
  monthlyAdditions?: Record<string, number>;
  onCreate: () => void;
  onOpen: (goal: Goal) => void;
  onReorder?: (from: number, to: number) => void;
};

export default function GoalList({ goals, monthlyAdditions = {}, onCreate, onOpen, onReorder }: Props) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  if (!goals.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Target className="mx-auto text-blue-600" size={32} />
        <h2 className="mt-3 text-lg font-bold text-slate-900">No goals found</h2>
        <p className="mt-2 text-sm text-slate-500">Create a new goal or adjust your filters.</p>
        <PrimaryButton type="button" onClick={onCreate} className="mx-auto mt-5 w-auto px-5">
          Create Goal
        </PrimaryButton>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      {goals.map((goal) => (
        <GoalCard
          key={goal.id}
          goal={goal}
          monthlyAdded={monthlyAdditions[goal.id] || 0}
          onOpen={onOpen}
          onDragStart={onReorder ? () => setDragIndex(goals.indexOf(goal)) : undefined}
          onDragOver={onReorder ? () => {
            const to = goals.indexOf(goal);
            if (dragIndex !== null && dragIndex !== to) {
              onReorder?.(dragIndex, to);
              setDragIndex(to);
            }
          } : undefined}
        />
      ))}
    </section>
  );
}
