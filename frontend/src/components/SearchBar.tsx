/**
 * SearchBar.tsx — Eingabezeile für Suche + Filter
 *
 * Zweck
 * -----
 * - Nimmt Suchbegriff entgegen, steuert Such-Typ (Abstracts/Authors)
 * - Ermöglicht Auswahl der Seitengröße und löst Suche aus
 * - Delegiert State-Änderungen über Props (kontrollierte Komponente)
 *
 * Props
 * -----
 * - keyword: string                        — aktueller Suchbegriff
 * - setKeyword: (v: string) => void        — Setter für Suchbegriff
 * - type: "abstracts" | "authors"          — aktueller Such-Typ
 * - setType: (v: "abstracts" | "authors") => void — Setter für Such-Typ
 * - onSearch: () => void                   — Callback zum Auslösen der Suche
 * - loading?: boolean                      — optional: zeigt Busy-State
 * - pageSize: number                       — aktuelle Seitengröße
 * - setPageSize: (value: number) => void   — Setter für Seitengröße
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type Props = {
  keyword: string;
  setKeyword: (v: string) => void;
  type: "abstracts" | "authors";
  setType: (v: "abstracts" | "authors") => void;
  onSearch: () => void;
  loading?: boolean;
  pageSize: number;
  setPageSize: (value: number) => void;
};

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function SearchBar({
  keyword,
  setKeyword,
  type,
  setType,
  onSearch,
  loading,
  pageSize,
  setPageSize,
}: Props) {
  // Enter-Taste im Eingabefeld startet die Suche
  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter") onSearch();
  };

  return (
    <div className="bg-white shadow-soft rounded-xl p-4 mb-5" role="search">
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Suchbegriff */}
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Suchbegriff eingeben…"
          aria-label="Suchbegriff"
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />

        {/* Such-Typ */}
        <select
          value={type}
          onChange={(e) => setType(e.target.value as "abstracts" | "authors")}
          aria-label="Suchtyp"
          className="border border-slate-300 rounded-lg px-3 py-2 bg-white"
        >
          <option value="abstracts">Abstracts</option>
          <option value="authors">Autoren</option>
        </select>

        {/* Seitengröße */}
        <select
          value={pageSize}
          onChange={(e) => setPageSize(Number(e.target.value))}
          aria-label="Ergebnisse pro Seite"
          className="border border-slate-300 rounded-lg px-3 py-2"
          disabled={loading}
        >
          {[5, 10, 20, 50].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>

        {/* Suche auslösen */}
        <button
          onClick={onSearch}
          disabled={loading}
          className="inline-flex items-center justify-center rounded-lg px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? "Suche…" : "Suchen"}
        </button>
      </div>
    </div>
  );
}
