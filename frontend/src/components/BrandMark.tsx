import { Sparkles } from "lucide-react";

export default function BrandMark({ compact = false }: { compact?: boolean }) {
  const size = compact ? "size-11 rounded-2xl" : "size-14 rounded-2xl";
  return <span className={`grid shrink-0 place-items-center bg-blue-600 text-white shadow-sm shadow-blue-900/20 ${size}`}>
    <Sparkles size={compact ? 25 : 30} strokeWidth={2.2} aria-hidden="true" />
  </span>;
}
