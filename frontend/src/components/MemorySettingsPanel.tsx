import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Download, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import {
  createMemory,
  deleteMemory,
  exportMemories,
  getMemories,
  updateMemory,
} from "../api/memory";
import type { Memory, MemoryCategory } from "../api/memory";

const categories: { value: MemoryCategory; label: string }[] = [
  { value: "debt", label: "Debt" },
  { value: "expense", label: "Expense" },
  { value: "income", label: "Income" },
  { value: "asset", label: "Asset" },
  { value: "goal", label: "Goal" },
  { value: "preference", label: "Preference" },
  { value: "profile", label: "Profile" },
  { value: "other", label: "Other" },
];

function dateLabel(value?: string | null) {
  if (!value) return "Never used";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function categoryLabel(category: MemoryCategory) {
  return categories.find((item) => item.value === category)?.label || "Other";
}

export default function MemorySettingsPanel() {
  const [items, setItems] = useState<Memory[]>([]);
  const [fact, setFact] = useState("");
  const [category, setCategory] = useState<MemoryCategory>("other");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const editing = useMemo(
    () => items.find((item) => item.id === editingId) || null,
    [editingId, items],
  );

  async function loadMemories() {
    setItems(await getMemories());
  }

  useEffect(() => {
    loadMemories()
      .catch((caught) =>
        setError(caught instanceof Error ? caught.message : "Unable to load memories."),
      )
      .finally(() => setLoading(false));
  }, []);

  function resetForm() {
    setEditingId(null);
    setFact("");
    setCategory("other");
  }

  function startEdit(item: Memory) {
    setEditingId(item.id);
    setFact(item.fact);
    setCategory(item.category);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!fact.trim()) return;
    setSaving(true);
    setError("");
    try {
      if (editing) await updateMemory(editing.id, { fact: fact.trim(), category });
      else await createMemory({ fact: fact.trim(), category });
      resetForm();
      await loadMemories();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save memory.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: number) {
    setError("");
    try {
      await deleteMemory(id);
      if (editingId === id) resetForm();
      await loadMemories();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to delete memory.");
    }
  }

  async function downloadExport() {
    setError("");
    try {
      const data = await exportMemories();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `financeai-memory-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to export memories.");
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold text-slate-900">Memories</h3>
          <p className="mt-1 text-sm text-slate-500">
            Review the financial facts your advisor can reuse across sessions.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void downloadExport()}
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          <Download size={17} />
          Export
        </button>
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="max-h-[30rem] space-y-3 overflow-y-auto pr-1">
          {loading && (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
              Loading memories...
            </div>
          )}
          {!loading && items.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
              No stored memory yet.
            </div>
          )}
          {!loading && items.map((item) => (
            <article key={item.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
                      {categoryLabel(item.category)}
                    </span>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">
                      {item.source === "chat" ? "From chat" : "Manual"}
                    </span>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-800">
                    {item.fact}
                  </p>
                  <p className="mt-3 text-xs text-slate-400">
                    Last used: {dateLabel(item.last_used_at)}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => startEdit(item)}
                    title="Edit memory"
                    aria-label="Edit memory"
                    className="grid size-9 place-items-center rounded-lg text-slate-600 hover:bg-slate-100"
                  >
                    <Pencil size={17} />
                  </button>
                  <button
                    type="button"
                    onClick={() => void remove(item.id)}
                    title="Delete memory"
                    aria-label="Delete memory"
                    className="grid size-9 place-items-center rounded-lg text-red-500 hover:bg-red-50"
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>

        <form
          onSubmit={(event) => void submit(event)}
          className="h-fit rounded-xl border border-slate-200 bg-white p-4"
        >
          <div className="flex items-center justify-between gap-3">
            <h4 className="text-base font-bold text-slate-900">
              {editing ? "Edit memory" : "Add memory"}
            </h4>
            {editing && (
              <button
                type="button"
                onClick={resetForm}
                title="Cancel edit"
                aria-label="Cancel editing memory"
                className="grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            )}
          </div>
          <label className="mt-4 block text-sm font-semibold text-slate-700">
            Category
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as MemoryCategory)}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            >
              {categories.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <label className="mt-4 block text-sm font-semibold text-slate-700">
            Stored fact
            <textarea
              value={fact}
              onChange={(event) => setFact(event.target.value)}
              rows={5}
              maxLength={1000}
              placeholder="Example: I have a $500 monthly car loan."
              className="mt-2 w-full resize-none rounded-xl border border-slate-200 px-3 py-3 text-sm leading-6 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </label>
          <button
            type="submit"
            disabled={saving || !fact.trim()}
            className={`mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold ${
              saving || !fact.trim()
                ? "bg-slate-200 text-slate-400"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {editing ? <Save size={18} /> : <Plus size={18} />}
            {saving ? "Saving..." : editing ? "Save" : "Add"}
          </button>
        </form>
      </div>
    </section>
  );
}
