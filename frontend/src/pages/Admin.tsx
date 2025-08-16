/**
 * Admin.tsx — Administrationsoberfläche für Modell-/Index-/Konfig-Aufgaben
 *
 * Zweck & Inhalte
 * ---------------
 * - Zeigt Systemstatus (Modell, Datenbank-Zähler, FAISS-Indizes, Config, Logger)
 * - Erlaubt Laufzeit-Konfiguration: Device wechseln, Score-Flags, Log-Level
 * - Rebuild der Indizes (FAISS), Datenbank-Reset, JSON-Import
 * - Nutzt modale Hinweise/Overlays für Busy/Feedback
 *
 * Abhängigkeiten
 * - axios: HTTP-Requests
 * - react-router-dom: Navigation (Back/Home-Buttons sind eigene Komponenten)
 * - UI: BackButton, HomeButton, LoadingOverlay, Modal, Collapsible
 */

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

// UI-Komponenten
import BackButton from "../components/BackButton";
import HomeButton from "../components/HomeButton";
import LoadingOverlay from "../components/LoadingOverlay";
import Modal from "../components/Modal";
import Collapsible from "../components/Collapsible";

// -----------------------------------------------------------------------------
// Konstanten
// -----------------------------------------------------------------------------
const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

// -----------------------------------------------------------------------------
// Typen
// -----------------------------------------------------------------------------
export type Status = {
  model: {
    name: string;
    device: "cpu" | "cuda" | "mps";
    available: { cpu: boolean; cuda: boolean; mps: boolean };
  };
  counts: { abstracts: number; authors: number };
  indices: { abstracts: number; authors: number };
  config: { show_scores: boolean; score_mode: "cosine" | "faiss" };
  logger?: { level: string };
};

// -----------------------------------------------------------------------------
// Hilfsfunktionen
// -----------------------------------------------------------------------------
/** Liefert eine nutzerfreundliche Fehlermeldung aus einer Axios-Exception. */
function parseAxiosError(err: unknown): string {
  const e = err as any;
  return (
    e?.response?.data?.detail?.message ||
    e?.response?.data?.detail ||
    e?.response?.data?.error ||
    e?.message ||
    "Unbekannter Fehler."
  );
}

/** Extrahiert Index-Zähler aus /admin/reindex Response (abwärtskompatibel). */
function getIndexCounts(data: any): { abstracts: number; authors: number } {
  const indices = data?.indices;
  if (indices) return { abstracts: indices.abstracts, authors: indices.authors };
  // Legacy-Fallback
  return { abstracts: data?.abstracts ?? 0, authors: data?.authors ?? 0 };
}

