import React from "react";

type Props = {
  keyword: string;
  setKeyword: (v: string) => void;
  type: "abstracts" | "authors";
  setType: (v: "abstracts" | "authors") => void;
  onSearch: () => void;
  loading?: boolean;
  pageSize: number;
  setPageSize: (value: number) => void;
};

export default function SearchBar({ keyword, setKeyword, type, setType, onSearch, loading, pageSize, setPageSize}: Props) {
  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter") onSearch();
  };

  return (
    <div className="bg-white shadow-soft rounded-xl p-4 mb-5">
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Suchbegriff eingeben…"
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />

        <select
          value={type}
          onChange={(e) => setType(e.target.value as "abstracts" | "authors")}
          className="border border-slate-300 rounded-lg px-3 py-2 bg-white"
        >
          <option value="abstracts">Abstracts</option>
          <option value="authors">Autoren</option>
        </select>

        <select
          value={pageSize}
          onChange={(e) => setPageSize(Number(e.target.value))}
          className="border border-slate-300 rounded-lg px-3 py-2"
          disabled={loading}
        >
          {[5, 10, 20, 50].map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>

        <button
          onClick={onSearch}
          disabled={loading}
          className="inline-flex items-center justify-center rounded-lg px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? "Suche…" : "Suchen"}
        </button>
      </div>
    </div>
  );
}