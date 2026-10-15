# DESIGN.md — iconpilot review page

Register: product. Strategy: **restrained** — tinted neutrals, one green
accent ≤10% of surface, amber reserved for agent/warning signals.

## Theme rationale
Light is the default: designers judge icons against the light surfaces they
ship to (docs, apps, paper), usually in daylight. Dark is a first-class
alternative for night sessions — same layout, token-swapped, never an
afterthought. Theme follows `prefers-color-scheme`, user override persists.

## Color tokens (OKLCH)
Neutrals tinted toward hue 150 (calm green-gray, matches the product world).

| Token | Light | Dark | Use |
|---|---|---|---|
| --bg | oklch(0.975 0.004 150) | oklch(0.165 0.008 155) | page canvas |
| --card | oklch(0.998 0.002 150) | oklch(0.205 0.009 155) | cards, dialogs, header |
| --card-2 | oklch(0.955 0.005 150) | oklch(0.245 0.010 155) | nested strips, chat history |
| --line | oklch(0.900 0.006 150) | oklch(0.300 0.012 155) | hairlines, input borders |
| --ink | oklch(0.240 0.012 155) | oklch(0.930 0.008 150) | primary text |
| --muted | oklch(0.520 0.015 155) | oklch(0.700 0.012 150) | secondary text |
| --accent | oklch(0.520 0.130 152) | oklch(0.720 0.140 152) | primary actions, approved |
| --accent-ink | oklch(0.995 0.002 150) | oklch(0.140 0.020 152) | text on accent |
| --warn | oklch(0.680 0.140 70) | oklch(0.780 0.130 75) | agent comments, new, danger-armed |
| --focus | oklch(0.620 0.110 152) | oklch(0.760 0.120 152) | focus rings |

Icon preview stages keep literal backgrounds (paper #f6f9f7, night #22292e)
in both themes: they are artifact surfaces, not UI chrome.

## Typography
System stack (no webfonts, no build): `system-ui, -apple-system, "Segoe UI", sans-serif`.
Scale: 0.75 (meta) / 0.85 (body-small) / 0.95 (body) / 1.15 (h3) / 1.35 (h2).
Weight contrast over color contrast: 600 headings, 400 body, 500 labels.

## Components
- **Inputs** (input/select/textarea): height 32px (40 mobile), 1px --line
  border, --card bg, radius 8px, 0 0 0 2px focus ring in --focus. Textarea
  min-height 3 rows. Consistent horizontal padding 10px.
- **Buttons**: primary (accent bg, accent-ink text), subtle (transparent,
  hairline border), iconbtn (28px square). Armed destructive states use
  --warn outline, never filled red.
- **Chips**: 0.75rem, tinted backgrounds via color-mix, no borders.
- **Dialogs**: solid --card surface, radius 14px, shadow oklch(0 0 0 / 0.18),
  max-width 520px, overlay oklch(0 0 0 / 0.45).
- **Cards (icon candidates)**: --card, hairline border, 12px radius; the
  64px thumb is the visual anchor, name + rating below.
- **Chat (feedback)**: bubbles full-width rows, author chip + text + relative
  time; agent rows tinted --warn 12%, user rows --card-2.

## Motion
None beyond 120ms ease-out on hover/focus color+shadow. No layout animation.

## Accessibility
Focus visible everywhere (2px ring), 44px touch targets on mobile, contrast
≥4.5 for text, icons have title text, aria-labels on icon-only buttons.
