# CLI reference

All commands accept `<pack>` as a pack directory or a `pack.json` path.
Everything is non-interactive by default; JSON where useful.

## Pack lifecycle

| Command | Purpose |
|---|---|
| `iconpilot new <dir> [--name N] [--author user|designer]` | Scaffold spec + empty registry; designer packs are todo-only |
| `iconpilot add <pack> <icon> --brief "…" [--variant mono:mono-line …]` | Add an icon with authored variants (todo); repeatable `--variant name:style` |
| `iconpilot check <pack>` | Full validation: JSON schema, semantics, style resolution, links, DAG |
| `iconpilot status <pack>` | Per-variant states, links, requests, rev, rounds, `✎edited` markers |

## The loop

| Command | Purpose |
|---|---|
| `iconpilot context <pack> --icon I --variant V [--json]` | Deterministic drafting contract (brief, style, gate thresholds, anchor/reference SVGs) |
| `iconpilot gate <run-dir> --pack P` | Batch-gate every candidate under `<run-dir>/<variant>/<icon>/<cand>.svg`; writes `<cand>.gate.json` beside each |
| `iconpilot gate <file>.svg --pack P [--variant V]` | Gate a single SVG (hand tweaks, debugging) |
| `iconpilot contact-sheet <dir> --pack P [--out F]` | One PNG grid of candidates or approved icons |
| `iconpilot similar <file> --pack P [--threshold 8]` | Rank pack SVGs by phash hamming distance; ≤ threshold flagged as link candidates |
| `iconpilot decide <pack> --text "…" \| --file F [--round R]` | Apply decisions (see [the loop](loop.md#decision-grammar)); the only writer of state transitions |

## Review page

| Command | Purpose |
|---|---|
| `iconpilot review <pack> [--host H] [--port P]` | Live review server: candidate ok/keep/no, decision text, per-icon editing (brief/prompt/main_color), renders, rev polling |

## Export & registry

| Command | Purpose |
|---|---|
| `iconpilot export <pack> --target T --out DIR` | `svg` · `sprite-svg` · `maplibre` (@1x/@2x PNG+JSON) · `iconify` (aliases for links) |
| `iconpilot styles [--pack P]` | Inspect the style registry: built-ins, user config, pack-local |
| `iconpilot install-skill [--force]` | Symlink the skill (SKILL.md + craft.md) into `~/.agents/skills/iconpilot` (+ `~/.claude/skills`) |

## Exit codes

`0` success · `1` gate/validation failure · `2` usage/parse error · `423` pack
locked by another writer (server).
