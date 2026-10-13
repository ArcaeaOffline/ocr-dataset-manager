## What this is

A local annotation tool that turns Arcaea play-result screenshots into
confirmed OCR training records. Recognition is handled by
[core-ocr](https://github.com/ArcaeaOffline/core-ocr),
this repo adds the dataset workflow around it: bulk import,
pre-recognition, human confirmations, SQLite storage.

## Layout

```
backend/          FastAPI + SQLAlchemy + SQLite, uv workspace member.
                  Read backend/AGENTS.md before changing backend code.
frontend/         vite + vue3 + UnoCSS SPA (pnpm); interactive components
                  sit on reka-ui headless primitives
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

# frontend dev server (proxies /api to :8199)
cd frontend && pnpm dev

# frontend checks
pnpm build   # vue-tsc + vite
pnpm lint    # oxlint
pnpm format  # oxfmt
```

## Conventions

- Interactive components compose reka-ui primitives for behavior and are
  styled exclusively with UnoCSS semantic tokens; reka state attributes
  (`data-state`, `data-highlighted`, …) map to styles via UnoCSS arbitrary
  variants (`data-[state=open]:…`). shadcn-vue is deliberately not used —
  its component sources target Tailwind.
- Clicking the active segment of a segmented select clears the value back
  to unknown.
- `vue-tsc` does not flag template tags that resolve to no component; grep
  the template before removing a component import.
- Frontend uses oxc tools.
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
