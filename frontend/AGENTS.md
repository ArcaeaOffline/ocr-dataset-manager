# Frontend

vite + vue3 + UnoCSS SPA built with pnpm.
For general project conventions, see root AGENTS.md.

## Layout

- `components/ui/` holds pure UI primitives. Membership test: generic
  controls only — no `@/api` imports, no domain vocabulary.
- `features/<name>/` holds one annotation feature per directory: its
  domain components plus feature-local `lib/` helpers.
- `views/` are page shells: router targets that compose features.
- `composables/` holds shared, feature-agnostic composables.
- `src/api-schema.d.ts` is the wire contract. `pnpm generate:api`
  regenerates it from the `openapi.json` the backend commits at the
  workspace root (`tests/test_openapi_spec.py` fails when that file is
  stale), and the generated file is committed as well. `api.ts`
  re-exports its types under stable names and wraps all requests.

## Commands

```bash
pnpm dev            # dev server. Proxies /api to 127.0.0.1:8199
pnpm build          # vue-tsc + vite (type check + production build)
pnpm test           # vitest (unit tests: composables and lib helpers)
pnpm lint           # oxlint
pnpm generate:api   # regenerate src/api-schema.d.ts from the committed openapi.json
pnpm format         # oxfmt (write)
pnpm format:check   # oxfmt (check only)
```

## Conventions

- Interactive components compose reka-ui primitives for behavior and are
  styled exclusively with UnoCSS semantic tokens. The token vocabulary
  mirrors the shadcn set and lives in `src/style.css` and
  `uno.config.ts` — extend it there instead of using literal Tailwind
  palette colors (`amber-500`, `blue-500`, …). Palette literals are
  reserved for imagery contexts such as masks over screenshots. Reka
  state attributes (`data-state`, `data-highlighted`, …) map to styles
  via UnoCSS arbitrary variants (`data-[state=open]:…`).
- shadcn-vue is deliberately not used — its component sources target
  Tailwind. Its conventions still apply: button variant names, a visible
  `focus-visible` style on every interactive element, and disabled plus
  placeholder styles on inputs.
- Before writing a control, check `components/ui/` and the
  `uno.config.ts` shortcuts. When a markup pattern appears a second
  time, extract it — class clusters become shortcuts, component
  structures become files in `components/ui/` (membership test above).
- Comments are English. UI copy is Chinese.
- Clicking the active segment of a segmented select clears the value
  back to unknown.
- Features never import each other. Views compose them. No barrel
  files (they defeat Vite tree-shaking) — import by file path.
- `@/` aliases `src/`. Use it for cross-directory imports, keep `./`
  for same-directory siblings.
- Requests go through the shared `useRequest` composable. Deliberately
  no vue-query or pinia.
- Opacity utilities (`/50`, `/80`) silently fail on `var()`-based
  semantic tokens. Apply them only to literal colors, or encode the
  opacity into a dedicated token.
- `vue-tsc` does not flag template tags that resolve to no component.
  Grep the template before removing a component import.
