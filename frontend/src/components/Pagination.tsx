import React from "react";

type Props = {
  page: number;
  pageSize: number;
  setPage: (n: number) => void;
  disablePrev?: boolean;
  disableNext?: boolean;
};

export default function Pagination({
  page, pageSize, setPage, disablePrev, disableNext
}: Props) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="text-sm text-slate-600">
        Seite <span className="font-medium">{page}</span> · {pageSize} pro Seite
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page === 1 || disablePrev}
          className="px-3 py-1.5 rounded-lg border bg-white hover:bg-slate-50 disabled:opacity-50"
        >
          Zurück
        </button>
        <button
          onClick={() => setPage(page + 1)}
          disabled={disableNext}
          className="px-3 py-1.5 rounded-lg border bg-white hover:bg-slate-50 disabled:opacity-50"
        >
          Weiter
        </button>
      </div>
    </div>
  );
}
