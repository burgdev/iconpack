---
name: iconpilot
description: Design, review, and export consistent SVG icon packs via the iconpilot CLI. Use when creating or extending an icon pack, running design rounds, applying review decisions, or exporting icons (SVG, MapLibre sprites, Iconify JSON) into a project. Covers the round → review → decide loop, compact decision text parsing, and pack exports.
---

# iconpilot — agent instructions

`iconpilot` is a multi-model pipeline: drafters generate SVG variants, deterministic
gates check them, a screener pre-ranks them, and **the user decides** every round.

Data model: icons have independent **variant siblings** (primitive/mono/color …)
each bound to a **style** from the registry; one variant may be the **anchor**
(form baseline for its siblings), `reference` adds a sibling to visually match,
and `link` aliases another icon's variant (no own file/state). Styles are
three-tier (built-in < `~/.config/iconpilot/styles.toml` < pack-local).

## When to use

- The user wants to create or extend an icon pack ("design icons for X").
- A round has variants awaiting review, or the user pasted decision text.
- A project needs exported icons (MapLibre sprite, Iconify JSON, plain SVGs).
- The user hands you a hand-drawn SVG that must conform to a pack (`iconpilot gate`).

## The loop

```
iconpilot round <pack>          # generate → gate → screen → set review
iconpilot review <pack>         # serve the review page (or --static)
<user decides>                 # page buttons OR compact text pasted here
iconpilot decide <pack> --text "…"   # apply decisions
repeat until all icons approved
iconpilot export <pack> --target <T> --out <DIR>
```

`<pack>` is a pack directory path (a folder containing `pack.json`).

## Compact decision text

When the review page is unreachable (`--static` fallback), the user pastes text like:

```
hut: a2 keep "thinner roof" · b1 no · more 2
lake: a1 ok
peak: * no · restart "too abstract"
```

Pass it **verbatim** to `iconpilot decide <pack> --text`. Do not reformat or interpret
it yourself — the CLI is the only parser.

## Hard rules

- **Never edit `pack.json` by hand.** Only the CLI and the review server write it
  (atomic + locked; keep/reject decisions flow through `decisions.json` → `decide`).
- **`icons/*.svg` are hand-editable between rounds** — that is the supported
  tweak loop: keep → edit → gate re-validates → next round refines from the
  edited file. Run `iconpilot gate <file> --pack <pack>` after editing.
- Never approve icons on the user's behalf; approval is always the user's action
  (page button or decision text). LLM-created packs are todo-only, enforced by
  the semantic validator.
- LLMs never self-certify gate results; only the deterministic gate does.
- LLMs reference registry styles; they never author gate thresholds
  (node budgets, gaps, stroke widths).
- Keep expensive-model usage to designer/reviewer/advisor roles; rounds with
  `--no-claude` run screener + user only (cheaper iterations).

## Escalation

When an icon has been fully rejected twice, or the user flags it, run the advisor
escalation path rather than re-rolling the same brief.

## Report back to the user

After each round: the review URL (or static file path), a round summary
(approved/kept/rejected per icon), and cost from `iconpilot status <pack>`.
