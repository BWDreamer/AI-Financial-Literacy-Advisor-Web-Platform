import { useState } from "react";
import type { Goal } from "../../types/goalTypes";
import GoalCard from "./GoalCard";

type Props = {
  goals: Goal[];
  monthlyAmounts?: Record<string, number>;
  onOpen: (goal: Goal) => void;
  onReorder?: (from: number, to: number) => void;
};

export default function GoalList({ goals, monthlyAmounts = {}, onOpen, onReorder }: Props) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  if (!goals.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <h2 className="text-lg font-bold text-slate-900">No goals found</h2>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      {goals.map((goal) => (
        <GoalCard
          key={goal.id}
          goal={goal}
          monthlyAmount={monthlyAmounts[goal.id]}
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
