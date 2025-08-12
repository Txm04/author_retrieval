import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import BackButton from "../components/BackButton";
import LoadingOverlay from "../components/LoadingOverlay";
import Modal from "../components/Modal";
import Collapsible from "../components/Collapsible";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

type Status = {
  model: {
    name: string;
    device: "cpu" | "cuda" | "mps";
    available: { cpu: boolean; cuda: boolean; mps: boolean };
  };
  counts: { abstracts: number; authors: number };
  indices: { abstracts: number; authors: number };
  config: {
    show_scores: boolean;
    score_mode: "cosine" | "faiss";
  };
};

export default function Admin() {
  const [status, setStatus] = useState<Status | null>(null);
  const [device, setDevice] = useState<"cpu" | "cuda" | "mps">("cpu");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageVariant, setMessageVariant] = useState<"info" | "success" | "error">("info");
  const [fileName, setFileName] = useState<string>("");

  const available = status?.model.available || { cpu: true, cuda: false, mps: false };
  const currentDevice = status?.model.device;
  const canSaveDevice = useMemo(() => {
    if (!status) return false;
    if (device === currentDevice) return false;
    if (device === "cuda" && !available.cuda) return false;
    if (device === "mps" && !available.mps) return false;
    return true;
  }, [status, device, currentDevice, available]);

  const [showScores, setShowScores] = useState(false);
  const [scoreMode, setScoreMode] = useState<"cosine" | "faiss">("cosine");

  const load = async () => {
    const res = await axios.get<Status>(`${API_BASE}/admin/status`);
    setStatus(res.data);
    if (res.data?.model?.device) setDevice(res.data.model.device);
    if (res.data?.config) {                   // ← guard
      setShowScores(res.data.config.show_scores);
      setScoreMode(res.data.config.score_mode);
    }
  };


  useEffect(() => { load(); }, []);

  const showMsg = (text: string, variant: "info" | "success" | "error" = "info") => {
    setMessage(text);
    setMessageVariant(variant);
  };

  const saveDevice = async () => {
    setBusy(true); setMessage(null);
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
        showMsg(`Konfiguration gespeichert. Modell auf ${r.data?.model?.device ?? device} geladen.`, "success");
      }
      await load();
    } catch {
      showMsg("Fehler beim Speichern.", "error");
    } finally { setBusy(false); }
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
    } catch {
      showMsg("Fehler beim Speichern der Score-Einstellungen.", "error");
    } finally {
      setBusy(false);
    }
  };

  const canSaveScores = useMemo(() => {
    const cfg = status?.config;
    if (!cfg) return true; // allow save if server hasn't sent config yet
    return showScores !== cfg.show_scores || scoreMode !== cfg.score_mode;
  }, [status, showScores, scoreMode]);



  const reindex = async () => {
    setBusy(true); setMessage(null);
    try {
      const r = await axios.post(`${API_BASE}/admin/reindex`);
      if (r.data?.status === "ok") {
        showMsg(`Reindex ok. Abstracts: ${r.data.indices.abstracts}, Autoren: ${r.data.indices.authors}`, "success");
      } else {
        showMsg("Fehler beim Reindex.", "error");
      }
      await load();
    } catch {
      showMsg("Fehler beim Reindex.", "error");
    } finally { setBusy(false); }
  };

  const upload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".json")) {
      showMsg("Bitte eine JSON-Datei wählen.", "error"); return;
    }
    const fd = new FormData();
    fd.append("file", file);
    setBusy(true); setMessage(null); setFileName(file.name);
    try {
      const res = await axios.post(`${API_BASE}/abstracts/import`, fd, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      showMsg(`Import OK: ${res.data.count ?? "–"} neue Abstracts`, "success");
      await load();
    } catch {
      showMsg("Fehler beim Import.", "error");
    } finally { setBusy(false); }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {busy && <LoadingOverlay text="Operation läuft…" />}

      <div className="bg-white rounded-xl shadow-soft p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Administration</h1>
          <BackButton />
        </div>
        {status && (
          <div className="mt-3 text-sm text-slate-700 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">Model</div>
              <div className="font-medium">{status.model.name}</div>
              <div>Device: <span className="font-mono">{status.model.device}</span></div>
              <div className="text-xs mt-1">
                Verfügbar: CPU{available.cuda ? ", CUDA" : ""}{available.mps ? ", MPS" : ""}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">Datenbank</div>
              <div>Abstracts: <span className="font-medium">{status.counts.abstracts}</span></div>
              <div>Autoren: <span className="font-medium">{status.counts.authors}</span></div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50">
              <div className="text-slate-500">FAISS</div>
              <div>Abstract-Index: <span className="font-medium">{status.indices.abstracts}</span></div>
              <div>Author-Index: <span className="font-medium">{status.indices.authors}</span></div>
            </div>
              <div className="p-3 rounded-lg bg-slate-50">
                <div className="text-slate-500">Scores</div>
                <div>Aktiv: <span className="font-medium">{status.config.show_scores ? "Ja" : "Nein"}</span></div>
                <div>Modus: <span className="font-medium">{status.config.score_mode.toUpperCase()}</span></div>
              </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6 space-y-3">
        <h2 className="font-semibold">Modell-Konfiguration</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">Device</label>
          <select
            value={device}
            onChange={(e) => setDevice(e.target.value as any)}
            disabled={busy}
            className="border border-slate-300 rounded-lg px-3 py-2 bg-white"
          >
            <option value="cpu">CPU</option>
            <option value="cuda" disabled={!available.cuda}>GPU (CUDA)</option>
            <option value="mps" disabled={!available.mps}>GPU (MPS)</option>
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
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6 space-y-3">
        <h2 className="font-semibold">Such-Score-Anzeige</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">Score anzeigen</label>
          <input
            type="checkbox"
            checked={!!showScores}
            onChange={(e) => setShowScores(e.target.checked)}
          />
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
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6 space-y-3">
        <h2 className="font-semibold">Import</h2>
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
      </div>

      <div className="bg-white rounded-xl shadow-soft p-6 space-y-3">
        <h2 className="font-semibold">Index-Verwaltung</h2>
        <button
          onClick={reindex}
          disabled={busy}
          className="px-3 py-2 rounded-lg bg-slate-800 text-white hover:bg-black disabled:opacity-50"
        >
          FAISS-Indizes neu aufbauen
        </button>
      </div>

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
