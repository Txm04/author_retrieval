/**
 * Loader.tsx — Lade-Indikator
 *
 * Zweck
 * -----
 * - Zeigt eine kleine Spinner-Animation mit Text "Laden…" an
 * - Einheitliches Styling für Ladezustände
 *
 * Abhängigkeiten
 * - React: funktionale Komponente
 * - TailwindCSS: Animation & Layout
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function Loader() {
  return (
    <div className="flex items-center gap-2 text-slate-600">
      {/* Spinner */}
      <span className="animate-spin h-5 w-5 inline-block rounded-full border-2 border-slate-300 border-t-slate-600" />
      {/* Text */}
      <span>Laden…</span>
    </div>
  );
}
