## What this is

A local annotation tool that turns Arcaea play-result screenshots into
confirmed OCR training records. Recognition is handled by
[core-ocr](https://github.com/ArcaeaOffline/core-ocr),
this repo adds the dataset workflow around it: bulk import,
pre-recognition, human review, SQLite storage.

## Layout

```
backend/          FastAPI + SQLAlchemy + SQLite, uv workspace member
  app/ocr/        text provider (RapidOCR), custom ROIs
  app/services/   import pipeline, prefill cache
  app/routers/    HTTP surface
  migrations/     alembic (auto-upgrades on app startup)
frontend/         vite + vue3 + UnoCSS SPA (pnpm)
data/             gitignored runtime data: db, image store, thumbnails and others
```

## Commands

```bash
# install (workspace root; --all-packages is required, plain `uv sync`
# installs nothing but the root project)
uv sync --all-packages

# backend dev server
cd backend && uv run uvicorn app.main:app --port 8199

# frontend dev server (proxies /api to :8199)
cd frontend && pnpm dev

# frontend checks
pnpm build   # vue-tsc + vite
pnpm lint    # oxlint
pnpm format  # oxfmt

# backend checks (run from the workspace root)
uv run ruff check backend        # lint (autofix: append --fix)
uv run basedpyright backend      # type check
```

## Schema changes

Edit `backend/app/models.py`, then from `backend/`:

```bash
ODM_DATABASE_URL="sqlite:///./scratch.db" uv run alembic upgrade head
ODM_DATABASE_URL="sqlite:///./scratch.db" uv run alembic revision --autogenerate -m "..."
rm scratch.db
```

Migrations apply automatically when the backend starts; the dev database
can be reset any time by deleting `data/odm.sqlite3`.

## Architecture notes

- **Recognition chain**: `DeviceRoisAutoSelector` (T1/T2 detection) →
  per-ROI OCR via `RapidOcrTextProvider` → `ImageHashDatabaseIdProvider`
  (ihdb) for song/partner → color-mask voting for enums. Custom ROIs for
  fields core-ocr does not cover live in `backend/app/ocr/custom_rois.py`
  and follow core-ocr's factor-based anchoring (T1 is scaled against
  h/720, T2 against h/1080).
- **Small single-line ROIs must skip detection**: PaddleOCR det fails or
  garbles them; use `RapidOcrTextProvider.result_rec_only()` (replicate
  pad + 2x upscale + recognition only).
- **Storage rule**: the database only stores human-confirmed values.
  OCR candidates, confidences, mask votes are recomputed on demand and
  cached in an LRU (`backend/app/services/prefill.py`), never persisted.
  "Not annotated yet" is represented by the absence of a
  `device_results` row, not by a status column.
- **device vs b30**: `device_results` is strictly 1:1 with an image. The
  planned B30/B50 mode gets its own `b30_components` table (one row per
  component) — do not add per-component concepts to the device table.
- Text recognition intentionally uses RapidOCR (PaddleOCR onnx models)
  instead of the CRNN bundled with core-ocr; the CRNN provider remains
  available as a fallback.

## Conventions

- Commit messages: conventional-commit style (`feat:`, `fix:`, `docs:`,
  `chore:`), subject in English, body states what is here now — not the
  history of how it got that way.
- Code comments state current behavior and constraints only; no
  change-narration ("previously X", "no longer Y").
- Python uses `ruff` and `basedpyright` (config in root `pyproject.toml`).
  Frontend uses oxc tools.

## Known limitations / roadmap

- No export path from SQLite to training formats yet.
- B30/B50 image mode not implemented (backend abstraction in core-ocr
  already exists: `scenarios/b30`).
- Near-duplicate warnings: the perceptual hash column is populated but
  nothing compares it yet.
