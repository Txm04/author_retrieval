import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { BrowserRouter, Routes, Route, Link, useSearchParams } from "react-router-dom";
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


const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

type Kind = "abstracts" | "authors";

function SearchPage() {
  const [keyword, setKeyword] = useState("");
  const [kind, setKind] = useState<Kind>("abstracts");
  const [results, setResults] = useState<(AbstractResult | AuthorResult)[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requested, setRequested] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  useEffect(() => { setPage(1); }, [keyword, kind]);

  const [searchParams, setSearchParams] = useSearchParams();
  const [topicIds, setTopicIds] = useState<number[]>(() => {
    const fromUrl = searchParams.get("topics");
    if (fromUrl) {
      return fromUrl
        .split(",")
        .map(s => s.trim())
        .filter(Boolean)
        .map(Number)
        .filter(n => Number.isFinite(n));
    }
    try { return JSON.parse(localStorage.getItem("topicIds") || "[]"); } catch { return []; }
  });
  useEffect(() => {
    // persistieren
    localStorage.setItem("topicIds", JSON.stringify(topicIds));
    // URL aktualisieren (nett für Shareable Links)
    const next = new URLSearchParams(searchParams);
    if (topicIds.length) next.set("topics", topicIds.join(","));
    else next.delete("topics");
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicIds]);

  useEffect(() => { setPage(1); }, [topicIds]);

  const disabled = useMemo(() => {
    if (kind === "abstracts") {
      // erlaubt: entweder keyword ODER Topics gesetzt
      return !keyword.trim() && topicIds.length === 0;
    }
    // bei Authors weiterhin Keyword nötig (falls du das so willst)
    return !keyword.trim();
  }, [keyword, topicIds, kind]);

  const search = useCallback(async () => {
    // disabled-Logik wie zuvor (leere Suche bei Abstracts mit Topics erlauben etc.)
    setRequested(true); setLoading(true); setError(null);
    try {
      const url = `${API_BASE}/${kind}/search`;
      const params: any = {
        keyword: keyword.trim(),
        page,
        page_size: pageSize,
      };
      // nur für Abstracts: Topic-Filter mitsenden
      if (kind === "abstracts" && topicIds?.length) {
        params.topic_ids = topicIds.join(",");
      }
      const res = await axios.get(url, { params });
      setResults(res.data?.results ?? []);
    } catch (e: any) {
      setError(e?.response?.data?.error || "Fehler beim Abrufen der Daten.");
      setResults([]);
    } finally { setLoading(false); }
  }, [kind, keyword, page, pageSize, topicIds]);

  // Suche auslösen, wenn page oder pageSize sich ändern
  useEffect(() => {
    if (requested) search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize]);

  useEffect(() => {
  if (requested) search();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [topicIds, kind]);

  return (
  <Layout>
    <div className="space-y-4">
      {/* ⬇️ SearchBar wieder anzeigen */}
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

      {/* Topic-Filter nur bei Abstracts */}
      {kind === "abstracts" && (
        <TopicFilter selected={topicIds} setSelected={setTopicIds} />
      )}

      {error && <ErrorAlert message={error} />}
      {loading && (<div className="bg-white rounded-xl shadow-soft p-4"><Loader /></div>)}

      {!loading && requested && results.length === 0 ? (
        <EmptyState hint="Keine Treffer für die aktuelle Seite/Filter. Probiere eine andere Seite oder passe die Filter an." />
      ) : null}

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