# Backend

FastAPI + SQLAlchemy + SQLite service, a uv workspace member.
For general project conventions, see root AGENTS.md.

## Layout

```
app/ocr/        text provider (RapidOCR), custom ROIs, layout probe
app/ocr/b30/    B30/B50 bot layout definitions and card recognizers
app/services/   import pipeline, prefill cache, queue queries
app/routers/    HTTP surface
migrations/     alembic (auto-upgrades on app startup)
tests/          API/characterization tests, real-OCR smoke fixtures
```

## Commands

```bash
# from the workspace root
uv run ruff check backend        # lint (autofix: append --fix)
uv run basedpyright backend      # type check (config in root pyproject.toml)

# backend dev server
cd backend && uv run uvicorn app.main:app --port 8199

# tests (from backend/)
uv run pytest            # API and characterization tests
uv run pytest -m slow    # real-OCR smoke on the committed fixtures
```

## Schema changes

Edit `app/models.py`, then from `backend/`:

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
  fields core-ocr does not cover live in `app/ocr/custom_rois.py`
  and follow core-ocr's factor-based anchoring (T1 is scaled against
  h/720, T2 against h/1080).
- **Small single-line ROIs must skip detection**: PaddleOCR det fails or
  garbles them; use `RapidOcrTextProvider.result_rec_only()` (replicate
  pad + 2x upscale + recognition only).
- **Storage rule**: the database only stores human-confirmed values.
  OCR candidates, confidences, mask votes are recomputed on demand and
  cached in an LRU (`app/services/prefill.py`), never persisted.
  "Not annotated yet" is represented by the absence of a row in the
  relevant results table, not by a status column.
- **device vs b30**: `device_results` is strictly 1:1 with an image.
  B30/B50 screenshots get their own `b30_results` (1:1, carries the
  confirmed bot layout) and `b30_components` (one row per card) tables —
  do not add per-component concepts to the device table. A B30 image
  counts as fully reviewed when every component its layout expects has a
  checked row; there is no image-level checked flag.
- **B30/B50 layouts** live in `app/ocr/b30/`: each `B30Layout`
  describes a bot's canonical canvas, card grid, and per-card ROIs, all
  factor-scaled by `width / canvas_width`. `layout_probe.py` classifies
  a screenshot by aspect ratio plus background-independent structural
  checks; the probe is only a prefill proposal and never persists. The
  UI mirrors that: a manual flow switch and layout selector in the
  image area override the probe per view (ephemeral UI state — queue
  kind still derives from saved rows), and the endpoints take explicit
  overrides (`/b30_card`, `/b30_prefill` accept `?layout=`; `/prefill`
  accepts `?flow=device` to compute the device proposal for a
  b30-probed image).
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

- Sessions are injected with `Depends(get_session)`; endpoints never
  open `SessionLocal` themselves (the import pipeline's background
  thread is the deliberate exception — it is not request-scoped).
- Routers stay thin: endpoints, parameter validation, HTTP error
  mapping. Query and business logic live in services, not routers.
- SQLAlchemy 2.0 `select()` style only.
- Endpoints return Pydantic models, never bare dicts. A response model
  silently drops undeclared fields, so check field parity against the
  exact-equality tests; new response fields must be mirrored in
  `frontend/src/api.ts`.
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
  PNG); `-m slow` runs them through the real OCR chain and skips only
  where the ihdb file is absent.

## Known limitations / roadmap

- No export path from SQLite to training formats yet.
- B30/B50 bot layouts covered: chieri v4, yurisaki, arcaeaonline
  (b30/b50). Other bot renderings probe as unclassified; they can still
  be annotated manually via the flow switch, but OCR prefill for them
  needs a new `B30Layout` + recognizer.
- Near-duplicate warnings: the perceptual hash column is populated but
  nothing compares it yet.
