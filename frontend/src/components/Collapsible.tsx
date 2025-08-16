/**
 * Collapsible.tsx — einklappbarer Bereich mit Titel
 *
 * Zweck
 * -----
 * - Stellt eine Container-Komponente dar, die Inhalte ein- und ausklappen kann
 * - Nutzt internen State, um Offen-/Zugeklappt-Status zu verwalten
 *
 * Props
 * -----
 * - title: Überschrift des Bereichs
 * - defaultOpen?: Standardzustand (default: true → geöffnet)
 * - children: Inhalt, der im Bereich angezeigt wird
 *
 * Abhängigkeiten
 * - React: useState für offenen Zustand
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React, { useState } from "react";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type Props = {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
};

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function Collapsible({ title, defaultOpen = true, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  /** Umschalten zwischen offen/geschlossen */
  const toggle = () => setOpen(v => !v);

  return (
    <div className="bg-white rounded-xl shadow-soft">
      {/* Header mit Titel + Pfeil */}
      <button
        type="button"
        onClick={toggle}
        className="w-full flex items-center justify-between px-6 py-4"
      >
        <h2 className="font-semibold">{title}</h2>
        <span className="text-slate-500">{open ? "▾" : "▸"}</span>
      </button>

      {/* Eingeklappter Inhalt */}
      {open && <div className="px-6 pb-6">{children}</div>}
    </div>
  );
}
