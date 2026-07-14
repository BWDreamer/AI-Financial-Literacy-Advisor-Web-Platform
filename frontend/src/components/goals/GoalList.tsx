import { Target } from "lucide-react";
import type { Goal } from "../../types/goalTypes";
import PrimaryButton from "../PrimaryButton";
import GoalCard from "./GoalCard";

type Props = {
  goals: Goal[];
  onCreate: () => void;
  onOpen: (goal: Goal) => void;
};

export default function GoalList({ goals, onCreate, onOpen }: Props) {
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
        <GoalCard key={goal.id} goal={goal} onOpen={onOpen} />
      ))}
    </section>
  );
}
