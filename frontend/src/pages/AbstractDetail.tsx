import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import BackButton from "../components/BackButton";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

type Topic = { id: number; title: string };

type Author = { id: number; name: string };

type AbstractDetail = {
  id: number;
  title: string;
  content_raw: string;
  content?: string | null;
  submission_date?: string | null;
  publication_date?: string | null;
  language_ref?: number | null;
  word_count?: number | null;
  keywords?: string | null;
  session_id?: number | null;
  session_title?: string | null;
  authors: Author[];
  topics?: Topic[];
};

export default function AbstractDetail() {
  const { id } = useParams();
  const [data, setData] = useState<AbstractDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true); setError(null);
    axios.get(`${API_BASE}/abstracts/${id}`)
      .then(res => {
        if (!mounted) return;
        if (res.data?.error === "not_found") { setError("Abstract nicht gefunden."); setData(null); }
        else setData(res.data);
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
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="bg-white rounded-xl shadow-soft p-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold leading-snug">{data.title}</h1>
          <BackButton />
        </div>
        <div className="mt-2 text-sm text-slate-600 space-x-2">
          {data.topics?.length ? (
              <ul className="flex flex-wrap gap-2">
                {data.topics.map(t => (
                  <li key={t.id}>
                    <Link
                      to={`/?topics=${t.id}`}
                      className="inline-block px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-sm"
                    >
                      {t.title}
                    </Link>
                  </li>
                ))}
              </ul>
          ) : (
              <p className="text-slate-500">Keine Topics vorhanden.</p>
          )}
          {data.session_title && <span>Session: {data.session_title}</span>}
          {data.word_count != null && <span>· {data.word_count} Wörter</span>}
        </div>
        {data.keywords && (
          <div className="mt-2 text-sm text-slate-600">Keywords: {data.keywords}</div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-2">Inhalt</h2>
        <p className="whitespace-pre-wrap leading-relaxed">{data.content || data.content_raw}</p>
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-2">Autoren</h2>
        {data.authors?.length ? (
          <ul className="list-disc list-inside text-slate-700">
            {data.authors.map(a => (
              <li key={a.id}>
                <Link to={`/authors/${a.id}`} className="text-blue-600 underline hover:no-underline">{a.name}</Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500">Keine Autoren hinterlegt.</p>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6 text-sm text-slate-500">
        <div className="flex flex-wrap gap-4">
          {data.submission_date && <span>Submitted: {new Date(data.submission_date).toLocaleString()}</span>}
          {data.publication_date && <span>Published: {new Date(data.publication_date).toLocaleString()}</span>}
          {data.language_ref != null && <span>Language Ref: {data.language_ref}</span>}
        </div>
      </div>
    </div>
  );
}