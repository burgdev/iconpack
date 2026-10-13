# iconpilot

Deterministic tooling + state for designing **consistent SVG icon packs**.

The AI agent running the skill (Claude, pi, any harness) is the *model layer* —
it drafts variants, screens renders, and drives the loop. iconpilot never
calls an LLM: no API keys, no model adapters. It validates, gates, hashes,
composes contact sheets, tracks pack state, and exports.

## Why

Icon-generation services produce one-off pictures without guarantees. For a
production icon *pack* you need the opposite: a fixed grid, uniform stroke,
lint-clean sources, sprite-ready exports, and a human deciding every round.
iconpilot makes the machine do the checking:

- **Deterministic gate** — parse, lint, geometry, render, similarity; LLMs
  never self-certify.
- **Human rounds** — variants narrow 4 → 2 → 1; you approve/keep/reject via a
  review page or compact decision text.
- **Pack state** — briefs, variants, styles, links, anchors, and statuses in
  one validated `pack.json`; exports are always regenerated from source.

## The one-minute tour

```bash
iconpilot new ~/packs/alpine
iconpilot add ~/packs/alpine hut --brief "Alpine hut: steep roof, small door"
iconpilot check ~/packs/alpine
iconpilot context ~/packs/alpine --icon hut --variant mono   # drafting contract
iconpilot gate ~/packs/alpine/.runs/r001 --pack ~/packs/alpine
iconpilot decide ~/packs/alpine --text 'hut/mono: a1 ok'
iconpilot export ~/packs/alpine --target maplibre --out sprites/
```

## Where to go next

- [Quickstart](quickstart.md) — install and run your first gated round
- [Concepts](concepts.md) — variants, styles, links, anchors, state
- [The agent loop](loop.md) — how the skill drives drafting and review
- [Library API](library.md) — embed iconpilot in your build (Django, deploy)
