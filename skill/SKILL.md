---
name: iconpilot
description: Design, review, and export consistent SVG icon packs with iconpilot — deterministic gates, pack state, review rounds, and exports (SVG, MapLibre sprites, Iconify JSON). The agent is the model layer; iconpilot never calls LLMs. Use when creating or extending an icon pack, drafting/gating variants, applying review decisions, or exporting icons into a project.
---

# iconpilot — agent instructions

`iconpilot` is **deterministic tooling + pack state**. You (the agent) are the
model layer: you draft variants, you screen renders, you run the loop. The CLI
provides the gate, the prompt context, similarity, the state machine, exports.
No API keys, no model config — use whatever models your harness offers.

Data model: icons have independent **variant siblings** (primitive/mono/color …)
each bound to a **style** from the registry; `anchor` = family form baseline,
`reference` = sibling to visually match, `link` = alias of another icon's
variant. Styles are three-tier (built-in < `~/.config/iconpilot/styles.toml` <
pack-local).

## The loop (you drive it)

```
1. CONTEXT   iconpilot context <pack> --icon hut --variant mono
             → deterministic brief + style + gate thresholds + anchor SVGs.
2. DRAFT     You (or a cheap subagent) write N candidate SVGs to
             <pack>/.runs/<round>/<variant>/<icon>/<cand>.svg (a1, a2, …).
             Follow the context exactly: style_words, avoid, node budget.
3. GATE      iconpilot gate <pack>/.runs/<round> --pack <pack>
             → <cand>.gate.json beside every SVG. Fix failures and re-gate
             until survivors pass. Never claim a pass the gate didn't make.
4. SCREEN    iconpilot contact-sheet <pack>/.runs/<round> --pack <pack>
             → one PNG. Attach it to a vision-capable subagent (or inspect
             yourself): score each candidate 0–10, one-line critique, rank.
             Also check family coherence against anchors.
5. DECIDE    The USER decides — review page, or compact text they paste:
             hut/mono: a2 keep "thinner roof" · b1 no · more 2
             → iconpilot decide <pack> --text "…" (verbatim; CLI is the
             only parser). Approval/keep materialize to icons/, dependents
             of changed anchors go stale automatically.
6. REPEAT    until every variant is approved; then export.
```

Round layout: `.runs/<round>/<variant>/<icon>/<cand>.svg` (r001, r002, …).

## Role mapping (harness-side, no config)

- **drafter** — cheapest capable model you can spawn (fast subagent); give it
  the `context` output verbatim.
- **screener** — any vision-capable model; it must see the contact sheet PNG.
- **reviewer/advisor** — your strongest model, on the whole contact sheet
  (set-level consistency) or for icons rejected twice.
- **designer** — you, when creating `pack.json` briefs; then validate with
  `iconpilot check <pack>`.

## Hard rules

- **Never edit `pack.json` by hand except briefs/prompts/main_color** — status,
  chosen, comments, requests are written only by `iconpilot decide`. The review
  server shares this contract.
- **`icons/*.svg` are hand-editable between rounds** (by you or the user):
  edit, then `iconpilot gate <file> --pack <pack>` re-validates; the next
  round refines from the edited file.
- Approval is always the user's action. LLMs never self-certify — the
  deterministic gate is the only certifier.
- Style thresholds (node budgets, gaps, stroke) come from the registry —
  reference styles, never invent thresholds.
- Near-duplicates: `iconpilot similar <file> --pack <pack>` — suggest links
  (`{"link": "hut#primitive"}`) only for user-confirmed intent, never auto.

## Report back to the user

After each round: candidates that passed the gate, screener ranking, the
contact-sheet path (or review URL), and what `decide` changed.
