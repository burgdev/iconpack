# iconpilot — quick reference

```
context → draft → gate --fix → step → wait → read decisions → repeat → export
```

| Step | Command | What |
|------|---------|------|
| Context | `iconpilot context <pack> --icon <id> --variant <v>` | Full drafting contract |
| Draft | Write SVGs to `.runs/<round>/<variant>/<icon>/<cand>.svg` | You or a subagent |
| Gate | `iconpilot gate <pack>/.runs/<round> --pack <pack>` | Deterministic check (`--fix` for single SVG only) |
| Step | `iconpilot step <pack>` | Gate + contact-sheet + status in one |
| Wait | `iconpilot wait <pack>` | Blocks until user applies |
| Status | `iconpilot status <pack>` | States, ✎edited, stale, notes |
| Decide | `iconpilot decide <pack> --text "..."` | Only YOU pass user text through |
| Export | `iconpilot export <pack> --target <T> --out <D>` | svg/maplibre/iconify |
| Packs | `iconpilot packs` | List all; ask user if ambiguous |

**Hard rules**: never edit pack.json state by hand · approval is always the user's ·
gate is the only certifier · notes (pack > icon > variant) are standing orders.

---
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
3b. VERIFY   Visual check (see Subagent drafting protocol): render survivors,
             inspect at 16px/24px/48px, score 0-10, discard < 4.
             Only verified candidates proceed to screening.
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
6. LEARN     After each round, before repeating: analyze which candidates
             scored highest and lowest. If a pattern emerges (e.g. "icons with
             thinner strokes consistently score 8+") suggest adding it to the
             pack's style_words via the review page. If a pattern fails
             consistently, suggest adding it to avoid. The user confirms —
             style evolution is a human decision, but you propose.
6a. TRACK    Record round costs in .runs/<round>/round.json:
             {"round": "r001", "models_used": {"drafter": "glm-5.3", ...},
              "candidates_generated": 4, "gate_fixes": 2,
              "estimated_cost_usd": 0.05}
             Update after each phase (draft/gate/fix/screen).
6b. REPEAT   When `wait` returns:
             a) read .runs/<round>/decisions.json — applied items + instructions
             b) `iconpilot status <pack>` — see ✎edited markers and new notes
             c) re-run `context` for every variant you'll draft next
             d) act on requests (`more N`, `like`, `restart`) and continue    `iconpilot status <pack>` shows what's outstanding (todo,
             in_review, `stale` — stale variants must be re-run; `✎edited`
             means the icons/ file changed after approval). Loop until every
             variant is approved; then export.
```

Round layout: `.runs/<round>/<variant>/<icon>/<cand>.svg` (r001, r002, …).

## Feedback — the per-round todo list

Feedback items are per-round comments (yours AND the user's) at three scopes:
pack, icon, variant. They guide exactly ONE draft, then die with their round
(history keeps them in `.runs/<round>/feedback.json`).

    iconpilot feedback <pack>                        # list live items
    iconpilot feedback <pack> --add "door too small" --icon hut --variant mono
    iconpilot feedback <pack> --resolve <id>         # addressed / done

Rules:
- After drafting, ADD your own comments (author=agent by default): what you
  tried, what you could not achieve, what you'd suggest. The user sees them
  on the review page with an `agent` chip.
- If feedback is generally valid for the pack (not a one-off correction),
  PROMOTE it — `--promote <id>` moves the text into the standing note so it
  survives rounds. Promote liberally: standing note beats repeating yourself.
- Never re-state promoted feedback as a new item.

## Round flow — what is open

`iconpilot next <pack>` is the ONLY source of truth for open work. It creates
the fresh `.runs/rNNN/` (old rounds stay as history) and prints exactly the
variants that are NOT approved. Draft only what it lists:

- approved/locked variants (10★ + ok applied) never reappear — tooling excludes them
- rejected candidates (0★) die with their round — history keeps them, you don't
- NEW notes are always visible: notes live on pack.json variants and are injected
  into every context build — the LLM always sees current notes, never stale comments
- never re-draft a locked variant unless the user explicitly unlocks it

## Mono/color consistency

Variants are siblings (redraws, not derivations). Consistency across mono and
color comes from three places, in order of strength:
1. Per-style Recraft styles — `iconpilot recraft-style` creates ONE Recraft style
   per pack style from that style's approved refs (mono refs → mono style,
   color refs → color style). `draft` picks the right one automatically.
2. Anchors — pin the best 2-3 icons per style; every context build injects them.
3. Auto-brief siblings — approving one variant makes it the reference_source for
   its siblings, so mono informs color and vice versa (same silhouette).

## Recraft seeding (optional quality floor)

For filled/color variants, Recraft can seed shape language before you redraw:

    iconpilot recraft-style <pack>     # once: custom style from approved/pinned icons ($0.005)
    iconpilot draft <pack> <icon> --n 4  # seeds r*.svg into the current run (~$0.05/img)

Seeds arrive on a rescaled grid wrapped in a transform group — they will NOT
pass the gate as-is (by design: seeds are references, not output). Your job:
redraw the best seed's silhouette on-grid in your normal fix-only pass, then
gate. Record the seeder cost in round.json (draft does this automatically).

Do NOT seed mono-line variants — Recraft emits filled paths, wrong construction.

## Model routing (user-definable)

The tool never calls models — the harness does. Routing lives in
`~/.config/iconpilot/models.toml` (create it if missing). If absent,
use cheapest-capable for drafting/screening, strongest for review/escalation.

```toml
[roles]
drafter  = "glm-5.3"           # high volume, cheap — writes SVG code
screener = "glm-5.3-flash"     # vision: scores the contact sheet
reviewer = "claude-opus"       # set-level consistency judgment
advisor  = "claude-opus"       # escalation: twice-rejected icons, style disputes
```

Show current routing: `cat ~/.config/iconpilot/models.toml` (or report "default").
When spawning subagents, pass the role's model — the subagent brief below
includes everything else it needs.

## Subagent drafting protocol

### When to use a subagent vs draft yourself

- **Subagent (drafter role)**: when generating 3+ candidates — it gets a clean,
  focused context without your conversation baggage. Cheaper and often better
  because it's not distracted by unrelated state.
- **Yourself**: when refining 1-2 variants with specific user comments, or when
  you need to reason about family coherence across multiple icons.

### The drafting brief (what to pass to a subagent)

Build from `iconpilot context <pack> --icon <id> --variant <v> --json`.
A complete brief has ALL 10 sections — omit nothing:

```
1. TASK       What to do: "Add 2 new variants (a3, a4)" / "Refine a2: [comment]"
2. BRIEF      The icon's brief from context (metaphor, key shapes, avoid)
3. STYLE      Gate constraints from context (viewBox, grid, gaps, budget, palette)
4. ANCHOR     The anchor SVG's actual markup, inline in a ```svg block
5. REFERENCES Sibling/reference SVGs inline (from context: reference_svg, pinned)
6. EXISTING   Current candidates' SVG source inline (if iterating a round)
7. FEEDBACK   Comments + rejected_ideas + variant/icon/pack notes (from context)
8. PALETTE    Allowed colors with hex codes (from context)
9. CRAFT      Tier-relevant rules from craft.md (grid, stroke parity, gaps,
              silhouette-first, 16px test — copy the sections, not a link)
