# ASTRO

Monorepo for the Large Data Vault: a local pipeline for managing raw media,
generating video proxies, and inspecting model weight assets — plus a
dashboard to drive it all.

```
ASTRO/
├── my-large-data-vault/   # Vault pipelines + JARVIS assistant
│   ├── main.py              # One-shot pipeline run (storage check, cleanup, media, weights)
│   ├── jarvis.py             # Interactive assistant loop (listen -> act -> speak)
│   └── src/utils/
│       ├── tools.py          # Phase 1 — intent router / tool registry
│       ├── llm.py            # Phase 3 — API-based inference w/ local fallback
│       └── voice.py          # Phase 2 — STT/TTS, degrades to text if deps missing
├── api/                   # FastAPI service exposing pipelines + assistant to the UI
└── frontend/              # React + Vite + TS dashboard (Storage / Media / Weights / Chat)
```

## JARVIS assistant

- **Run in the terminal:** `python jarvis.py` from `my-large-data-vault/`. Works with zero extra
  deps (typed input/printed output); install `requirements-jarvis.txt` for real voice.
- **Run from the dashboard:** the Chat page hits `POST /api/chat`, which uses the same
  `handle_intent()` / `ask_llm()` logic as the CLI loop — behavior is identical either way.
- **Known commands** (keyword-matched, see `src/utils/tools.py`): "check disk space", "clean cache",
  "transcode" / "generate proxies", "list proxies", "list weights", "zone report", "system stats",
  "open dashboard". Anything else falls through to the configured LLM.
- **LLM fallback:** set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in your environment. With neither
  set, JARVIS reports what local weights exist (if any) rather than guessing — local inference isn't
  wired to a model-specific loader yet.

## Running it

**1. Backend API** (from the `ASTRO/` root):

```bash
cd my-large-data-vault && pip install -r requirements.txt && cd ..
pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
```

Interactive API docs: http://127.0.0.1:8000/docs

**2. Frontend dashboard** (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to the
backend on port 8000, so both need to be running.

## What the dashboard shows

- **Storage** — disk headroom, size of each vault zone (`00_raw_data` /
  `01_processed_data` / `02_build_cache` / `03_backups_and_archives`), a
  folder tree browser, and a one-click scratch cleanup.
- **Media** — raw footage awaiting a proxy, existing 720p proxies, and a
  button to kick off transcoding as a background job with live progress.
- **Weights** — every `.safetensors` / `.pt` / `.bin` file in
  `00_raw_data/model_weights`, with per-tensor dtype/shape detail for
  `.safetensors` files (header-only, nothing loaded into RAM).

## Notes on setup_jarvis.py

Deprecated — it's a no-op now (see the docstring). It used to overwrite the vault's source files
with an outdated snapshot; keep editing `my-large-data-vault/src/` directly instead.

## Notes

- The vault pipelines in `my-large-data-vault/` still run standalone via
  `python main.py` exactly as before — the API layer imports them rather
  than replacing them.
- Job tracking is in-memory (see `api/job_manager.py`), which is intentional
  for a local, single-user tool. It resets if the API process restarts.
