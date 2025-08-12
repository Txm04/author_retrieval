import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function BackButton({ fallback = "/" }: { fallback?: string }) {
  const navigate = useNavigate();
  const onClick = () => {
    // versuche history -1, fallback auf eine Route (z.B. Startseite)
    if (window.history.length > 1) navigate(-1);
    else navigate(fallback);
  };
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg shadow-sm transition"
    >
      <ArrowLeft className="w-4 h-4" />
      Zurück
    </button>
  );
}
