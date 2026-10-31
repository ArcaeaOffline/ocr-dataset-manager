## What this is

A local annotation tool that turns Arcaea play-result screenshots into
confirmed OCR training records. Recognition is handled by
[core-ocr](https://github.com/ArcaeaOffline/core-ocr),
this repo adds the dataset workflow around it: bulk import,
pre-recognition, human confirmations, SQLite storage.

## Layout

```
backend/          FastAPI + SQLAlchemy + SQLite, uv workspace member.
                  Read `backend/AGENTS.md` before changing backend code.
frontend/         vite + vue3 + UnoCSS SPA (pnpm).
                  Read `frontend/AGENTS.md` before changing frontend code.
data/             gitignored runtime data: db, image store, thumbnails and others
```

Note: never commit user-provided real game screenshots or assets, for
privacy and copyright reasons. Such files are user-specific, so ignore
them in the local `.git/info/exclude`, not the shared `.gitignore`,
and not user-global ignore files.

## Commands

```bash
# install from the workspace root. --all-packages is required: plain
# `uv sync` installs nothing but the root project
uv sync --all-packages

# local all-checks: backend format + lint + types + tests,
# frontend build + tests + lint + format
uv run ruff format --check backend && uv run ruff check backend && \
  uv run basedpyright backend && \
  (cd backend && uv run pytest -q) && \
  (cd frontend && pnpm build && pnpm test && pnpm lint && pnpm format:check)
```

## Mandatory checks

After any code change, agents MUST run the all-checks command above
and fix every failure before committing or reporting the work done.
If a check cannot run in the current environment, say so explicitly
instead of skipping it silently.

## Conventions

- Commit messages: conventional-commit style (`feat:`, `fix:`, `docs:`,
  `chore:`), subject in English, body states what is here now, not the
  history of how it got that way.
- Code comments state current behavior and constraints only. No
  change-narration ("previously X", "no longer Y").

## Help make this project better

- See [docs/token-usage.md](./docs/token-usage.md).
- See [CONTRIBUTING.md](./CONTRIBUTING.md).

## PR policy

Every PR description must include a verification note: either who (a **HUMAN**)
ran what and confirmed the behavior, or the literal string `No human verifications`.
Never write a verification claim for something that did not happen or
was performed entirely by AI.
