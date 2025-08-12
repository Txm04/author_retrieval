import React from "react";

export default function Loader() {
  return (
    <div className="flex items-center gap-2 text-slate-600">
      <span className="animate-spin h-5 w-5 inline-block rounded-full border-2 border-slate-300 border-t-slate-600" />
      <span>Laden…</span>
    </div>
  );
}