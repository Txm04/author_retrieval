import React from "react";

type Props = { hint?: string };

export default function EmptyState({ hint }: Props) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
      <p className="font-medium">Keine Ergebnisse</p>
      {hint && <p className="text-sm mt-1">{hint}</p>}
    </div>
  );
}