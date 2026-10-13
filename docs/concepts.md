# Concepts

## Packs

A pack is a directory with `pack.json` (schema v2) plus icon originals. The
pack is the unit of consistency: one grid, one stroke family, one style point
per variant. Consuming projects link a pack and export from it.

## Variants are siblings, not derivations

An icon has a `brief` (what it *is*), an optional `prompt` (composition
hints), an optional `main_color`, and independently authored **variants**:

```json
"hut": {
  "brief": "Alpine hut: steep roof, small door, no chimney",
  "main_color": "#346751",
  "variants": {
    "primitive": { "style": "primitive", "anchor": true },
    "mono":      { "style": "mono-line" },
    "color":     { "style": "lineal-color", "reference": "hut#mono" }
  }
}
```

A primitive is a redraw at lower detail — not a mono with fills flipped. A
color variant is a redraw at higher detail. Each variant has **its own
rounds, status, and decisions**.

### anchor and reference

- `anchor: true` — the family form baseline. Its approved SVG is injected
  into every sibling's drafting context.
- `reference: "<icon>#<variant>"` — an additional sibling to visually match.

Both are dependency edges: the pack loader verifies acyclicity, and when an
approved target changes, dependents become `stale` automatically.

### links

```json
"selfhut": { "variants": { "primitive": { "link": "hut#primitive" } } }
```

A variant-level alias: no own file, no own state — it inherits the master's
status and materializes at export under its own icon name. Links on non-mono
styles require equal `main_color` on both icons (linked paint must be sound).
`unlink` re-materializes a copy as `in_review` so it can diverge.

## Styles — one definition, two jobs

A style carries **gate thresholds** *and* **prompt vocabulary**:

| Axis | Values |
|---|---|
| construction | outline · solid · outline+fill · hand-drawn |
| color mode | mono · bicolor · color · gradient |
| weight | thin (1.5) · regular (2) · bold (2.5) |
| detail | low · medium · high → node budget, min gap |

Three tiers, highest wins: built-ins shipped with the tool (`primitive`,
`mono-line`, `mono-line-thin`, `mono-bold`, `filled`, `duotone`,
`lineal-color`, `flat-color`, `gradient-color`) < user registry
(`~/.config/iconpilot/styles.toml`) < pack-local (`pack.json.styles`).
Unknown style ids are load errors — register or fix, never invent.

## State machine

```
todo → drafting → in_review → approved (frozen)
                     │  ↑            │
                     └──┘ (keep)     └→ stale (a dependency changed)
         restart (explicit) → todo    reopen (explicit user action)
```

- Round state lives **per variant**; icon-level status is derived, never stored.
- `iconpilot decide` is the only writer of state transitions — from the review
  page or from compact text, the same code path.
- Approval is always the user's action. Packs created by an LLM
  (`provenance.created_by: "designer"`) must be todo-only — the validator
  enforces it.

## Two-layer output

| Layer | Path | Editable |
|---|---|---|
| Originals | `icons/<icon>/<variant>.svg` — readable source of truth | by hand, freely — the gate re-validates |
| Assets | `export/` — optimized SVG, sprites, Iconify JSON | never — always regenerated |

Kept/approved candidates materialize into `icons/` immediately, so the next
round (and your hand-tweaks) always start from the current best file.

## The write path

`pack.json` has exactly two sanctioned writers: the CLI and the review server
(atomic writes + advisory flock, monotonic `rev`). Decisions flow through
`decisions.json` → `decide`; live page editing patches per-icon fields only —
global spec numbers stay CLI-side so past gate results can't be silently
invalidated.