10. FORMAT    "Output: SVG source in fenced ```svg blocks, one per candidate,
              labeled with the candidate id. One line per candidate on what
              differs from existing. No file edits."
```

**The brief is complete when a stranger with no file access could produce a
gate-passing, family-consistent icon from it alone.**

### Prompting techniques that measurably improve SVG quality

Include these in every drafting brief (subagent OR yourself):

1. **Coordinate anchors** — give specific key positions:
   ```
   The roof apex is at (24,8). The eaves are at (8,22) and (40,22).
   The door center is at (24,35). The ground line is y=42.
   ```
   This eliminates spatial guessing entirely. Extract from the anchor SVG.

2. **Chain-of-thought geometry** — instruct: "Before writing the SVG, list:
   shapes needed, their coordinates, gaps between shapes. Then write the SVG
   from your plan." This forces per-coordinate thinking, reducing near-misses.

3. **Negative examples** — include 1-2 gate failure reports:
   ```
   GATE FAILURE EXAMPLE (avoid this):
   ✗ geometry: near-miss gap 0.69 < min_gap 1.5 — strokes almost touch but don't
   ✗ geometry: coordinates off the 0.5 grid by up to 0.20
   ```
   Models learn boundaries better from concrete failures than from rules alone.

4. **Fix-only iteration** — when a gate failure comes back:
   "Fix ONLY these errors: [paste gate output]. Change NOTHING else — same
   shapes, same proportions, just correct the specific violations."
   This prevents the model from redesigning when it should just adjust.

5. **Low temperature** — when spawning the drafting subagent, use temperature
   0.2-0.4 if your harness supports it. Lower = more deterministic coordinates.

6. **Few-shot boundary** — show one PASS and one FAIL:
   ```
   THIS PASSES: <svg with clean grid, proper gaps, inside live area>
   THIS FAILS: <svg with near-miss gap> → gate says: near-miss gap 0.7 < 1.5
   ```

### Visual verification (MANDATORY before showing the user)

After `iconpilot gate` passes and before generating the contact sheet:

1. Render each candidate at 16px, 24px, 48px (the gate already does this)
2. **Inspect visually yourself or with a vision subagent**:
   - Is the silhouette readable at 16px? (squint test)
   - Does it match the anchor's visual weight and style?
   - Any near-miss gaps the sampled gate might have missed?
   - Is the color balanced (not too dark, not washed out)?
3. Score 0-10. **Discard any candidate scoring < 4.** Only survivors get
   a spot on the contact sheet.
4. If ALL candidates score < 4, go back to drafting with the failure reasons.

**Never present ungated or unverified candidates to the user.** The user
should only ever see icons that pass both the deterministic gate AND your
visual check. This is the trust contract.

### Subagent screener brief

For the vision model that scores candidates:

```
Score each candidate 0-10 against its brief:
- 0-3: wrong metaphor, unreadable silhouette, or gate-visible flaws
- 4-6: correct but generic — legible, on-style, no presence
- 7-8: clean, balanced, family-coherent — ship candidate
- 9-10: instant readability at 16px — anchor material

Test family coherence on confusable pairs (e.g. hut vs selfhut vs hotel).
Rank candidates. Flag any that break set consistency.
[Attach the contact-sheet PNG]
```

### Subagent reviewer brief (set-level, once per round)

```
Review the full contact sheet for SET consistency:
- Same visual weight across icons? (no one icon much heavier/lighter)
- Consistent roof line / perspective / detail level?
- Color palette coherent? (no rogue hues)
- Any icon that looks like it's from a different family?
Flag specific icons with what's off. This is advisory — the user decides.
[Attach the contact-sheet PNG]
```

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