// -----------------------------------------------------------------------------
// Komponente
// -----------------------------------------------------------------------------
export default function Admin() {
  // --- Status- & UI-State
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageVariant, setMessageVariant] = useState<"info" | "success" | "error">("info");
  const [fileName, setFileName] = useState<string>("");
  const [confirmText, setConfirmText] = useState<string>("");

  // --- Konfiguration (vom Server gelesen → lokal bearbeitet)
  const [device, setDevice] = useState<"cpu" | "cuda" | "mps">("cpu");
  const [showScores, setShowScores] = useState(false);
  const [scoreMode, setScoreMode] = useState<"cosine" | "faiss">("cosine");
  const [logLevel, setLogLevel] = useState<string>("INFO");

  // --- abgeleitete Werte
  const available = status?.model.available || { cpu: true, cuda: false, mps: false };
  const currentDevice = status?.model.device;

  /** Kann die Device-Config gespeichert werden? */
  const canSaveDevice = useMemo(() => {
    if (!status) return false;
    if (device === currentDevice) return false;
    if (device === "cuda" && !available.cuda) return false;
    if (device === "mps" && !available.mps) return false;
    return true;
  }, [status, device, currentDevice, available]);

  /** Haben sich Score-Optionen gegenüber dem Serverzustand geändert? */
  const canSaveScores = useMemo(() => {
    const cfg = status?.config;
    if (!cfg) return true; // erlauben, falls Server noch nichts geliefert hat
    return showScores !== cfg.show_scores || scoreMode !== cfg.score_mode;
  }, [status, showScores, scoreMode]);

  // ---------------------------------------------------------------------------
  // Daten laden
  // ---------------------------------------------------------------------------
  const load = async () => {
    const res = await axios.get<Status>(`${API_BASE}/admin/status`);
    setStatus(res.data);

    // lokale States mit Serverzustand initialisieren
    if (res.data?.model?.device) setDevice(res.data.model.device);
    if (res.data?.config) {
      setShowScores(res.data.config.show_scores);
      setScoreMode(res.data.config.score_mode);
    }
    if (res.data?.logger?.level) setLogLevel(res.data.logger.level);
  };

  useEffect(() => {
    load();
  }, []);

  // ---------------------------------------------------------------------------
  // Feedback-Helfer
  // ---------------------------------------------------------------------------
  const showMsg = (text: string, variant: "info" | "success" | "error" = "info") => {
    setMessage(text);
    setMessageVariant(variant);
  };

  // ---------------------------------------------------------------------------
  // Aktionen
  // ---------------------------------------------------------------------------
  const saveDevice = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const r = await axios.post(`${API_BASE}/admin/config`, { device });
      if (r.data?.error) {
        const map: Record<string, string> = {
          cuda_unavailable: "CUDA ist auf diesem System nicht verfügbar.",
          mps_unavailable: "Apple MPS ist auf diesem System nicht verfügbar.",
          invalid_device: "Ungültiges Gerät.",
        };
        showMsg(map[r.data.error] ?? `Fehler: ${r.data.error}`, "error");
      } else {
        showMsg(
          `Konfiguration gespeichert. Modell auf ${r.data?.model?.device ?? device} geladen.`,
          "success"
        );
      }
      await load();
    } catch (e) {
      showMsg(parseAxiosError(e), "error");
    } finally {
      setBusy(false);
    }
  };

  const saveScoreConfig = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const r = await axios.post(`${API_BASE}/admin/config`, {
        show_scores: showScores,
        score_mode: scoreMode,
      });
      if (r.data?.error) {
        showMsg(`Fehler: ${r.data.error}`, "error");
      } else {
        showMsg("Score-Konfiguration gespeichert.", "success");
      }
      await load();
    } catch (e) {
      showMsg("Fehler beim Speichern der Score-Einstellungen.", "error");
    } finally {
      setBusy(false);
    }
  };

  const saveLogLevel = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const r = await axios.post(`${API_BASE}/admin/loglevel`, { level: logLevel });
      if (r.data?.status === "ok") {
        showMsg(`Log-Level gesetzt auf ${r.data.new_level}.`, "success");
      } else {
        showMsg("Fehler beim Setzen des Log-Levels.", "error");
      }
      await load();
    } catch (e) {
      showMsg(parseAxiosError(e), "error");
    } finally {
      setBusy(false);
    }
  };

  const resetDb = async () => {
    if (confirmText !== "RESET") {
      showMsg('Bitte "RESET" eingeben, um zu bestätigen.', "error");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const r = await axios.post(`${API_BASE}/admin/reset`, { confirm: "RESET" });
      if (r.data?.status === "ok") {
        showMsg("Datenbank wurde geleert und Indizes neu aufgebaut.", "success");
      } else {
        showMsg("Fehler beim Reset.", "error");
      }
      setConfirmText("");
      await load();
    } catch (e) {
      showMsg(parseAxiosError(e), "error");
    } finally {
      setBusy(false);
    }
  };

  const reindex = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const r = await axios.post(`${API_BASE}/admin/reindex`);
      if (r.data?.status === "ok") {
        const { abstracts, authors } = getIndexCounts(r.data);
        showMsg(`Reindex ok. Abstracts: ${abstracts}, Autoren: ${authors}`, "success");
      } else {
        showMsg("Fehler beim Reindex.", "error");
      }
      await load();
    } catch (e) {
      showMsg(parseAxiosError(e), "error");
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".json")) {
      showMsg("Bitte eine JSON-Datei wählen.", "error");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    setBusy(true);
    setMessage(null);
    setFileName(file.name);
    try {
      const res = await axios.post(`${API_BASE}/abstracts/import`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      showMsg(`Import OK: ${res.data.count ?? "–"} neue Abstracts`, "success");
      await load();
    } catch (e) {
      showMsg(parseAxiosError(e), "error");
    } finally {
      setBusy(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {busy && <LoadingOverlay text="Operation läuft…" />}

      {/* Kopfbereich mit Schnellstatus */}
      <div className="bg-white rounded-xl shadow-soft p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Administration</h1>
          <div className="flex gap-2">
            <BackButton />
            <HomeButton />
          </div>
        </div>
        {status && (
          <div className="mt-3 text-sm text-slate-700 grid grid-cols-1 sm:grid-cols-5 gap-3">
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">Model</div>
              <div className="font-medium">{status.model.name}</div>
              <div>
                Device: <span className="font-mono">{status.model.device}</span>
              </div>
              <div className="text-xs mt-1">
                Verfügbar: CPU{status.model.available.cuda ? ", CUDA" : ""}
                {status.model.available.mps ? ", MPS" : ""}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">Datenbank</div>
              <div>
                Abstracts: <span className="font-medium">{status.counts.abstracts}</span>
              </div>
              <div>
                Autoren: <span className="font-medium">{status.counts.authors}</span>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">FAISS</div>
              <div>
                Abstract-Index: <span className="font-medium">{status.indices.abstracts}</span>
              </div>
              <div>
                Author-Index: <span className="font-medium">{status.indices.authors}</span>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">Scores</div>
              <div>
                Aktiv: <span className="font-medium">{status.config.show_scores ? "Ja" : "Nein"}</span>
              </div>
              <div>
                Modus: <span className="font-medium">{status.config.score_mode.toUpperCase()}</span>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">Logger</div>
              <div>
                Level: <span className="font-medium">{status.logger?.level ?? "INFO"}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modell-Konfiguration */}
      <Collapsible title="Modell-Konfiguration">
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">Device</label>
          <select
            value={device}
            onChange={(e) => setDevice(e.target.value as any)}
            disabled={busy}
            className="border border-slate-300 rounded-lg px-3 py-2 bg-white"
          >
            <option value="cpu">CPU</option>
            <option value="cuda" disabled={!available.cuda}>
              GPU (CUDA)
            </option>
            <option value="mps" disabled={!available.mps}>
              GPU (MPS)
            </option>
          </select>
          <button
            onClick={saveDevice}
            disabled={busy || !canSaveDevice}
            className="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            title={!canSaveDevice ? "Keine Änderung oder nicht verfügbar" : "Speichern"}
          >
            Speichern
          </button>
        </div>
        <p className="text-xs text-slate-500">Beim Wechsel wird das Modell neu geladen.</p>
      </Collapsible>

      {/* Score-Anzeige */}
      <Collapsible title="Such-Score-Anzeige">
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">Score anzeigen</label>
          <input type="checkbox" checked={!!showScores} onChange={(e) => setShowScores(e.target.checked)} />
          <select
            value={scoreMode || "cosine"}
            onChange={(e) => setScoreMode(e.target.value as "cosine" | "faiss")}
            disabled={!showScores}
            className="border border-slate-300 rounded-lg px-3 py-2 bg-white"
          >
            <option value="cosine">Cosine Similarity</option>
            <option value="faiss">FAISS-Heuristik</option>
          </select>
          <button
            onClick={saveScoreConfig}
            disabled={busy || !canSaveScores}
            className="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Speichern
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Falls aktiv, werden Suchergebnisse mit einem Ähnlichkeitswert angezeigt.
        </p>
      </Collapsible>

      {/* Logging */}
      <Collapsible title="Logging">
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">Log-Level</label>
          <select
            value={logLevel}
            onChange={(e) => setLogLevel(e.target.value)}
            disabled={busy}
            className="border border-slate-300 rounded-lg px-3 py-2 bg-white"
          >
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
          <button
            onClick={saveLogLevel}
            disabled={busy}
            className="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Setzen
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Wird zur Laufzeit via <code>/admin/loglevel</code> gesetzt.
        </p>
      </Collapsible>

      {/* Import */}
      <Collapsible title="Import">
        <div className="flex items-center gap-3">
          <input
            type="file"
            accept="application/json"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
            disabled={busy}
            className="block"
          />
          {fileName && <span className="text-xs text-slate-500">{fileName}</span>}
        </div>
        <p className="text-xs text-slate-500">JSON-Datei im bisherigen Import-Format.</p>
      </Collapsible>

      {/* Index-Verwaltung */}
      <Collapsible title="Index-Verwaltung">
        <button
          onClick={reindex}
          disabled={busy}
          className="px-3 py-2 rounded-lg bg-slate-800 text-white hover:bg-black disabled:opacity-50"
        >
          FAISS-Indizes neu aufbauen
        </button>
      </Collapsible>

      {/* Danger Zone */}
      <Collapsible title="Danger Zone" defaultOpen={false}>
        <p className="text-sm text-slate-600">
          <strong>Achtung:</strong> Dies löscht <em>alle</em> Daten (Abstracts, Autor*innen, Topics)
          und setzt IDs zurück. Vorgang ist irreversibel.
        </p>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder='Zum Bestätigen "RESET" eingeben'
            disabled={busy}
            className="border border-slate-300 rounded-lg px-3 py-2 bg-white w-64"
          />
          <button
            onClick={resetDb}
            disabled={busy || confirmText !== "RESET"}
            className="px-3 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          >
            Datenbank zurücksetzen
          </button>
        </div>
      </Collapsible>

      {/* Meldungs-Modal */}
      <Modal
        open={!!message}
        title={messageVariant === "error" ? "Fehler" : messageVariant === "success" ? "Erfolg" : "Hinweis"}
        variant={messageVariant}
        onClose={() => setMessage(null)}
      >
        {message}
      </Modal>
    </div>
  );
}
