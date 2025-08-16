/**
App.tsx — Haupteinstiegspunkt der React-Frontend-Anwendung

Struktur & Ziele
----------------
- Definiert die Haupt-Routing-Logik (BrowserRouter + Routes)
- Stellt die `SearchPage` als zentrale Such- und Filterseite bereit
- Enthält Subseiten: AbstractDetail, AuthorDetail, Admin
- Nutzt zentrale Komponenten (SearchBar, ResultList, TopicFilter, Pagination)
- API-Basis-URL aus ENV konfigurierbar
**/
import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { BrowserRouter, Routes, Route, useSearchParams } from "react-router-dom";
import Layout from "./components/Layout";
import SearchBar from "./components/SearchBar";
import ResultList, { AbstractResult, AuthorResult } from "./components/ResultList";
import Loader from "./components/Loader";
import ErrorAlert from "./components/ErrorAlert";
import EmptyState from "./components/EmptyState";
import AbstractDetail from "./pages/AbstractDetail";
import AuthorDetail from "./pages/AuthorDetail";
import Admin from "./pages/Admin";
import TopicFilter from "./components/TopicFilter";
import Pagination from "./components/Pagination";

// -----------------------------------------------------------------------------
// Konstanten
// -----------------------------------------------------------------------------
const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
const DEFAULT_PAGE_SIZE = 10;

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
/** Art der Suche/Ergebnisliste */
type Kind = "abstracts" | "authors";

/** Vereinigung möglicher Ergebnis-Items */
type SearchResult = AbstractResult | AuthorResult;

// -----------------------------------------------------------------------------
// Hilfsfunktionen
// -----------------------------------------------------------------------------
/**
 * Liest Topic-IDs zunächst aus der URL (z. B. ?topics=1,2,3) und fällt dann auf
 * localStorage zurück. Ungültige Werte werden gefiltert.
 */
function getInitialTopicIds(sp: URLSearchParams): number[] {
  const fromUrl = sp.get("topics");
  if (fromUrl) {
    return fromUrl
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number)
      .filter((n) => Number.isFinite(n));
  }
  try {
    return JSON.parse(localStorage.getItem("topicIds") || "[]");
  } catch {
    return [];
  }
}

/** Liefert eine nutzerfreundliche Fehlermeldung aus einer Axios-Exception. */
function parseAxiosError(err: unknown): string {
  const e = err as any;
  return (
    e?.response?.data?.detail?.message ||
    e?.response?.data?.detail ||
    e?.response?.data?.error ||
    e?.message ||
    "Fehler beim Abrufen der Daten."
  );
}

// -----------------------------------------------------------------------------
// SearchPage – Hauptseite mit Suchformular, Filter, Resultaten
// -----------------------------------------------------------------------------
function SearchPage() {
  // --- Router-/URL-State
  const [searchParams, setSearchParams] = useSearchParams();

  // --- UI-State
  const [keyword, setKeyword] = useState("");
  const [kind, setKind] = useState<Kind>("abstracts");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requested, setRequested] = useState(false); // wurde schon mindestens einmal gesucht?

  // --- Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  // Bei Wechsel von Keyword/Kind/Topics: zur ersten Seite springen
  useEffect(() => setPage(1), [keyword, kind]);

  // --- Topic-Filter (nur für Abstracts relevant)
  const [topicIds, setTopicIds] = useState<number[]>(() => getInitialTopicIds(searchParams));

  // Persistiere Topic-IDs & synchronisiere URL (für sharebare Links)
  useEffect(() => {
    localStorage.setItem("topicIds", JSON.stringify(topicIds));
    const next = new URLSearchParams(searchParams);
    if (topicIds.length) next.set("topics", topicIds.join(","));
    else next.delete("topics");
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicIds]);

  // Bei Änderung der Topics: Seite zurücksetzen
  useEffect(() => setPage(1), [topicIds]);

  // Ist der Suchen-Button deaktiviert?
  const disabled = useMemo(() => {
    if (kind === "abstracts") {
      // erlaubt: entweder keyword ODER Topics gesetzt
      return !keyword.trim() && topicIds.length === 0;
    }
    // bei Authors weiterhin Keyword nötig
    return !keyword.trim();
  }, [keyword, topicIds, kind]);

  /** Führt die Suche aus (ruft das API) und aktualisiert Resultate/Fehler/Loader. */
  const search = useCallback(async () => {
    setRequested(true);
    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/${kind}/search`;
      const params: Record<string, any> = {
        keyword: keyword.trim(),
        page,
        page_size: pageSize,
      };
      if (kind === "abstracts" && topicIds?.length) {
        params.topic_ids = topicIds.join(",");
      }

      const res = await axios.get(url, { params });
      setResults(res.data?.results ?? []);
    } catch (e) {
      setError(parseAxiosError(e));
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [kind, keyword, page, pageSize, topicIds]);

  // Suche auslösen, wenn page oder pageSize sich ändern (aber nur wenn zuvor gesucht wurde)
  useEffect(() => {
    if (requested) search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize]);

  // Suche neu auslösen, wenn Topics oder Kind wechseln (falls bereits gesucht)
  useEffect(() => {
    if (requested) search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicIds, kind]);

  return (
    <Layout>
      <div className="space-y-4">
        {/* Suchleiste */}
        <SearchBar
          keyword={keyword}
          setKeyword={setKeyword}
          type={kind}
          setType={setKind}
          onSearch={search}
          loading={loading}
          pageSize={pageSize}
          setPageSize={setPageSize}
        />

        {/* Topic-Filter nur bei Abstracts sichtbar */}
        {kind === "abstracts" && (
          <TopicFilter selected={topicIds} setSelected={setTopicIds} />
        )}

        {/* Fehler- und Ladezustände */}
        {error && <ErrorAlert message={error} />}
        {loading && (
          <div className="bg-white rounded-xl shadow-soft p-4">
            <Loader />
          </div>
        )}

        {/* Leerer Zustand nach einer Suche ohne Treffer */}
        {!loading && requested && results.length === 0 ? (
          <EmptyState hint="Keine Treffer für die aktuelle Seite/Filter. Probiere eine andere Seite oder passe die Filter an." />
        ) : null}

        {/* Ergebnisliste + Pagination */}
        {!loading && results.length > 0 && (
          <>
            <ResultList type={kind} results={results} withLinks />
            <Pagination
              page={page}
              pageSize={pageSize}
              setPage={setPage}
              disableNext={results.length < pageSize}
            />
          </>
        )}
      </div>
    </Layout>
  );
}

// -----------------------------------------------------------------------------
// App – Router-Setup
// -----------------------------------------------------------------------------
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/abstracts/:id" element={<AbstractDetail />} />
        <Route path="/authors/:id" element={<AuthorDetail />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </BrowserRouter>
  );
}
