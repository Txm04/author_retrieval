import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import BackButton from "../components/BackButton";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

type Topic = { id: number; title: string };

type AbstractLite = {
  id: number;
  title: string;
  session_title?: string | null;
  publication_date?: string | null;
  topics?: Topic[];
};


type AuthorDetail = {
  id: number;
  name: string;
  abstract_count: number;
  abstracts: AbstractLite[];
};

type SimilarItem = {
  id: number;
  name: string;
  score?: number;
};

export default function AuthorDetail() {
  const { id } = useParams();
  const [data, setData] = useState<AuthorDetail | null>(null);
  const [similar, setSimilar] = useState<SimilarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true); setError(null);

    Promise.all([
      axios.get(`${API_BASE}/authors/${id}`),
      axios.get(`${API_BASE}/authors/${id}/similar`, { params: { top_k: 5 } }),
    ])
      .then(([detailRes, simRes]) => {
        if (!mounted) return;
        if (detailRes.data?.error === "not_found") {
          setError("Autor nicht gefunden.");
          setData(null);
        } else {
          setData(detailRes.data);
        }
        setSimilar(simRes.data?.results ?? []);
      })
      .catch(() => setError("Fehler beim Laden."))
      .finally(() => mounted && setLoading(false));

    return () => { mounted = false; };
  }, [id]);

  if (loading) return <div className="max-w-5xl mx-auto p-4">Laden…</div>;
  if (error) return (
    <div className="max-w-5xl mx-auto p-4">
      <p className="text-red-600">{error}</p>
      <Link to="/" className="text-blue-600 underline">Zurück zur Suche</Link>
    </div>
  );
  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white rounded-xl shadow-soft p-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold leading-snug">{data.name}</h1>
          <BackButton />
        </div>
        <p className="text-sm text-slate-600 mt-1">{data.abstract_count} Abstracts</p>
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-3">Abstracts</h2>
        {data.abstracts.length ? (
          <ul className="grid gap-3">
              {data.abstracts.map((a) => {
                const topicText =
                  (a.topics && a.topics.length ? a.topics.map(t => t.title).join(", ") : "") || null;

                return (
                  <li key={a.id} className="bg-white border rounded-xl p-4 hover:shadow transition">
                    <Link to={`/abstracts/${a.id}`} className="block">
                      <div className="font-medium">{a.title}</div>

                      <div className="text-sm text-slate-600 mt-1">
                        {topicText && <span className="mr-2">Topic: <em>{topicText}</em></span>}
                        {a.session_title && <span className="mr-2">Session: {a.session_title}</span>}
                        {a.publication_date && (
                          <span className="mr-2">{new Date(a.publication_date).toLocaleDateString()}</span>
                        )}
                      </div>

                      {/* Optional: hübsch als Chips */}
                      {a.topics?.length ? (
                        <ul className="flex flex-wrap gap-1 mt-2">
                          {a.topics.map(t => (
                            <li key={t.id} className="text-xs px-2 py-0.5 rounded-full bg-slate-100">
                              {t.title}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
        ) : (
          <p className="text-slate-500">Keine Abstracts vorhanden.</p>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-3">Ähnliche Autor:innen</h2>
        {similar.length ? (
          <ul className="flex flex-wrap gap-2">
            {similar.map(s => (
              <li key={s.id}>
                <Link to={`/authors/${s.id}`} title={typeof (s as any).score === "number" ? `Score: ${s.score !== undefined ? s.score.toFixed(3) : "-"}
` : undefined} className="inline-block px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-sm">
                  {s.name}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500">Keine ähnlichen Autor:innen gefunden.</p>
        )}
      </div>
    </div>
  );
}