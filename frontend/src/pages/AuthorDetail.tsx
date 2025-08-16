/**
 * AuthorDetail.tsx — Detailansicht einer Autor:in
 *
 * Zweck & Inhalte
 * ---------------
 * - Lädt die Detaildaten eines Autors: Name, Anzahl & Liste der Abstracts
 * - Zeigt ähnliche Autor:innen (Vektorraum-Similarity)
 * - Bietet Navigation (Back/Home) sowie eine DangerZone zum Löschen
 * - Kapselt API-Basis, Typen, Hilfsfunktionen und Rendering klar strukturiert
 *
 * Abhängigkeiten
 * - react-router-dom: useParams, useNavigate, Link
 * - axios: HTTP-Requests (GET Detail, GET Similar, DELETE)
 * - UI-Komponenten: BackButton, HomeButton, DangerZone
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link, useNavigate, useParams } from "react-router-dom";

// UI-Komponenten
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
export type Topic = { id: number; title: string };

export type AbstractLite = {
  id: number;
  title: string;
  session_title?: string | null;
  publication_date?: string | null;
  topics?: Topic[];
};

export type AuthorDetailData = {
  id: number;
  name: string;
  abstract_count: number;
  abstracts: AbstractLite[];
};

export type SimilarItem = {
  id: number;
  name: string;
  score?: number;
};

// -----------------------------------------------------------------------------
// Hilfsfunktionen
// -----------------------------------------------------------------------------
/** Formatiert ein ISO-Datum lokal, oder liefert einen leeren String. */
function fmtDate(iso?: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return "";
  }
}

/** Extrahiert eine sinnvolle Fehlermeldung aus einer Axios-Exception. */
function parseAxiosError(err: unknown): string {
  const e = err as any;
  return (
    e?.response?.data?.detail?.message ||
    e?.response?.data?.detail ||
    e?.response?.data?.error ||
    e?.message ||
    "Fehler beim Laden."
  );
}

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function AuthorDetail() {
  // Router-Params & Navigation
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // UI-State
  const [data, setData] = useState<AuthorDetailData | null>(null);
  const [similar, setSimilar] = useState<SimilarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Memoisierte IDs/URLs für Requests
  const authorId = useMemo(() => (id ? String(id) : ""), [id]);
  const detailUrl = useMemo(() => `${API_BASE}/authors/${authorId}`, [authorId]);
  const similarUrl = useMemo(
    () => `${API_BASE}/authors/${authorId}/similar`,
    [authorId]
  );

  // Daten laden (Detail + Similar) — mit AbortController gegen Race Conditions
  useEffect(() => {
    if (!authorId) return;
    const controller = new AbortController();
    const { signal } = controller;

    async function run() {
      setLoading(true);
      setError(null);

      try {
        const [detailRes, simRes] = await Promise.all([
          axios.get(detailUrl, { signal }),
          axios.get(similarUrl, { params: { top_k: 5 }, signal }),
        ]);

        // 404/Fehlersignal kompatibel behandeln
        if (detailRes.data?.error === "not_found") {
          setData(null);
          setError("Autor nicht gefunden.");
        } else {
          setData(detailRes.data as AuthorDetailData);
          setError(null);
        }

        setSimilar((simRes.data?.results as SimilarItem[]) ?? []);
      } catch (e: any) {
        if (axios.isCancel?.(e) || e?.code === "ERR_CANCELED") return; // Request abgebrochen
        setError(parseAxiosError(e));
        setData(null);
        setSimilar([]);
      } finally {
        setLoading(false);
      }
    }

    run();
    return () => controller.abort();
  }, [authorId, detailUrl, similarUrl]);

  // Render-Pfade: Laden / Fehler / Kein Datensatz
  if (loading)
    return <div className="max-w-5xl mx-auto p-4">Laden…</div>;

  if (error)
    return (
      <div className="max-w-5xl mx-auto p-4">
        <p className="text-red-600">{error}</p>
        <Link to="/" className="text-blue-600 underline">
          Zurück zur Suche
        </Link>
      </div>
    );

  if (!data) return null;

  // JSX: Detailseite
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header-Karte */}
      <div className="bg-white rounded-xl shadow-soft p-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold leading-snug">{data.name}</h1>
          <div className="flex gap-2">
            <BackButton />
            <HomeButton />
          </div>
        </div>
        <p className="text-sm text-slate-600 mt-1">
          {data.abstract_count} Abstracts
        </p>
      </div>

      {/* Abstract-Liste */}
      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-3">Abstracts</h2>
        {data.abstracts.length ? (
          <ul className="grid gap-3">
            {data.abstracts.map((a) => {
              const topicText =
                (a.topics && a.topics.length
                  ? a.topics.map((t) => t.title).join(", ")
                  : "") || null;

              return (
                <li
                  key={a.id}
                  className="bg-white border rounded-xl p-4 hover:shadow transition"
                >
                  <Link to={`/abstracts/${a.id}`} className="block">
                    <div className="font-medium">{a.title}</div>

                    <div className="text-sm text-slate-600 mt-1">
                      {topicText && (
                        <span className="mr-2">
                          Topic: <em>{topicText}</em>
                        </span>
                      )}
                      {a.session_title && (
                        <span className="mr-2">Session: {a.session_title}</span>
                      )}
                      {a.publication_date && (
                        <span className="mr-2">{fmtDate(a.publication_date)}</span>
                      )}
                    </div>

                    {/* Optional: Chips */}
                    {a.topics?.length ? (
                      <ul className="flex flex-wrap gap-1 mt-2">
                        {a.topics.map((t) => (
                          <li
                            key={t.id}
                            className="text-xs px-2 py-0.5 rounded-full bg-slate-100"
                          >
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

      {/* Ähnliche Autor:innen */}
      <div className="bg-white rounded-xl shadow-soft p-6">
        <h2 className="font-semibold mb-3">Ähnliche Autor:innen</h2>
        {similar.length ? (
          <ul className="flex flex-wrap gap-2">
            {similar.map((s) => (
              <li key={s.id}>
                <Link
                  to={`/authors/${s.id}`}
                  title={
                    typeof (s as any).score === "number"
                      ? `Score: ${s.score !== undefined ? s.score.toFixed(3) : "-"}`
                      : undefined
                  }
                  className="inline-block px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-sm"
                >
                  {s.name}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500">Keine ähnlichen Autor:innen gefunden.</p>
        )}
      </div>

      {/* Danger Zone: Löschen */}
      <DangerZone
        label="Autor:in löschen"
        onConfirm={async () => {
          try {
            await axios.delete(`${API_BASE}/authors/${authorId}`);
            navigate("/");
          } catch (e) {
            alert(parseAxiosError(e));
          }
        }}
      />
    </div>
  );
}
