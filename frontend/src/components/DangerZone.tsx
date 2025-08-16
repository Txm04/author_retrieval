/**
 * DangerZone.tsx — kritischer Aktionsbereich (z. B. "Löschen")
 *
 * Zweck
 * -----
 * - Stellt einen auffälligen, rot markierten Bereich dar für irreversible Aktionen
 * - Bietet Sicherheitsmechanismus: Nutzer muss "DELETE" eingeben, um Aktion freizugeben
 * - Führt eine asynchrone `onConfirm`-Funktion aus, sobald bestätigt
 *
 * Props
 * -----
 * - label: Beschriftung der Aktion (z. B. "Abstract löschen", "Autor:in löschen")
 * - onConfirm: Async-Funktion, die nach Bestätigung ausgeführt wird
 *
 * Abhängigkeiten
 * - React: useState für Eingabetext, Busy-State, Fehlermeldungen
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React, { useState } from "react";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
type DangerZoneProps = {
  label: string;
  onConfirm: () => Promise<void>;
};

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function DangerZone({ label, onConfirm }: DangerZoneProps) {
  const [confirmText, setConfirmText] = useState("");   // Eingabefeld für "DELETE"
  const [busy, setBusy] = useState(false);              // Busy-Status während Request
  const [msg, setMsg] = useState<string | null>(null);  // Fehlermeldung / Feedback

  const canDelete = confirmText === "DELETE";

  /** Führt den Löschvorgang aus, wenn bestätigt */
  const fire = async () => {
    if (!canDelete) return;
    setBusy(true);
    setMsg(null);
    try {
      await onConfirm();
    } catch {
      setMsg("Löschen fehlgeschlagen. Bitte erneut versuchen.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-soft p-6 space-y-3 border border-red-200">
      <h2 className="font-semibold text-red-700">Danger Zone</h2>
      <p className="text-sm text-slate-600">
        Vorgang ist dauerhaft. Zum Bestätigen <code>DELETE</code> eingeben.
      </p>

      {/* Eingabefeld + Button */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          placeholder='Zum Bestätigen "DELETE" eingeben'
          disabled={busy}
          className="border border-slate-300 rounded-lg px-3 py-2 bg-white w-64"
        />
        <button
          onClick={fire}
          disabled={!canDelete || busy}
          className="px-3 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
        >
          {busy ? "Lösche…" : label}
        </button>
      </div>

      {/* Fehlermeldung */}
      {msg && <div className="text-sm text-red-700">{msg}</div>}
    </div>
  );
}
