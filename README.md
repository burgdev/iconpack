# iconpilot

Multi-model pipeline for designing consistent SVG icon packs: cheap models draft
variants, deterministic tools gate them, and you decide each round in a review page.

**Status:** scaffold + phase 1 — `gate` (parse/lint/geometry slice) and `styles`
(registry) work today; rounds/server/export are stubs.

## Install

```bash
uv tool install iconpilot             # from PyPI (once published)
uv tool install --from . iconpilot    # from a checkout
iconpilot install-skill               # symlink skill into ~/.agents/skills/ (+ ~/.claude/skills/)
```

## Concepts

**Pack** — a directory: `pack.json` (spec + icons), `icons/<icon>/<variant>.svg`
(readable originals — the source of truth), `.runs/` (scratch), `export/`
(regenerated assets; never hand-edited).

**Variants are siblings, not derivations** — an icon (`brief`, optional `prompt`,
optional `main_color`) has independently authored variants, each referencing a
style: `primitive` (ultra-minimal), `mono`, `color` (more detail). One variant
may be `anchor` — its approved SVG is the family form baseline injected into all
sibling prompts; `reference: "<icon>#<variant>"` adds a specific sibling to
visually match. These relations form a DAG (acyclicity + target existence are
validated on every load; a changed dependency marks dependents `stale`).

**Links** — a variant may alias another icon's variant (`{"link": "hut#primitive"}`):
no own file, no own state, inherits the master's status; export materializes per
icon name. `unlink` re-materializes as `in_review`. Links on non-mono styles
require equal `main_color` on both icons.

**Styles** — one definition drives gates *and* prompts: construction
(outline/solid/outline+fill) × color mode (mono/bicolor/color/gradient) × weight
× detail (node budget, min gap) plus drafter vocabulary. Three tiers: built-ins
(`primitive`, `mono-line`, `mono-line-thin`, `mono-bold`, `filled`, `duotone`,
`lineal-color`, `flat-color`, `gradient-color`) < user registry
(`~/.config/iconpilot/styles.toml`) < pack-local (`pack.json.styles`).

## Usage

```bash
iconpilot new <pack-dir>               # LLM designer drafts spec + briefs (todo-only)
iconpilot add <pack> hut --brief "…"
iconpilot styles [--pack P]            # inspect the style registry
iconpilot gate hut.svg --pack P [--variant mono]   # deterministic check on any SVG
iconpilot round <pack>                 # generate → gate → screen → review
iconpilot review <pack>                # review page (live per-icon editing)
iconpilot decide <pack> --text 'hut: a2 ok · b1 no · more 2'
iconpilot export <pack> --target maplibre --out <dir>
```

## Rules of the road

- `pack.json` is written only by the CLI and the review server (atomic writes +
  lock; decisions flow through `decisions.json` → `decide`, never straight to
  status). Never edit it by hand.
- `icons/*.svg` are yours to edit between rounds — the gate re-validates; the
  next round refines from your edited file. Approval is always a human action.
- LLMs never self-certify; the deterministic gate is the only certifier.
  LLM-created packs are todo-only by validation.
- Style thresholds (node budgets, gaps, stroke) come from the registry — LLMs
  reference styles, they never author thresholds.

## Development

```bash
uv sync && uv run pytest
```

## Roadmap

1. ✅ Schema v2 + styles registry + semantic validator + gate slice
2. ✅ Full gate (render via resvg-py at style sizes, ink checks, phash; `iconpilot similar`)
3. Model routing + `round` + `new` (todo-only) + `decide`
4. Review server (locking, optimistic concurrency) + live per-icon editing
5. Hand-tweak loop materialization (shared with links/export)
6. Export targets (svg, sprite-svg, maplibre, iconify)
7. Optional: embedded gate-constrained SVG editor (custom, mirrors gate rules)

## License

MIT
