# SVG icon craft — the corpus

Read before drafting any variant; `iconpilot context` tells you which numbers
apply (they override anything here — this file gives typical defaults).

## 1. Output contract

Every icon is exactly this shape (no `width`/`height`, no `xmlns` needed for
candidates, presentation attrs on the root):

```svg
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
  <!-- only allowed elements; absolute coords; no transforms, ids, or style attrs -->
</svg>
```

## 2. Tier table (structural; `context` names your style + its numbers)

| Tier | Shapes | Node budget | Min gap | Stroke |
|---|---|---|---|---|
| primitive | 2–3, silhouette only | ~14 | 2.5 | none (solid fill) |
| mono | ≤ ~8 | ~40 | 1.5 | 2px, round caps/joins |
| color | more detail, ≤ 3 colors + dark stroke | ~60 | 1.25 | 2px outline + flat fills |

## 3. The gap rule (gate-enforced — get this right first)

Strokes either **touch cleanly** (gap 0, shared point/segment) or **clear the
style's min_gap**. Never land in the near-miss band between (e.g. 0.5–1.5 for
mono): the gate rejects it. If two strokes almost meet, join them or open them.

## 4. Grid, live box, keylines

- Half-unit grid (0.5 steps); snap anchors and control points to it (checked).
- **Live box: 2→22** on the 24 canvas — every coordinate stays inside (checked,
  bezier control points included).
- Keylines at *equal perceived size inside the box*: circle Ø20, square 18×18,
  landscape 20×16, portrait 16×20. A circle must span the box to look as big
  as the square sitting inside it.

## 5. Stroke discipline

- One stroke width per icon, always. Never widen "just this segment".
- Round caps/joins unless the style says square; end strokes on the grid,
  don't let them dangle.
- Inside corners: inner radius = outer radius − stroke width.

## 6. Small-size legibility (the 16px test)

- Minimum feature 2px at 24 viewBox; any enclosed counter must survive 16px —
  if it would close up, remove it (that detail belongs to the color tier).
- Fewer shapes = smaller icon. That's what the primitive tier is for.

## 7. Matching an anchor or reference SVG

Mechanical, not artistic: open the anchor SVG and **copy its `stroke-width`,
`stroke-linecap`, `stroke-linejoin` verbatim**; reuse its corner-radius habit;
place your icon's visual mass where the anchor's mass sits (same center, same
weight distribution). Match first, then differentiate on the brief.

## 8. Form & metaphor

- Build from geometric primitives; one flat plane — no perspective, 3D,
  shadows, or gradients (unless the style is `gradient-color`).
- One concept per icon. **Silhouette first**: the black-fill outline must read
  alone; if the filled silhouette is ambiguous, the icon fails small sizes.
- Keep gaps between repeated elements equal (door slats, windows, bars).

## 9. Color tiers

- `main_color` dominates ~60%, one support tone ~30%, accent ≤10%.
- Color adds information (sky, wood, terrain), never re-outlines what mono
  already carries. Duotone: one accent layer at 40–50% opacity.

## 10. DO and DON'T

DO — passes the gate and reads as a hut when filled black:

```svg
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 11 L12 4 L20 11"/>   <!-- roof: apex y=4, eaves x=4/20 -->
  <path d="M6 11 V20 H18 V11"/>    <!-- walls: base on y=20 -->
</svg>
```

DON'T — coordinates at 1/23 (outside the live box), hairline stroke, dot
smaller than the stroke (vanishes at 16px):

```svg
<svg viewBox="0 0 24 24">
  <path d="M1 23 L12 1 L23 23 Z" stroke-width="1"/>
  <circle cx="12" cy="14" r="0.5"/>
</svg>
```

## 11. Pre-submit checklist (run it before you hand the SVG to the gate)

- [ ] viewBox `0 0 24 24`, presentation attrs on the root
- [ ] every coordinate inside 2→22, on the 0.5 grid
- [ ] one stroke width, caps/joins match the style
- [ ] every stroke pair touches or clears min_gap (no near-misses)
- [ ] silhouette reads when filled black; counters survive 16px
- [ ] no transforms, ids, classes, inline styles, text
