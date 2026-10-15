# iconpilot review page — PRODUCT.md

## Product purpose
A single-page review tool where a human designer rates, comments on, and
decides AI-drafted SVG icon candidates, round by round, while an agent drafts
the next round from the same shared state. It is the human half of an
agent+human design loop; the deterministic gate is the only certifier.

## Users
- **Tobias**, designer-develop: reviews candidate grids daily, rates with the
  keyboard (1/2/3, arrows), writes per-round feedback, promotes standing rules.
  Uses light mode by day; occasionally dark at night. Works on a laptop, often
  with the page open on a second screen next to an editor.
- **The drafting agent** (LLM): reads the same pack state, drafts candidates,
  leaves agent-authored feedback comments. Never touches the page directly.

## Register
product — the design serves fast, confident decisions. Not a marketing surface.

## Tone
Calm, precise, tool-like. Dense but quiet: many candidates on screen, zero
decoration. The icons are the color; the chrome recedes.

## Strategic principles
1. Candidates are the hero — chrome must never out-visualize the icon grid.
2. Keyboard speed: every decision reachable without the mouse.
3. State must be legible: open vs locked, live vs history, user vs agent
   comments — always visible, never guessed.
4. Round history is sacred: nothing is deleted, everything is reachable.
5. No build step: Vue 3 vendored, one HTML page, stdlib server. Design system
   is hand-rolled CSS tokens.

## Anti-references
- Dashboard/SaaS admin templates (shadcn-gray, hero metrics).
- Dribbble icon-showcase prettiness over legibility.
- Emoji as UI icons (they leak the OS locale and look casual).

## Surfaces
One page: header (round switcher, theme, feedback, actions), candidate groups
per icon (variant sub-groups), decision composer, icons registry, round
history. Dialogs: rating sheet, feedback chat, compare, settings.
