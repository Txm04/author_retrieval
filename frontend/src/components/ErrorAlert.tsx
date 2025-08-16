/**
 * ErrorAlert.tsx — Komponente zur Anzeige von Fehlermeldungen
 *
 * Zweck
 * -----
 * - Zeigt eine hervorgehobene Box mit Fehlermeldung an
 * - Einheitliches Styling für Fehlerzustände (z. B. bei fehlgeschlagenen API-Calls)
 *
 * Props
 * -----
 * - message: string — Text der Fehlermeldung, die angezeigt wird
 *
 * Abhängigkeiten
 * - React: funktionale Komponente
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React from "react";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type Props = { message: string };

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function ErrorAlert({ message }: Props) {
  return (
    <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">
      <strong className="font-medium">Fehler:</strong> {message}
    </div>
  );
}
