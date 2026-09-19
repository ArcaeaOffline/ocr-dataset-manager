# ocr-dataset-manager

A local, web-based annotation tool for building OCR training datasets from
Arcaea play-result screenshots. It pairs with
[core-ocr](https://github.com/ArcaeaOffline/core-ocr), which provides the
screenshot layout detection, text/icon recognition primitives, and the image
hash database (ihdb) used for song and partner identification.

The workflow it is built around:

1. **Bulk import** a folder of screenshots. Files are content-hashed for
   deduplication, renamed to UUIDs, and organized into a local store.
2. **Automatic pre-recognition** runs on every image: T1/T2 layout
   detection, numeric field OCR (score, PURE/FAR/LOST, max recall, high
   score, shiny count, early/late counts), clear-type and difficulty
   classification via color masks, and song/partner identification against
   an ihdb.
3. **Human review** is what the UI optimizes for: every field arrives
   pre-filled, suspicious values are flagged by client-side consistency
   checks (identity equations like `pure = shiny + early + late`), and
   annotating one image is mostly "glance, correct, confirm".
4. Confirmed values land in SQLite; everything OCR-related is recomputable
   and never persisted.

A B30/B50 results-image mode (one image, many sub-components) is planned;
the database layout keeps device results and that future mode separate.

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and [pnpm](https://pnpm.io/)
- A checkout of [core-ocr](https://github.com/ArcaeaOffline/core-ocr) as a
  sibling directory (wired in as a path dependency)
- Your own data, prepared locally (see below)

## What you need to provide

This repository distributes no game assets and no game-derived data. To run
recognition you need, on your own machine:

- **An image hash database (ihdb)** built with core-ocr's
  `ImageHashesDatabaseBuilder` from song jackets and partner icons you
  extracted yourself. Set its path via `ODM_IHDB_PATH`.
- **Partner icons and the song list**, extracted from an Arcaea APK:

  ```bash
  cd backend
  uv run python scripts/extract_assets.py /path/to/arcaea.apk
  ```

This writes `data/partner_icons/` and `data/catalog/songlist` relative to
the repository root.

## Running

```bash
# backend
uv sync --all-packages
cd backend
uv run uvicorn app.main:app --port 8199

# frontend (second terminal, from the repository root)
cd frontend
pnpm install
pnpm dev
```

The dev server proxies `/api` to the backend. For daily use you can also
build the frontend (`pnpm build`) and serve the static files from FastAPI.

### Configuration

All paths have defaults that work for a checkout sitting next to a
`core-ocr` checkout, and can be overridden with environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ODM_DATA_DIR` | `<repo>/data` | Database, image store, thumbnails, assets |
| `ODM_DATABASE_URL` | sqlite in the data dir | SQLAlchemy URL |
| `ODM_IHDB_PATH` | `<core-ocr>/__debug/ihdb-7.0.255.db` | Image hash database |
| `ODM_CRNN_MODEL_PATH` | `<core-ocr>/assets/ocr/model_patched.onnx` | Fallback text model |

## License

[MIT](LICENSE).

Arcaea is a game by lowiro. This project is an independent tool and is not
affiliated with or endorsed by lowiro.
