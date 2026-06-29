import { ReactNode, useEffect } from "react";
import { X } from "lucide-react";

type ModalProps = {
  children: ReactNode;
  onClose: () => void;
  title: string;
  wide?: boolean;
};

export default function Modal({ children, onClose, title, wide = false }: ModalProps) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-6" onMouseDown={onClose}>
      <section role="dialog" aria-modal="true" aria-labelledby="modal-title" onMouseDown={(event) => event.stopPropagation()} className={`max-h-[90vh] w-full overflow-y-auto rounded-3xl border border-slate-200 bg-white shadow-2xl ${wide ? "max-w-3xl" : "max-w-lg"}`}>
        <header className="sticky top-0 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
          <h2 id="modal-title" className="text-xl font-bold tracking-tight">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close modal" className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"><X size={20} /></button>
        </header>
        <div className="p-6">{children}</div>
      </section>
    </div>
  );
}
