import React, { useEffect, useRef } from "react";

type Props = {
  open: boolean;
  title?: string;
  children?: React.ReactNode;
  onClose: () => void;
  variant?: "info" | "success" | "error";
};

export default function Modal({ open, title = "Hinweis", children, onClose, variant = "info" }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const bar =
    variant === "success" ? "bg-emerald-500" :
    variant === "error" ? "bg-red-500" : "bg-blue-500";

  return (
    <div className="fixed inset-0 z-50">
      {/* backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      {/* dialog */}
      <div className="absolute inset-0 flex items-center justify-center px-4">
        <div ref={ref} role="dialog" aria-modal="true"
             className="w-full max-w-md rounded-2xl bg-white shadow-xl overflow-hidden">
          <div className={`${bar} h-1 w-full`} />
          <div className="p-5">
            <div className="text-lg font-semibold">{title}</div>
            <div className="mt-2 text-sm text-slate-700">{children}</div>
            <div className="mt-4 text-right">
              <button
                onClick={onClose}
                className="inline-flex items-center px-3 py-1.5 rounded-lg bg-slate-800 text-white hover:bg-black"
                autoFocus
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
