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

Note: when user provides real game screenshots or assets, NEVER expose
the files into repository. Such files should be ignored in local `.git/info/exclude`
(instead of `.gitignore`, do not add user preferences to global options)
due to privacy and copyright issues.

## Commands

```bash
# install (workspace root; --all-packages is required, plain `uv sync`
# installs nothing but the root project)
uv sync --all-packages

# local all-checks: backend format + lint + types + tests,
# frontend build + lint + format
uv run ruff format --check backend && uv run ruff check backend && \
  uv run basedpyright backend && \
  (cd backend && uv run pytest -q) && \
  (cd frontend && pnpm build && pnpm lint && pnpm format:check)
```

## Mandatory checks

After any code change, agents MUST run the all-checks command above
and fix every failure before committing or reporting the work done.
If a check cannot run in the current environment, say so explicitly
instead of skipping it silently.

## Conventions

- Commit messages: conventional-commit style (`feat:`, `fix:`, `docs:`,
  `chore:`), subject in English, body states what is here now — not the
  history of how it got that way.
- Code comments state current behavior and constraints only; no
  change-narration ("previously X", "no longer Y").

## Help make this project better

- See [docs/token-usage.md](./docs/token-usage.md).
- See [CONTRIBUTING.md](./CONTRIBUTING.md).

## PR policy

Every PR description must include a verification note: either who (a **HUMAN**)
ran what and confirmed the behavior, or the literal string `No human verifications`.
Never write a verification claim that did not happen or fully done by AI.
