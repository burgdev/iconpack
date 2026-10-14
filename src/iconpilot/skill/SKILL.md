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

**Craft:** before drafting any variant, read `craft.md` (next to this file) —
grid, stroke discipline, 16px legibility, silhouette-first, color ratios.
The gate enforces the numbers; craft.md carries the judgment.

## Notes hierarchy (read before every draft)

Notes flow into `context` automatically — but know the layers:
1. **Pack note** (`pack.note`): standing orders for the whole pack
2. **Icon note** (`icons.<id>.note`): per-icon guidance
3. **Variant note** (`icons.<id>.variants.<v>.note`): most specific — wins for that variant
4. **Apply-time instructions** (in `decisions.json.instructions`): one-shot, for the next round only

Never override a note. If two notes conflict, the more specific one wins.

## Re-read after changes

The review page bumps `rev` on every write (notes, briefs, styles, decisions).
When `iconpilot wait` returns, ALWAYS:
1. `iconpilot status <pack>` — see what changed (`✎edited` = hand-edited SVGs)
2. `iconpilot context <pack> --icon <id> --variant <v>` — re-read for each variant you'll draft;
   the context includes any new notes and reflects the CURRENT `icons/` file
3. If an SVG was hand-edited (`✎edited`), open `icons/<icon>/<variant>.svg` and READ it —
   the user's changes are the new refinement base, not the old candidate

## SVG paths (for debugging)

`iconpilot status` and the review page (⧉ button) give the absolute file path for any SVG.
Use it to open the file in an editor or examine the raw markup when the gate reports issues.

## Who writes what (the write contract)

- `pack.json` state (status/chosen/comments/requests/ratings/hashes) is written
  **only by `iconpilot decide`** — you pass the user's decision text verbatim.
  Never construct or patch state JSON yourself; use the review server's API for
  brief/prompt/main_color/style-ref edits.
- You **do** write directly: candidate SVGs into `.runs/…` (that is drafting)
  and the `.runs/.ai-status` signal file.
- Rounds never start themselves. If no variant is `todo`/`stale` but the gate
  has findings on approved icons, **propose an improvement round** (list the
  findings, suggest which variant to reopen) and wait for the user's go —
  reopening is `decide … restart`, a user decision.

## Finding the pack (multiple packs supported)

`iconpilot packs` lists every discovered pack (roots from
`~/.config/iconpilot/config.toml` `[packs].dirs`, plus `~/iconpacks`). When the
user doesn't say which pack: list the candidates and **ask** — never guess.
If a repo contains an `iconpacks/` dir, that's a strong hint; still confirm
when more than one pack exists.

## DESIGN.md (design system context)

Before drafting for a pack: if `pack.json` sets `inherits.design_md`, read
that file (context output points to it). If not set, **look for a `DESIGN.md`
in the pack dir and its repo root anyway** — colors, corner radii, mood and
anti-references from the design system feed the drafter's prompt (pack spec
and style numbers always win over DESIGN.md prose).

## The loop (you drive it)

```
1. CONTEXT   iconpilot context <pack> --icon hut --variant mono
             → deterministic brief + style + gate thresholds + anchor SVGs.
2. DRAFT     You (or a cheap subagent) write N candidate SVGs to
             <pack>/.runs/<round>/<variant>/<icon>/<cand>.svg (a1, a2, …).
             Follow the context exactly: style_words, avoid, node budget.
3. GATE      iconpilot gate <pack>/.runs/<round> --pack <pack>
             → <cand>.gate.json beside every SVG. Fix failures and re-gate,
             but bounded: after ~2 failed fix attempts on a candidate, drop
             it and draft fresh from the gate feedback. If ALL candidates
             fail, go back to DRAFT with the failure reasons as constraints —
             never re-gate the same geometry forever, and never screen an
             empty round. Never claim a pass the gate didn't make.
4. SCREEN    iconpilot contact-sheet <pack>/.runs/<round> --pack <pack>
             → one PNG. Attach it to a vision-capable subagent (or inspect
             yourself): score each candidate 0–10, one-line critique, rank.
             Ranking orders candidates FOR THE USER — it never selects or
             approves; only `decide` (step 5) changes state.
             Also check family coherence against anchors.
5. DECIDE    Announce, then hand over, then block.
             BEFORE waiting you MUST tell the user (chat message):
               - a 1–3 line round summary: what was drafted, gate results,
                 the screener's top pick
               - the review URL as a markdown link, e.g.
                 [iconpilot review — accommodation](http://home:8765)
               Build the URL with tailscale when active (works from any device):
                 HOST=$(tailscale status --json 2>/dev/null \
                        | jq -r '.Self.DNSName // empty' | sed 's/\.$//')
                 URL="http://${HOST:-127.0.0.1}:8765"
               Start the server if not running (bind all interfaces):
                 iconpilot review <pack> --host 0.0.0.0 &
             THEN block:
             iconpilot wait <pack>          # returns when they Apply
             The USER decides — page buttons or compact text they paste:
             hut/mono: a2 keep "thinner roof" · b1 rate 7 · more 2
             → iconpilot decide <pack> --text "…" (verbatim; CLI is the
             only parser). Approval/keep materialize to icons/, dependents
             of changed anchors go stale automatically.
6. REPEAT    When `wait` returns:
             a) read .runs/<round>/decisions.json — applied items + instructions
             b) `iconpilot status <pack>` — see ✎edited markers and new notes
             c) re-run `context` for every variant you'll draft next
             d) act on requests (`more N`, `like`, `restart`) and continue    `iconpilot status <pack>` shows what's outstanding (todo,
             in_review, `stale` — stale variants must be re-run; `✎edited`
             means the icons/ file changed after approval). Loop until every
             variant is approved; then export.
```

