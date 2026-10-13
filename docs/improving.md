# Improving existing packs

Packs often start as an **imported baseline** — icons already shipped
elsewhere (a sprite dir, a previous project, a PR). The import pattern:

```json
"variants": {
  "mono": { "style": "import-mono", "status": "approved",
            "chosen": { "run": "pr314", "variant": "source" } }
}
```

with transitional styles (`import-*`) whose notes say what to converge toward,
and `provenance.source` recording where the baseline came from.

## The improve loop

1. **Reopen exactly what you want to improve** — approval is only undone
   explicitly:

   ```bash
   iconpilot decide <pack> --text 'hut/mono: restart "align to new style family"'
   ```

   The variant goes back to `todo`; the current SVG stays in `icons/` as the
   refinement base; comments and rejected ideas carry forward.

2. **Point at a target style** — swap the transitional import style for a
   built-in (`mono-line`, `lineal-color`, …). Style references are structural
   metadata: edit them, then `iconpilot check`.

3. **Run normal rounds** — `context` now emits the target style's thresholds
   and vocabulary, plus approved siblings as references. Drafts evolve *from*
   the imported SVG, not from zero.

4. **Hand-tweaks count** — edit the SVG and re-gate; small fixes never need a
   round.

## Rules of thumb

- Never bulk-reopen: improve one variant at a time; the set stays shippable.
- The gate is informative on approved imports too — run it over `icons/` to
  get a work list of real inconsistencies (bbox overshoot, node counts,
  near-duplicates via `iconpilot similar`).
- Dependent variants (anchor/reference targets) go `stale` automatically when
  an approved target changes — let the state machine drive what needs a
  second look, not your memory.
