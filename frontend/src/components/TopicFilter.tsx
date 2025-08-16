/**
 * TopicFilter.tsx — Filterleiste für Topics (Mehrfachauswahl)
 *
 * Zweck
 * -----
 * - Lädt Topics vom Backend und erlaubt die Auswahl mehrerer Topics als Filter
 * - Zeigt Badge mit Anzahl ausgewählter Topics
 * - Merkt sich Offen/Geschlossen-Status im localStorage
 *
 * Props
 * -----
 * - selected: number[]                 — aktuell ausgewählte Topic-IDs
 * - setSelected: (ids: number[]) => void — Setter für ausgewählte IDs (kontrollierte Komponente)
 * - title?: string                     — Überschrift (Default: "Topics")
 *
 * Abhängigkeiten
 * - React
 * - Fetch API (GET /topics)
 */

import React, { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

type Topic = { id: number; title: string; abstract_count?: number };

type Props = {
  selected: number[];
  setSelected: (ids: number[]) => void;
  title?: string;
};

// Kleine Helper zum sicheren Sortieren (nach Titel)
function sortTopics(a: Topic, b: Topic) {
  return a.title.localeCompare(b.title, undefined, { sensitivity: "base" });
}

export default function TopicFilter({ selected, setSelected, title = "Topics" }: Props) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [open, setOpen] = useState<boolean>(() => {
    // Offen, wenn schon etwas ausgewählt ist – oder gespeicherter Zustand
    const saved = localStorage.getItem("topicFilterOpen");
    if (saved === "true" || saved === "false") return saved === "true";
    return selected.length > 0; // default
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Topics laden (mit AbortController gegen Race Conditions)
  useEffect(() => {
    const ctrl = new AbortController();
    const { signal } = ctrl;
    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/topics`, { signal })
      .then(async (r) => {
        if (!r.ok) {
          const txt = await r.text().catch(() => "");
          throw new Error(`HTTP ${r.status} ${txt || ""}`.trim());
        }
        return r.json();
      })
      .then((data: Topic[]) => {
        setTopics(Array.isArray(data) ? [...data].sort(sortTopics) : []);
      })
      .catch((e) => {
        if (e?.name === "AbortError") return;
        setError("Topics konnten nicht geladen werden.");
        setTopics([]);
      })
      .finally(() => setLoading(false));

    return () => ctrl.abort();
  }, []);

  // Offen/Geschlossen im localStorage persistieren
  useEffect(() => {
    localStorage.setItem("topicFilterOpen", String(open));
  }, [open]);

  // Auswahl toggeln
  const toggle = (id: number) => {
    setSelected(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  // Auswahl leeren
  const clear = () => setSelected([]);

  // Badge für die Anzahl ausgewählter Topics
  const badge = useMemo(
    () =>
      selected.length ? (
        <span
          className="ml-2 inline-flex items-center justify-center text-xs bg-blue-600 text-white rounded-full min-w-[1.25rem] h-5 px-2"
          aria-label={`${selected.length} Topics ausgewählt`}
        >
          {selected.length}
        </span>
      ) : null,
    [selected.length]
  );

  return (
    <section className="bg-white shadow-soft rounded-xl" aria-labelledby="topic-filter-title">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="topic-filter-panel"
        onClick={() => setOpen((o) => !o)}
        className="w-full px-4 py-3 flex items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2">
          <span id="topic-filter-title" className="font-medium">
            {title}
          </span>
          {badge}
        </div>
        <span className={`transition-transform ${open ? "rotate-180" : "rotate-0"}`} aria-hidden>
          ▼
        </span>
      </button>

      {/* Inhalt */}
      {open && (
        <div id="topic-filter-panel" className="px-3 pb-3">
          {error ? (
            <div className="text-sm text-red-600 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
              {error}
            </div>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {loading && (
                  <span className="text-sm text-slate-500 px-3 py-1">Lade Topics…</span>
                )}

                {!loading &&
                  topics.map((t) => {
                    const isSelected = selected.includes(t.id);
                    return (
                      <button
                        key={t.id}
                        onClick={() => toggle(t.id)}
                        className={`px-3 py-1 rounded-full border text-sm transition ${
                          isSelected
                            ? "bg-blue-600 text-white border-blue-600"
                            : "bg-white hover:bg-slate-50 border-slate-300"
                        }`}
                        title={t.title}
                        aria-pressed={isSelected}
                      >
                        {t.title}
                        {typeof t.abstract_count === "number" ? ` (${t.abstract_count})` : ""}
                      </button>
                    );
                  })}

                {!loading && !topics.length && !error && (
                  <span className="text-sm text-slate-500 px-3 py-1">Keine Topics verfügbar.</span>
                )}
              </div>

              <div className="mt-3 flex items-center gap-2">
                <button
                  type="button"
                  onClick={clear}
                  disabled={!selected.length}
                  className="text-sm text-slate-600 hover:text-slate-800 disabled:opacity-50"
                >
                  Auswahl zurücksetzen
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
