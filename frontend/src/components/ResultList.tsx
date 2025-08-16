/**
 * ResultList.tsx — Ergebnisliste für Abstracts oder Autoren
 *
 * Zweck
 * -----
 * - Stellt Suchergebnisse in Kartenform dar
 * - Unterscheidung nach Typ ("abstracts" | "authors")
 * - Optional klickbare Links zu Detailseiten
 * - Anzeige von Meta-Infos (Session/Topic, Anzahl Abstracts, Score)
 *
 * Props
 * -----
 * - type: "abstracts" | "authors" — Art der Ergebnisse
 * - results: Array von AbstractResult oder AuthorResult
 * - withLinks?: boolean            — optional: macht Abstracts klickbar
 *
 * Abhängigkeiten
 * - react-router-dom: für Links
 * - TailwindCSS: Styling
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";
import { Link } from "react-router-dom";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
export type AbstractResult = {
  id: number;
  title: string;
  session_title?: string | null;
  topic_title?: string | null;
  score?: number;
};

export type AuthorResult = {
  id: number;
  name: string;
  abstract_count?: number;
  score?: number;
};

type Props = {
  type: "abstracts" | "authors";
  results: (AbstractResult | AuthorResult)[];
  withLinks?: boolean;
};

// -----------------------------------------------------------------------------
// Hilfskomponenten
// -----------------------------------------------------------------------------
/** Stellt Topic und/oder Session als Untertitel dar (mit Trenner). */
function Subtitle({ topic, session }: { topic?: string | null; session?: string | null }) {
  const parts: React.ReactNode[] = [];
  if (topic) parts.push(<em key="t">{topic}</em>);
  if (session) parts.push(<span key="s">{session}</span>);

  if (parts.length === 0) return null;              // nichts anzeigen
  if (parts.length === 1) return <>{parts[0]}</>;   // nur ein Teil → kein Trenner

  return (
    <>
      {parts[0]}{" — "}{parts[1]}
    </>
  );
}

/** Zeigt eine kleine "Pill" mit Score an, falls vorhanden. */
function ScorePill({ score }: { score?: number }) {
  if (typeof score !== "number") return null;
  return (
    <span className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-700">
      Score {score.toFixed(3)}
    </span>
  );
}

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function ResultList({ type, results, withLinks }: Props) {
  return (
    <ul className="grid gap-3">
      {results.map((item) =>
        type === "abstracts" ? (
          <li
            key={(item as AbstractResult).id}
            className="bg-white rounded-xl shadow-soft p-4 hover:shadow transition"
          >
            {withLinks ? (
              <Link to={`/abstracts/${(item as AbstractResult).id}`} className="block">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-semibold text-lg leading-snug">
                    {(item as AbstractResult).title}
                  </h3>
                  <ScorePill score={(item as AbstractResult).score} />
                </div>
                <p className="text-sm text-slate-600 mt-1">
                  <Subtitle
                    topic={(item as AbstractResult).topic_title}
                    session={(item as AbstractResult).session_title}
                  />
                </p>
              </Link>
            ) : (
              <>
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-semibold text-lg leading-snug">
                    {(item as AbstractResult).title}
                  </h3>
                  <ScorePill score={(item as AbstractResult).score} />
                </div>
                <p className="text-sm text-slate-600 mt-1">
                  <Subtitle
                    topic={(item as AbstractResult).topic_title}
                    session={(item as AbstractResult).session_title}
                  />
                </p>
              </>
            )}
          </li>
        ) : (
          <li
            key={(item as AuthorResult).id}
            className="bg-white rounded-xl shadow-soft p-4 hover:shadow transition"
          >
            <Link to={`/authors/${(item as AuthorResult).id}`} className="block">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold text-lg leading-snug">
                  {(item as AuthorResult).name}
                </h3>
                <ScorePill score={(item as AuthorResult).score} />
              </div>
              <p className="text-sm text-slate-600 mt-1">
                {typeof (item as AuthorResult).abstract_count === "number"
                  ? `${(item as AuthorResult).abstract_count} Abstracts`
                  : ""}
              </p>
            </Link>
          </li>
        )
      )}
    </ul>
  );
}
