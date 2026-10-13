# SVG icon craft — the corpus

Distilled design knowledge every drafter (human or model) must apply. The
gate enforces the numbers; this guide carries the judgment. Read before
drafting any variant; `iconpilot context` tells you which slice applies.

## Grid & metrics (24px default)

- ViewBox `0 0 24 24`; **live area = 20×20** centered (2px padding). Every
  drawn coordinate stays inside it — geometry checked by the gate.
- Design on the **half-unit grid** (0.5 steps); snap start/end points of
  strokes to whole units where possible.
- Keyline shapes: square 20×20, circle Ø22 (optical overshoot), landscape
  20×16, portrait 16×20. Different silhouettes at *equal perceived size* —
  a circle must be bigger than the square to look equal.

## Stroke discipline

- One stroke width per pack (from the style). Never mix weights.
- Round caps/joins unless the style says square. Terminals are design
  decisions: end strokes cleanly on the grid, don't let them dangle.
- Diagonals read *thicker* than orthogonal strokes at the same width —
  compensate optically, never by changing the width.
- Inside corners: inner radius = outer radius − stroke width, so the gap
  looks uniform.

## Small-size legibility (the 16px test)

- Minimum feature: 2px at 24px viewBox. Minimum gap between strokes: the
  style's `min_gap` (default 1.5; primitives 2.5).
- Any enclosed counter must survive 16px: if it would close up, remove it —
  that detail belongs in the color variant, not mono.
- Fewer shapes = smaller icon. That's what the **primitive** tier is for:
  2–3 shapes, generous gaps, silhouette only.

## Form & metaphor

- Build from geometric primitives (rects, circles, arcs at grid points).
- One flat plane: no perspective, no 3D, no cast shadows, no gradients
  (unless the style is `gradient-color`).
- One concept per icon. If you need two metaphors, the icon is two icons.
- **Silhouette first**: the black-fill outline must read alone. If the
  filled silhouette is ambiguous, the icon fails at small sizes regardless
  of detail.
- Match the family: when an `anchor` SVG is given, echo its mass, angle
  vocabulary, and terminal style; same for `reference` siblings.
- Negative space is a shape: rhythm between forms matters as much as the
  forms. Keep spacing consistent across the set.

## Color variants (`lineal-color`, `flat-color`, `duotone`)

- Dark outer stroke stays (lineal-color); fills are flat, pack-palette only.
- `main_color` dominates ~60%, one supporting tone ~30%, accent ≤10%.
- Never re-outline details that mono already carries — color adds
  information (sky, wood, terrain), not noise.
- Duotone: accent layer at 40–50% opacity of the primary, one layer only.

## Anti-patterns (automatic rejects)

- Hairline strokes, mixed caps, floating stroke fragments.
- Literal metaphors (a photograph of the thing, translated to paths).
- Perspective, gradients in mono, drop shadows, <text>, transforms.
- Detail soup at 16px; interiors smaller than the stroke width.
- Inventing new stroke widths "just this once".
