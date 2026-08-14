"""
ASTRO Vault API — local FastAPI service exposing the my-large-data-vault
pipelines (storage, media, model weights) to the dashboard frontend.

Run from the ASTRO/ repo root:
    uvicorn api.main:app --reload --port 8000
"""
import sys
from pathlib import Path

# Make the vault's package importable (main.py, src/*) without moving any files.
VAULT_ROOT = Path(__file__).resolve().parent.parent / "my-large-data-vault"
sys.path.insert(0, str(VAULT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import storage as storage_router
from api.routers import media as media_router
from api.routers import models as models_router
from api.routers import assistant as assistant_router

app = FastAPI(
    title="ASTRO Vault API",
    description="Local API for browsing and driving the Large Data Vault pipelines.",
    version="0.1.0",
)

# Local-only dashboard — wide open CORS is fine since nothing here is public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(storage_router.router, prefix="/api/storage", tags=["storage"])
app.include_router(media_router.router, prefix="/api/media", tags=["media"])
app.include_router(models_router.router, prefix="/api/models", tags=["models"])
app.include_router(assistant_router.router, prefix="/api", tags=["assistant"])


@app.get("/api/health")
def health():
    return {"status": "ok", "vault_root": str(VAULT_ROOT)}
