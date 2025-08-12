import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # === Datenbank ===
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:password@localhost/abstractdb"
    )

    # === Embeddings ===
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
    EMBED_DEVICE: str | None = os.getenv("EMBED_DEVICE")  # "cpu", "cuda", "mps" oder None

    # === Frontend CORS ===
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

    # === Such-/UI-Optionen ===
    SHOW_SCORES: bool = os.getenv("SHOW_SCORES", "false").lower() == "true"
    SCORE_MODE: str = os.getenv("SCORE_MODE", "cosine")  # "cosine" | "faiss"

    # === FAISS / Index ===
    VECTOR_DIM: int = int(os.getenv("VECTOR_DIM", 384))
    INDEX_OVERSAMPLE_FACTOR: int = int(os.getenv("INDEX_OVERSAMPLE_FACTOR", 5))

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Singleton-Settings-Objekt
settings = Settings()
