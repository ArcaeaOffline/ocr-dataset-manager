## What this is

A local annotation tool that turns Arcaea play-result screenshots into
confirmed OCR training records. Recognition is handled by
[core-ocr](https://github.com/ArcaeaOffline/core-ocr),
this repo adds the dataset workflow around it: bulk import,
pre-recognition, human confirmations, SQLite storage.

## Layout

```
backend/          FastAPI + SQLAlchemy + SQLite, uv workspace member
  app/ocr/        text provider (RapidOCR), custom ROIs, layout probe
  app/ocr/b30/    B30/B50 bot layout definitions and card recognizers
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
  "Not annotated yet" is represented by the absence of a row in the
  relevant results table, not by a status column.
- **device vs b30**: `device_results` is strictly 1:1 with an image.
  B30/B50 screenshots get their own `b30_results` (1:1, carries the
  confirmed bot layout) and `b30_components` (one row per card) tables —
  do not add per-component concepts to the device table. A B30 image
  counts as fully reviewed when every component its layout expects has a
  checked row; there is no image-level checked flag.
- **B30/B50 layouts** live in `backend/app/ocr/b30/`: each `B30Layout`
  describes a bot's canonical canvas, card grid, and per-card ROIs, all
  factor-scaled by `width / canvas_width`. `layout_probe.py` classifies
  a screenshot by aspect ratio plus background-independent structural
  checks; the probe is only a prefill proposal and never persists.
  `chieri_v4` delegates card cutting and OCR to core-ocr's
  `ChieriBotV4Best30Scenario`; yurisaki and arcaeaonline have local
  recognizers. Card OCR is computed on request per card (~0.4s) and is
  never bulk-warmed. Clear-type badges map onto the st3 clearType values
  (0-5, including easy/hard clear); arcaeaonline cards render no rating
  class (their level diamond is difficulty-agnostic) and no P/F/L.
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
- B30/B50 bot layouts covered: chieri v4, yurisaki, arcaeaonline
  (b30/b50). Other bot renderings probe as unclassified and need a new
  `B30Layout` + recognizer.
- Near-duplicate warnings: the perceptual hash column is populated but
  nothing compares it yet.

## Help make this project better

- See [docs/token-usage.md](./docs/token-usage.md).
- See [CONTRIBUTING.md](./CONTRIBUTING.md).

## PR policy

Every PR description must include a verification note: either who (a **HUMAN**)
ran what and confirmed the behavior, or the literal string `No human verifications`.
Never write a verification claim that did not happen or fully done by AI.
