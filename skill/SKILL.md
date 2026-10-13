---
name: iconpack
description: Design, review, and export consistent SVG icon packs via the iconpack CLI. Use when creating or extending an icon pack, running design rounds, applying review decisions, or exporting icons (SVG, MapLibre sprites, Iconify JSON) into a project. Covers the round → review → decide loop, compact decision text parsing, and pack exports.
---

# iconpack — agent instructions

`iconpack` is a multi-model pipeline: drafters generate SVG variants, deterministic
gates check them, a screener pre-ranks them, and **the user decides** every round.

## When to use

- The user wants to create or extend an icon pack ("design icons for X").
- A round has variants awaiting review, or the user pasted decision text.
- A project needs exported icons (MapLibre sprite, Iconify JSON, plain SVGs).
- The user hands you a hand-drawn SVG that must conform to a pack (`iconpack gate`).

## The loop

```
iconpack round <pack>          # generate → gate → screen → set review
iconpack review <pack>         # serve the review page (or --static)
<user decides>                 # page buttons OR compact text pasted here
iconpack decide <pack> --text "…"   # apply decisions
repeat until all icons approved
iconpack export <pack> --target <T> --out <DIR>
```

`<pack>` is a pack directory path (a folder containing `pack.json`).

## Compact decision text

When the review page is unreachable (`--static` fallback), the user pastes text like:

```
hut: a2 keep "thinner roof" · b1 no · more 2
lake: a1 ok
peak: * no · restart "too abstract"
```

Pass it **verbatim** to `iconpack decide <pack> --text`. Do not reformat or interpret
it yourself — the CLI is the only parser.

## Hard rules

- **Never edit `pack.json` or `icons/` by hand.** Only the CLI writes pack state.
- Never approve icons on the user's behalf; approval is always the user's action
  (page button or decision text).
- LLMs never self-certify gate results; only the deterministic gate does.
- Keep expensive-model usage to designer/reviewer/advisor roles; rounds with
  `--no-claude` run screener + user only (cheaper iterations).

## Escalation

When an icon has been fully rejected twice, or the user flags it, run the advisor
escalation path rather than re-rolling the same brief.

## Report back to the user

After each round: the review URL (or static file path), a round summary
(approved/kept/rejected per icon), and cost from `iconpack status <pack>`.
