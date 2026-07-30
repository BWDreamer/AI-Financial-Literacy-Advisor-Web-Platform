import { ReactNode, useEffect } from "react";
import { X } from "lucide-react";

type ModalProps = {
  children: ReactNode;
  onClose: () => void;
  title: string;
  wide?: boolean;
  hideHeader?: boolean;
  variant?: "default" | "glass";
};

export default function Modal({
  children,
  onClose,
  title,
  wide = false,
  hideHeader = false,
  variant = "default",
}: ModalProps) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  const isGlass = variant === "glass";

  return (
    <div
      className={`fixed inset-0 z-50 grid place-items-center ${isGlass ? "bg-slate-950/45 backdrop-blur-sm" : "bg-slate-950/55"} ${hideHeader ? "p-2" : "p-6"}`}
      onMouseDown={onClose}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onMouseDown={(event) => event.stopPropagation()}
        className={`w-full rounded-3xl shadow-2xl ${wide ? "max-w-6xl" : "max-w-lg"} ${hideHeader ? "max-h-[96vh] overflow-y-auto" : "max-h-[90vh] overflow-y-auto"} ${
          isGlass
            ? "border border-white/25 bg-white/12 text-white backdrop-blur-2xl"
            : "border border-slate-200 bg-white"
        }`}
      >
        {!hideHeader && <header className={`sticky top-0 flex items-center justify-between px-6 py-5 ${isGlass ? "border-b border-white/15 bg-slate-950/10 backdrop-blur" : "border-b border-slate-200 bg-white"}`}>
          <h2 id="modal-title" className="text-xl font-bold tracking-tight">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close modal" className={`rounded-lg p-2 transition ${isGlass ? "text-white/70 hover:bg-white/10 hover:text-white" : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"}`}><X size={20} /></button>
        </header>}
        <div id="modal-title" className={hideHeader ? "px-5 pb-6 pt-3 sm:px-6" : "p-6"}>{children}</div>
      </section>
    </div>
  );
}
