/**
 * Pagination.tsx — Paginierungskomponente
 *
 * Zweck
 * -----
 * - Bietet einfache Vor-/Zurück-Steuerung für Seitennavigation
 * - Zeigt aktuelle Seite und Page-Size an
 *
 * Props
 * -----
 * - page: number                   — aktuelle Seite (1-basiert)
 * - pageSize: number               — Anzahl der Elemente pro Seite (Anzeige)
 * - setPage: (n: number) => void   — Callback zum Setzen der neuen Seite
 * - disablePrev?: boolean          — optional: Vorherige-Seite-Button deaktivieren
 * - disableNext?: boolean          — optional: Nächste-Seite-Button deaktivieren
 *
 * Abhängigkeiten
 * - React: funktionale Komponente
 * - TailwindCSS: Styling
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type Props = {
  page: number;
  pageSize: number;
  setPage: (n: number) => void;
  disablePrev?: boolean;
  disableNext?: boolean;
};

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function Pagination({
  page,
  pageSize,
  setPage,
  disablePrev,
  disableNext,
}: Props) {
  return (
    <div className="flex items-center justify-between gap-3">
      {/* Statusanzeige */}
      <div className="text-sm text-slate-600">
        Seite <span className="font-medium">{page}</span> · {pageSize} pro Seite
      </div>

      {/* Buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page === 1 || disablePrev}
          className="px-3 py-1.5 rounded-lg border bg-white hover:bg-slate-50 disabled:opacity-50"
        >
          Zurück
        </button>
        <button
          onClick={() => setPage(page + 1)}
          disabled={disableNext}
          className="px-3 py-1.5 rounded-lg border bg-white hover:bg-slate-50 disabled:opacity-50"
        >
          Weiter
        </button>
      </div>
    </div>
  );
}
