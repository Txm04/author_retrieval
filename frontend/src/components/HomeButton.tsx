/**
 * HomeButton.tsx — Navigations-Button zur Startseite
 *
 * Zweck
 * -----
 * - Einheitlicher Button, der zur Startseite ("/") navigiert
 * - Enthält Icon + Label
 *
 * Abhängigkeiten
 * - react-router-dom: useNavigate für Routing
 * - lucide-react: Home-Icon
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";
import { useNavigate } from "react-router-dom";
import { Home } from "lucide-react";

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function HomeButton() {
  const navigate = useNavigate();

  /** Klick-Handler: navigiert zur Root-Route */
  const onClick = () => {
    navigate("/");
  };

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg shadow-sm transition"
    >
      <Home className="w-4 h-4" />
      Startseite
    </button>
  );
}