Round layout: `.runs/<round>/<variant>/<icon>/<cand>.svg` (r001, r002, …).

## Role mapping (harness-side)

The tool never calls models — the harness picks them. For consistent routing
across sessions, an optional **advisory** mapping lives at
`~/.config/iconpilot/models.toml`; if present, honor it when spawning:

```toml
[roles]
drafter  = "cheapest capable model"   # drafts candidates; gets `context` verbatim
screener = "any vision model"         # must see the contact-sheet PNG
reviewer = "your strongest model"     # set-level consistency on the sheet
advisor  = "your strongest model"     # escalation only (twice-rejected icons)
```

Without a config: drafter/screener = cheapest capable, reviewer/advisor =
your strongest. **designer** is you — validate briefs with `iconpilot check`.

## Improving an existing pack (imported baseline)

Packs often start as an import of already-shipped icons (`status: approved`,
`chosen: {run: "<import>", variant: "source"}`, import styles marked
*transitional*). To improve over that baseline:

1. **Reopen what you want to improve** — approval is only undone explicitly:
   `iconpilot decide <pack> --text 'hut/mono: restart "align to new style family"'`
   → the variant goes back to `todo`; the current SVG stays in `icons/` as the
   starting point, rejected ideas and comments carry forward.
2. **Set the target style** — swap the variant's transitional import style for
   a built-in (edit `pack.json` styles refs — allowed, they're structural
   metadata — then `iconpilot check`).
3. **Run normal rounds** — `context` now emits the target style's gate
   thresholds and vocabulary; approved siblings arrive as references. The
   imported SVG is the refinement base, so drafts evolve from it, not from
   zero.
4. **Hand-tweaks count too** — edit `icons/<icon>/<variant>.svg` directly and
   re-gate; small fixes never need a full round.

Never bulk-reopen: improve one variant at a time; the set stays shippable.

## Signal your progress (the review page shows it)

While working a pack, keep the review page informed — it polls
`.runs/.ai-status` and shows a working/ready banner:

```bash
echo "drafting hut/mono — 4 candidates" > <pack>/.runs/.ai-status
# ...draft + gate...
echo "screening r001" >> <pack>/.runs/.ai-status   # overwrite, keep it one line
# when candidates are gated and the sheet is ready:
rm <pack>/.runs/.ai-status    # page switches to 'ready for decision'
```

Update it at every loop step (drafting → gating → screening); remove it when
you hand over for decisions.

## Failure paths

- **Pack locked** (`pack is locked` / HTTP 423): another writer (review
  server, concurrent decide) holds the flock. Wait and retry — never delete
  the lock file or force a write.
- **No candidates survive the gate**: return to DRAFT; feed every gate error
  into the next drafting prompt as hard constraints.
- **Stale variants**: a dependency changed (or was hand-edited) after
  approval — `status` lists them; re-run their rounds before exporting.
- **Decisions rejected** (`decide` exits 2): the error lists every problem;
  fix the text or run `iconpilot check` to see pack-level issues.

## Hard rules

- **Never edit `pack.json` by hand except briefs, prompts, main_color, and a
  variant's style ref** — status, chosen, comments, requests, and links are
  written only by `iconpilot decide`. After any hand edit: `iconpilot check <pack>`.
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
