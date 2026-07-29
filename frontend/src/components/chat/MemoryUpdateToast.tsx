import { Brain, X } from "lucide-react";

type MemoryUpdateToastProps = {
  count: number;
  onDismiss: () => void;
};

export default function MemoryUpdateToast({
  count,
  onDismiss,
}: MemoryUpdateToastProps) {
  const detailLabel = count === 1
    ? "1 detail saved to your memories."
    : `${count} details saved to your memories.`;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-[5.75rem] left-4 right-4 z-[80] sm:right-auto sm:w-[22rem] lg:bottom-6 lg:left-[21.5rem]"
    >
      <div className="flex items-start gap-3 rounded-lg border border-emerald-200 bg-white p-4 shadow-xl">
        <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
          <Brain size={21} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-slate-950">Memory updated</p>
          <p className="mt-1 text-sm leading-5 text-slate-600">
            {detailLabel}
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="grid size-8 shrink-0 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
          aria-label="Dismiss memory update"
          title="Dismiss"
        >
          <X size={17} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
