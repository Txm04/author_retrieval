/**
 * Modal.tsx — Einfacher modaler Dialog mit Overlay
 *
 * Zweck
 * -----
 * - Zeigt ein modales Dialogfenster mit Titel, Inhalt und Schließen-Button
 * - Unterstützt Varianten ("info" | "success" | "error") über Farbmarkierung
 * - Schließt bei ESC-Taste und Klick auf den Hintergrund (Backdrop)
 *
 * Props
 * -----
 * - open: boolean            — steuert Sichtbarkeit
 * - title?: string           — Überschrift (Default: "Hinweis")
 * - children?: ReactNode     — Dialoginhalt
 * - onClose: () => void      — Schließen-Handler
 * - variant?: "info" | "success" | "error" (Default: "info")
 *
 * A11y
 * ----
 * - role="dialog", aria-modal="true"
 * - Tastatur: ESC schließt
 * - Optionales Scroll-Locking bei geöffnetem Dialog
 */

import React, { useEffect, useMemo, useRef } from "react";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type Variant = "info" | "success" | "error";

type Props = {
  open: boolean;
  title?: string;
  children?: React.ReactNode;
  onClose: () => void;
  variant?: Variant;
};

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function Modal({
  open,
  title = "Hinweis",
  children,
  onClose,
  variant = "info",
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = "modal-title";

  // ESC zum Schließen
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Optional: Scroll-Lock für Body, solange das Modal offen ist
  useEffect(() => {
    if (!open) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [open]);

  // Farbbalken nach Variante
  const barClass = useMemo(() => {
    switch (variant) {
      case "success":
        return "bg-emerald-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-blue-500";
    }
  }, [variant]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="absolute inset-0 flex items-center justify-center px-4">
        <div
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className="w-full max-w-md rounded-2xl bg-white shadow-xl overflow-hidden"
          // Klicks im Dialog sollen NICHT das Modal schließen
          onClick={(e) => e.stopPropagation()}
        >
          <div className={`${barClass} h-1 w-full`} />
          <div className="p-5">
            <div id={titleId} className="text-lg font-semibold">
              {title}
            </div>
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
