import React, { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

type Topic = { id: number; title: string; abstract_count?: number };

type Props = {
  selected: number[];
  setSelected: (ids: number[]) => void;
  title?: string;
};

export default function TopicFilter({ selected, setSelected, title = "Topics" }: Props) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [open, setOpen] = useState<boolean>(() => {
    // Offen, wenn schon etwas ausgewählt ist – oder gespeicherter Zustand
    const saved = localStorage.getItem("topicFilterOpen");
    if (saved === "true" || saved === "false") return saved === "true";
    return selected.length > 0; // default
  });

  useEffect(() => {
    fetch(`${API_BASE}/topics`).then(r => r.json()).then(setTopics).catch(() => setTopics([]));
  }, []);

  useEffect(() => {
    localStorage.setItem("topicFilterOpen", String(open));
  }, [open]);

  const toggle = (id: number) => {
    setSelected(selected.includes(id) ? selected.filter(x => x !== id) : [...selected, id]);
  };

  const clear = () => setSelected([]);

  const badge = useMemo(() => (
    selected.length ? (
      <span className="ml-2 inline-flex items-center justify-center text-xs bg-blue-600 text-white rounded-full min-w-[1.25rem] h-5 px-2">
        {selected.length}
      </span>
    ) : null
  ), [selected.length]);

  return (
    <section className="bg-white shadow-soft rounded-xl">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
        className="w-full px-4 py-3 flex items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium">{title}</span>
          {badge}
        </div>
        <span className={`transition-transform ${open ? "rotate-180" : "rotate-0"}`} aria-hidden>
          ▼
        </span>
      </button>

      {/* Inhalt */}
      {open && (
        <div className="px-3 pb-3">
          <div className="flex flex-wrap gap-2">
            {topics.map(t => (
              <button
                key={t.id}
                onClick={() => toggle(t.id)}
                className={`px-3 py-1 rounded-full border text-sm transition ${
                  selected.includes(t.id)
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white hover:bg-slate-50 border-slate-300"
                }`}
                title={t.title}
              >
                {t.title}{typeof t.abstract_count === 'number' ? ` (${t.abstract_count})` : ''}
              </button>
            ))}
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
        </div>
      )}
    </section>
  );
}