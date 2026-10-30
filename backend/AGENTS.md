# Backend

FastAPI + SQLAlchemy + SQLite service, a uv workspace member.
For general project conventions, see root AGENTS.md.

## Layout

```
app/ocr/        text provider (RapidOCR), layout probe
app/ocr/b30/    B30/B50 bot layout definitions and card recognizers
app/services/   import pipeline, prefill cache, queue queries
app/routers/    HTTP surface
migrations/     alembic (auto-upgrades on app startup)
tests/          API/characterization tests, real-OCR smoke fixtures
```

## Commands

```bash
# from the workspace root
uv run ruff format --check backend  # format check (write: drop --check)
uv run ruff check backend           # lint (autofix: append --fix)
uv run basedpyright backend         # type check (config in root pyproject.toml)

# backend dev server
cd backend && uv run uvicorn app.main:app --port 8199

# single-process mode serving the built frontend. --no-open: headless
uv run odm --no-open

# tests (from backend/). The real-OCR smoke is part of the default run
# and skips itself where no ihdb is present (CI)
uv run pytest
uv run pytest -m "not slow"  # quick run without the real-OCR smoke
```

## Schema changes

Edit `app/models.py`, then from `backend/`:

```bash
ODM_DATABASE_URL="sqlite:///./scratch.db" uv run alembic upgrade head
ODM_DATABASE_URL="sqlite:///./scratch.db" uv run alembic revision --autogenerate -m "..."
rm scratch.db
```

Migrations apply automatically when the backend starts. The dev database
can be reset any time by deleting `data/odm.sqlite3`.

## Architecture notes

- **Recognition chain**: `DeviceRoisAutoSelector` (T1/T2 detection) →
  per-ROI OCR via `RapidOcrTextProvider` → `ImageHashDatabaseIdProvider`
  (ihdb) for song/partner → color-mask voting for enums. All device
  roi windows, including high score / shiny / early-late, come from
  core-ocr's packaged layout data.
- **Small single-line ROIs must skip detection**: PaddleOCR det fails or
  garbles them. Use `RapidOcrTextProvider.result_rec_only()` (replicate
  pad + 2x upscale + recognition only).
- **Annotate view crops**: the device flow displays the black-edge-cropped
  screenshot (`/images/{id}/cropped`) and CSS-crops each field window out
  of it, positioned by `/images/{id}/device_rois` (rects rounded exactly
  as the OCR chain rounds them, so crops show the pixels the OCR read).
  The raw `/file` is the load fallback and the viewer's full-fidelity
  source.
- **Storage rule**: the database only stores human-confirmed values.
  OCR candidates, confidences, mask votes are recomputed on demand and
  cached in an LRU (`app/services/prefill.py`), never persisted.
  "Not annotated yet" is represented by the absence of a row in the
  relevant results table, not by a status column.
- **device vs b30**: `device_results` is strictly 1:1 with an image.
  B30/B50 screenshots get their own `b30_results` (1:1, carries the
  confirmed bot layout) and `b30_components` (one row per card) tables —
  do not add per-component concepts to the device table. One image,
  one kind: `services/results.py` drops the other kind's rows in the
  same transaction on every save, and the annotate UI confirms before
  the first cross-kind save. A B30 image counts as fully reviewed when
  every component its layout expects has a checked row. There is no
  image-level checked flag.
- **B30/B50 layouts** live in `app/ocr/b30/`: each `B30Layout` wraps
  core-ocr's `CardLayout`, an explicit card origin list plus card-local
  field windows, factor-scaled by `width / canvas_width`. Layout data is
  JSON in `app/ocr/b30/layouts/`, except chieri_v4 which loads core-ocr's
  packaged copy. `layout_probe.py` classifies a screenshot by aspect
  ratio plus background-independent structural checks. The probe is only
  a prefill proposal and never persists. The UI mirrors that: a manual
  flow switch and layout selector in the image area override the probe
  per view as ephemeral UI state, while the queue kind still derives
  from saved rows. The endpoints take explicit overrides: `/b30_card`
  and `/b30_prefill` accept `?layout=`, and `/prefill` accepts
  `?flow=device` to compute the device proposal for a b30-probed image.
  `chieri_v4` delegates card cutting and OCR to core-ocr's
  `ChieriBotV4Best30Scenario`. Yurisaki and arcaeaonline have local
  recognizers. Card OCR is computed on request per card (~0.4s) and is
  never bulk-warmed. Clear-type badges map onto the st3 clearType values
  0-5, including easy/hard clear. Arcaeaonline cards render no rating
  class (their level diamond is difficulty-agnostic) and no P/F/L.
- Text recognition intentionally uses RapidOCR (PaddleOCR onnx models)
  instead of the CRNN bundled with core-ocr. The CRNN provider remains
  available as a fallback.

## Conventions

- Sessions are injected with `Depends(get_session)`. Endpoints never
  open `SessionLocal` themselves. The import pipeline's background
  thread is the deliberate exception, as it is not request-scoped.
- Routers stay thin: endpoints, parameter validation, HTTP error
  mapping. Query and business logic live in services, not routers.
- SQLAlchemy 2.0 `select()` style only.
- Endpoints return Pydantic models, never bare dicts. A response model
  silently drops undeclared fields, so check field parity against the
  exact-equality tests. After API changes, run
  `uv run python backend/scripts/dump_openapi.py` to refresh the
  committed `openapi.json` (a test fails while it is stale), then
  `pnpm generate:api` in `frontend/` to regenerate the wire types.
- Add or update characterization tests before changing behavior.
- `Depends()` in parameter defaults is declaration syntax, not a
  mutable default: B008 and `reportCallInDefaultInitializer` are
  deliberately suppressed in the root `pyproject.toml`.

## Tests

- `tests/conftest.py` points `ODM_DATA_DIR` and `ODM_DATABASE_URL` at a
  temp dir before the first `app` import — `app.config` snapshots its
  paths and `app.db` binds its engine at import time.
- The test database is a real SQLite file in that temp dir, not
  in-memory: alembic opens its own connection, and `SessionLocal` is
  name-imported, so monkeypatching could not intercept it.
- Committed image fixtures are synthetic (hand-drawn SVGs exported to
  PNG). The real-OCR smoke runs in the default suite, seeded from the
  repository's `data/ihdb.db` when present (`tests/conftest.py`), and
  skips on machines without one, e.g. CI.

## Known limitations / roadmap

- No export path from SQLite to training formats yet.
- B30/B50 bot layouts covered: chieri v4, yurisaki, arcaeaonline
  (b30/b50). Other bot renderings probe as unclassified. They can still
  be annotated manually via the flow switch, but OCR prefill for them
  needs a new `B30Layout` + recognizer.
- Near-duplicate warnings: the perceptual hash column is populated but
  nothing compares it yet.
