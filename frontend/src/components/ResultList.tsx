// src/components/ResultList.tsx
import React from "react";
import { Link } from "react-router-dom";

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

function Subtitle({ topic, session }: { topic?: string | null; session?: string | null }) {
  const parts: React.ReactNode[] = [];
  if (topic) parts.push(<em key="t">{topic}</em>);
  if (session) parts.push(<span key="s">{session}</span>);

  if (parts.length === 0) return null;              // nichts anzeigen
  if (parts.length === 1) return <>{parts[0]}</>;   // kein Trenner

  // genau ein Trenner zwischen den Teilen
  return (
    <>
      {parts[0]}{" — "}{parts[1]}
    </>
  );
}

function ScorePill({ score }: { score?: number }) {
  if (typeof score !== "number") return null;
  return (
    <span className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-700">
      Score {score.toFixed(3)}
    </span>
  );
}

export default function ResultList({ type, results, withLinks }: Props) {
  return (
    <ul className="grid gap-3">
      {results.map((item) =>
        type === "abstracts" ? (
          <li key={(item as AbstractResult).id} className="bg-white rounded-xl shadow-soft p-4 hover:shadow transition">
            {withLinks ? (
              <Link to={`/abstracts/${(item as AbstractResult).id}`} className="block">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-semibold text-lg leading-snug">{(item as AbstractResult).title}</h3>
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
                  <h3 className="font-semibold text-lg leading-snug">{(item as AbstractResult).title}</h3>
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
          <li key={(item as AuthorResult).id} className="bg-white rounded-xl shadow-soft p-4 hover:shadow transition">
            <Link to={`/authors/${(item as AuthorResult).id}`} className="block">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold text-lg leading-snug">{(item as AuthorResult).name}</h3>
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
