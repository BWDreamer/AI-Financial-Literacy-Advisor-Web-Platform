import { useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";

type Props = {
  id: string;
  label: string;
  name?: string;
  value?: string;
  defaultValue?: string;
  max?: string;
  placement?: "bottom" | "top";
  onChange?: (value: string) => void;
};

const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const inputClass = "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-left text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

function todayValue() { return new Date().toISOString().slice(0, 10); }
function parts(value: string) { const [y, m, d] = value.split("-").map(Number); return { year: y || new Date().getFullYear(), month: (m || 1) - 1, day: d || 1 }; }
function iso(year: number, month: number, day: number) { return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`; }
function daysInMonth(year: number, month: number) { return new Date(year, month + 1, 0).getDate(); }
function display(value: string) { if (!value) return "Select date"; const item = parts(value); return `${item.year} ${months[item.month]} ${String(item.day).padStart(2, "0")}`; }
function clamp(value: string, max: string) { return value && value > max ? max : value; }

export default function DatePicker({ id, label, name, value, defaultValue = "", max = todayValue(), placement = "bottom", onChange }: Props) {
  const controlled = value !== undefined; const [selected, setSelected] = useState(clamp(value ?? defaultValue, max)); const [open, setOpen] = useState(false);
  const current = parts(selected || max); const maxParts = parts(max);
  const years = useMemo(() => Array.from({ length: maxParts.year - 1900 + 1 }, (_, index) => maxParts.year - index), [maxParts.year]);
  const days = Array.from({ length: daysInMonth(current.year, current.month) }, (_, index) => index + 1);
  const popupPosition = placement === "top" ? "bottom-full mb-0" : "mt-2";
  useEffect(() => { if (controlled) setSelected(clamp(value || "", max)); }, [controlled, max, value]);
  function update(year = current.year, month = current.month, day = current.day) {
    const next = iso(year, month, Math.min(day, daysInMonth(year, month)));
    if (next <= max) { if (!controlled) setSelected(next); onChange?.(next); }
  }
  return <label className="relative block" htmlFor={id}><span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>{name && <input type="hidden" name={name} value={selected} />}<button id={id} type="button" onClick={() => setOpen(!open)} className={`${inputClass} flex items-center justify-between`}><span>{display(selected)}</span><ChevronDown size={16} /></button>{open && <div className={`absolute z-50 grid w-full min-w-72 grid-cols-3 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl ${popupPosition}`}><div className="max-h-40 overflow-y-auto border-r border-slate-100 p-1.5">{years.map((year) => <button key={year} type="button" onClick={() => update(year)} className={`mb-0.5 w-full rounded-lg px-2 py-1.5 text-sm font-semibold ${year === current.year ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-50"}`}>{year}</button>)}</div><div className="max-h-40 overflow-y-auto border-r border-slate-100 p-1.5">{months.map((month, index) => <button key={month} type="button" disabled={current.year === maxParts.year && index > maxParts.month} onClick={() => update(current.year, index)} className={`mb-0.5 w-full rounded-lg px-2 py-1.5 text-sm font-semibold ${index === current.month ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"} disabled:text-slate-300`}>{month}</button>)}</div><div className="max-h-40 overflow-y-auto p-1.5">{days.map((day) => <button key={day} type="button" disabled={iso(current.year, current.month, day) > max} onClick={() => { update(current.year, current.month, day); setOpen(false); }} className={`mb-0.5 w-full rounded-lg px-2 py-1.5 text-sm font-semibold ${day === current.day ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"} disabled:text-slate-300`}>{day}</button>)}</div></div>}</label>;
}
