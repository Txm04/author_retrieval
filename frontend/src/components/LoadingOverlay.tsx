/**
 * LoadingOverlay.tsx — Vollbild-Ladeanzeige
 *
 * Zweck
 * -----
 * - Überlagert die gesamte Seite mit einem halbtransparenten Overlay
 * - Zeigt zentrierten Spinner + Text ("Bitte warten…")
 * - Wird für Busy-States oder lange API-Operationen genutzt
 *
 * Props
 * -----
 * - text?: string — anzeigbarer Ladehinweis (Default: "Bitte warten…")
 *
 * Abhängigkeiten
 * - React: funktionale Komponente
 * - TailwindCSS: Styling & Animation
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function LoadingOverlay({ text = "Bitte warten…" }: { text?: string }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-white/60 backdrop-blur-sm"
      role="alert"
      aria-live="assertive"
      aria-busy="true"
    >
      <div className="flex flex-col items-center gap-3">
        {/* Spinner */}
        <svg
          className="animate-spin h-8 w-8"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
          />
        </svg>
        {/* Lade-Text */}
        <div className="text-sm text-slate-700">{text}</div>
      </div>
    </div>
  );
}
