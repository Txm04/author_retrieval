#!/usr/bin/env bash
set -euo pipefail

# Default setzen, falls vergessen
: "${INDEX_DIR:=/app/.indices}"

# Ordner existiert? Wenn nicht, anlegen.
mkdir -p "$INDEX_DIR"

# Eigentümer auf appuser setzen (auch wenn Volume gemountet)
# Fehler ignorieren, falls das Dateisystem chown nicht unterstützt
if ! chown -R appuser:appuser "$INDEX_DIR" 2>/dev/null; then
  echo "WARN: konnte chown auf $INDEX_DIR nicht ausführen (ignoriere)."
fi

# Optional: Schreibtest (hilft bei Diagnose)
if ! gosu appuser bash -lc "test -w '$INDEX_DIR'"; then
  echo "ERROR: $INDEX_DIR ist für appuser nicht schreibbar."
  echo "Bitte Volume-Rechte prüfen oder anderen INDEX_DIR setzen."
  exit 1
fi

# App als appuser starten
exec gosu appuser "$@"
