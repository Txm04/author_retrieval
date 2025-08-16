"""\
app/config.py — zentrale Konfiguration via pydantic-settings (v2)

Ziele:
- Saubere ENV-Überschreibung mit Defaults
- Typisierung/Validierung (Literal, PositiveInt, URLs)
- Robuste Normalisierung von Pfaden (INDEX_DIR)
- Komfort-Helfer (FRONTEND_ORIGINS als Liste)
"""

from __future__ import annotations

# ── Standardbibliothek
from pathlib import Path
from typing import Literal

# ── Drittanbieter
from pydantic import AnyHttpUrl, Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Projektweite Settings.

    Werte werden automatisch aus der Umgebung (ENV) gelesen; Defaults greifen,
    wenn die jeweilige Variable nicht gesetzt ist. `.env` wird ebenfalls geladen.
    """

    # === Datenbank ===
    # Hinweis: SQLAlchemy-URLs mit Dialekt/Driver (z. B. "postgresql+psycopg")
    # lassen sich nur schwer strikt typisieren → wir verwenden str.
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://user:password@localhost/abstractdb",
        description="SQLAlchemy-DSN zur Datenbank",
    )

    # === Logging ===
    LOG_LEVEL: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = Field(
        default="INFO",
        description="Globale Log-Stufe",
    )

    # === Embeddings ===
    EMBED_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="Name/Checkpoint des Embedding-Modells",
    )
    EMBED_DEVICE: Literal["cpu", "cuda", "mps"] | None = Field(
        default=None,
        description="Ziel-Device für das Modell (None = Auto)",
    )

    # === Frontend CORS ===
    # Einzelner Origin (Komma-separierte Liste optional erlaubt, siehe Helper unten)
    FRONTEND_ORIGIN: AnyHttpUrl | str = Field(
        default="http://localhost:3000",
        description="Erlaubter Origin für CORS (optional: mehrere, komma-separiert)",
    )

    # === Such-/UI-Optionen ===
    SHOW_SCORES: bool = Field(
        default=False, description="Zeige Scores im UI"
    )
    SCORE_MODE: Literal["cosine", "faiss"] = Field(
        default="cosine", description="Score-Berechnung im UI/Backend"
    )

    # === FAISS / Index ===
    VECTOR_DIM: PositiveInt = Field(
        default=384, description="Vektordimension des Embedding-Modells"
    )
    INDEX_OVERSAMPLE_FACTOR: PositiveInt = Field(
        default=5, description="Faktor für Oversampling beim Index-Build"
    )

    # Pfad relativ zum Projekt; im Docker per ENV/Volume überschreibbar
    INDEX_DIR: str = Field(
        default=str(Path.cwd() / ".indices"),
        description="Verzeichnis zur Persistenz der FAISS-Indizes",
    )

    # ── Model Config (pydantic v2) ────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Validatoren / Helper ─────────────────────────────────────────────────
    @field_validator("INDEX_DIR", mode="before")
    @classmethod
    def _normalize_index_dir(cls, v: str) -> str:
        """Pfad robust normalisieren (~/… expandieren, absolut machen)."""
        return str(Path(str(v)).expanduser().resolve())

    # Komfort: Erzeuge Liste der erlaubten CORS-Origins aus FRONTEND_ORIGIN
    # - Unterstützt Komma-separierte Werte ("https://a,https://b").
    # - Entfernt Leerzeichen und leere Einträge.
    @property
    def FRONTEND_ORIGINS(self) -> list[str]:  # noqa: N802 (bewusst all caps)
        value = str(self.FRONTEND_ORIGIN)
        return [o.strip() for o in value.split(",") if o and o.strip()]


# Singleton-Settings-Objekt
settings = Settings()  # type: ignore[var-annotated]
