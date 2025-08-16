/**
 * AbstractDetail.tsx — Detailansicht eines Abstracts
 *
 * Zweck & Inhalte
 * ---------------
 * - Lädt ein Abstract anhand der ID aus der URL (/abstracts/:id)
 * - Zeigt Titel, Topics, Session, Keywords, Inhalt, Autoren und Meta-Infos an
 * - Ermöglicht das Löschen des Abstracts über eine DangerZone
 * - Nutzt axios für API-Calls, react-router für Navigation
 *
 * Abhängigkeiten
 * - axios: HTTP Requests
 * - react-router-dom: useParams, useNavigate, Link
 * - UI: BackButton, HomeButton, DangerZone
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

import BackButton from "../components/BackButton";
import HomeButton from "../components/HomeButton";
import DangerZone from "../components/DangerZone";

// -----------------------------------------------------------------------------
// Konstanten
// -----------------------------------------------------------------------------
const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type Topic = { id: number; title: string };
type Author = { id: number; name: string };

export type AbstractDetailData = {
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

// -----------------------------------------------------------------------------
// Hilfsfunktionen
// -----------------------------------------------------------------------------
/** Formatiert ein Datum (ISO-String) in lesbares Datum/Zeit. */
function fmtDateTime(value?: string | null): string | null {
  return value ? new Date(value).toLocaleString() : null;
}

/** Fehlertext aus einer Axios-Exception extrahieren. */
function parseAxiosError(err: unknown): string {
  const e = err as any;
  return (
    e?.response?.data?.detail?.message ||
    e?.response?.data?.detail ||
    e?.response?.data?.error ||
    e?.message ||
    "Unbekannter Fehler."
  );
}

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function AbstractDetail() {
  // --- Hooks & State
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<AbstractDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- Abstract laden
  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);

    axios
      .get(`${API_BASE}/abstracts/${id}`, { signal: ctrl.signal })
      .then((res) => {
        if (res.data?.error === "not_found") {
          setError("Abstract nicht gefunden.");
          setData(null);
        } else {
          setData(res.data);
        }
      })
      .catch((err) => {
        if (axios.isCancel(err)) return;
        setError(parseAxiosError(err));
      })
      .finally(() => setLoading(false));

    return () => ctrl.abort();
  }, [id]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (loading) {
    return <div className="max-w-5xl mx-auto p-4">Laden…</div>;
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto p-4">
        <p className="text-red-600">{error}</p>
        <Link to="/" className="text-blue-600 underline">
          Zurück zur Suche
        </Link>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Kopfbereich mit Titel und Buttons */}
      <div className="bg-white rounded-xl shadow-soft p-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold leading-snug">{data.title}</h1>
          <div className="flex gap-2">
            <BackButton />
            <HomeButton />
          </div>
        </div>

        {/* Topics, Session, Wordcount */}
        <div className="mt-2 text-sm text-slate-600 space-x-2">
          {data.topics?.length ? (
            <ul className="flex flex-wrap gap-2">
              {data.topics.map((t) => (
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

        {/* Keywords */}
        {data.keywords && (
          <div className="mt-2 text-sm text-slate-600">Keywords: {data.keywords}</div>
        )}
      </div>

      {/* Inhalt */}
      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-2">Inhalt</h2>
        <p className="whitespace-pre-wrap leading-relaxed">
          {data.content || data.content_raw}
        </p>
      </div>

      {/* Autoren */}
      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-2">Autoren</h2>
        {data.authors?.length ? (
          <ul className="list-disc list-inside text-slate-700">
            {data.authors.map((a) => (
              <li key={a.id}>
                <Link
                  to={`/authors/${a.id}`}
                  className="text-blue-600 underline hover:no-underline"
                >
                  {a.name}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500">Keine Autoren hinterlegt.</p>
        )}
      </div>

      {/* Metadaten */}
      <div className="bg-white rounded-xl shadow-soft p-6 text-sm text-slate-500">
        <div className="flex flex-wrap gap-4">
          {data.submission_date && <span>Submitted: {fmtDateTime(data.submission_date)}</span>}
          {data.publication_date && <span>Published: {fmtDateTime(data.publication_date)}</span>}
          {data.language_ref != null && <span>Language Ref: {data.language_ref}</span>}
        </div>
      </div>

      {/* DangerZone: Löschen */}
      <DangerZone
        label="Abstract löschen"
        onConfirm={async () => {
          await axios.delete(`${API_BASE}/abstracts/${id}`);
          navigate("/");
        }}
      />
    </div>
  );
}
