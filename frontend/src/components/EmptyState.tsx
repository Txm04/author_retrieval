/**
 * EmptyState.tsx — Anzeige für leere Such- oder Ergebnislisten
 *
 * Zweck
 * -----
 * - Zeigt eine neutrale Info-Box an, wenn keine Daten vorhanden sind
 * - Optionale Zusatzinfo (Hint) kann mitgegeben werden, um Nutzer zu leiten
 *   (z. B. "Probiere eine andere Seite oder passe die Filter an")
 *
 * Props
 * -----
 * - hint?: string — optionaler erklärender Hinweistext
 *
 * Abhängigkeiten
 * - React: funktionale Komponente
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type Props = { hint?: string };

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function EmptyState({ hint }: Props) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
      <p className="font-medium">Keine Ergebnisse</p>
      {hint && <p className="text-sm mt-1">{hint}</p>}
    </div>
  );
}
