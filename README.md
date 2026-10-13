# iconpilot

Multi-model pipeline for designing consistent SVG icon packs: cheap models draft
variants, deterministic tools gate them, and you decide each round in a review page.

**Status:** 0.0.1 (unreleased) — gate, agent loop (context/decide), review
server, and all four export targets are implemented and tested; MCP, `--static`
page fallback, and the embedded editor are future work.

## Install

```bash
uv tool install iconpilot             # from PyPI (once published)
uv tool install --from . iconpilot    # from a checkout
iconpilot install-skill               # symlink skill into ~/.agents/skills/ (+ ~/.claude/skills/)
```

## Concepts

**Agent-driven, not standalone**: the AI running this skill (Claude, pi, …) is
the model layer — drafting, screening, reviewing. iconpilot is deterministic
tooling + state: no API keys, no model adapters. The CLI validates, gates,
hashes, composes, and applies decisions.

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
iconpilot new <pack-dir>               # scaffold (agent fills briefs, then check)
iconpilot check <pack>                 # schema + semantic validation
iconpilot context <pack> --icon hut --variant mono   # drafting contract
iconpilot gate <run-dir> --pack P      # batch gate (writes .gate.json per candidate)
iconpilot gate hut.svg --pack P        # gate any single SVG (hand tweaks)
iconpilot contact-sheet <run-dir> --pack P           # one PNG for screening
iconpilot similar <file> --pack P      # near-duplicates → link suggestions
iconpilot decide <pack> --text 'hut/mono: a2 ok · b1 no · more 2'
iconpilot export <pack> --target maplibre --out <dir>
```

Rounds live at `<pack>/.runs/<round>/<variant>/<icon>/<cand>.svg`.

## Rules of the road

- `pack.json` is written only by the CLI and the review server (flock-serialized atomic writes; decisions flow through `decisions.json` →
  `decide`, never straight to status). Never edit it by hand.
- `icons/*.svg` are yours to edit between rounds — the gate re-validates; the
  next round refines from your edited file. Approval is always a human action.
- LLMs never self-certify; the deterministic gate is the only certifier.
  LLM-created packs are todo-only by validation.
- Style thresholds (node budgets, gaps, stroke) come from the registry — LLMs
  reference styles, they never author thresholds.

## Development

```bash
uv sync --all-groups
just check          # ruff + format + ty + pytest
just docs-serve     # live docs preview
```

## Roadmap

1. ✅ Schema v2 + styles registry + semantic validator + gate slice
2. ✅ Full gate (resvg renders, ink checks, phash) + `similar`
3. ✅ Agent-loop plumbing: `check`, `context`, batch gate, `contact-sheet`,
   `decide` (state machine, materialization, staleness)
4. Review server (locking, optimistic concurrency) + live per-icon editing
5. Export targets (svg, sprite-svg, maplibre, iconify) + shared materialization
6. Optional: embedded gate-constrained SVG editor (custom, mirrors gate rules)

## License

MIT

## Documentation

```bash
uv run --group docs zensical serve   # live preview at localhost:8000
uv run --group docs zensical build   # static site → site/
```

Docs live in `docs/` (zensical.toml + Markdown). Audience split: `docs/` is
for humans; `src/iconpilot/skill/` (SKILL.md + craft.md) is for agents.
