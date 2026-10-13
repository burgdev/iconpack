# iconpack — Architecture

Multi-model pipeline for designing consistent SVG icon packs, with deterministic
quality gates and the user as the final gate in every round.

> Named `ARCHITECTURE.md` on purpose: `DESIGN.md` is reserved for the Google Stitch
> brand/design-system format, which iconpack *consumes* (see §8).

---

## 1. Goals

- Produce **consistent, production-ready SVG icon packs** (fixed grid, uniform stroke, clean paths).
- Use **cheap models for volume**, **Claude only where judgment matters** (concepts, set review, escalation).
- **Deterministic tools do the checking**; LLMs never self-certify validity.
- **User decides** each round via an HTML review page; variants narrow round by round.
- Packs are **authored in project design repos** and reusable across projects; consuming
  projects only link and export. The tool itself is project-agnostic.
- Works locally, headless, and remotely (e.g. via Paseo).

Non-goals: raster/illustration generation, a hosted service, a Paseo-specific plugin.

---

## 2. Where things live

```
1. Tool repo (code)     ~/git/burgdev/iconpack          → github.com/burgdev/iconpack
                                                          installed globally: uv tool install --from git+…
2. Skill (thin)         ~/.agents/skills/iconpack/       (symlinked into ~/.claude/skills/
                                                          by `iconpack install-skill`)
3. Packs (design data)  <design-repo>/iconpacks/<pack>/  e.g. wodore-design: iconpacks/outdoor-poi/
4. Config / secrets     ~/.config/iconpack/config.toml   (chezmoi-managed, no secrets)
                        API keys via environment (my_envs.env), referenced by name only
```

The tool never assumes a pack location: packs are addressed by `--pack <path>`
or resolved from `packs_dir` in config. First consumer: wodore (map POI + category
icons), but nothing in the pipeline knows about maps (§9).

### 2.1 Tool repo

```
iconpack/
  src/iconpack/
    cli.py              # entry point (§10)
    pipeline/           # concept, generate, gate, screen, setreview, apply
    models/             # adapters: openai_compat (GLM), anthropic (Claude)
    gate/               # lint, simplify, geometry, config generation from pack.json
    render/             # resvg renders, contact sheets
    server/             # review server + page template (§6)
    prompts/            # prompt templates per role
    schema/             # JSON Schemas: pack.json, decisions.json, round.json
  skill/SKILL.md        # skill source (§11)
  pyproject.toml
  tests/
```

Node tools (`package.json`) are added with the export milestone (M6) — M1–M3 are
pure Python (see §2.2).

### 2.2 External tools (Python first, Node later)

| Purpose | Tool | Ecosystem | Milestone |
|---|---|---|---|
| Deterministic rendering (PNG at 16/24/48, contact sheets) | `resvg-py` | Python | M1 |
| Geometry checks (bbox, live area, snapping, node count) | `svgpathtools`, `lxml` | Python | M1 |
| Perceptual similarity (duplicate detection) | `imagehash` | Python | M2 |
| Simplify to plain paths (no transforms/groups, shapes→paths) | `picosvg` | Python | M6 |
| Optimize/minify with fixed config | `svgo` | Node | M6 |
| Rule-based lint | `svglint` | Node | M6 |
| Cleanup, color normalization, Iconify JSON export | `@iconify/tools` | Node | M6 |
| MapLibre sprite sheets (incl. SDF) | `spreet` | Rust binary | M6 |
| DESIGN.md validation | `@google/design.md` | Node | M6 (optional) |

Node tools will be pinned in the repo's `package.json` and called via a small
runner (no global npm installs). Optional: Docker image bundling Python + Node +
spreet for headless runs. Python equivalents (e.g. `scour`) are acceptable
substitutes if the Node runner becomes friction.

---

## 3. Model roles

| Role | Default model | Input | Output | Frequency |
|---|---|---|---|---|
| **designer** — spec draft, style anchors, concept briefs | Claude (strong) | DESIGN.md, pack spec, icon list | briefs (metaphor, key shapes, avoid) | once per new/restarted icon, batched |
| **drafter** — draw & refine SVG | GLM-5.3 (no vision) | brief, spec, anchors as SVG text, gate report, geometry metrics, critiques, user comments | SVG | per variant |
| **fixer** — mechanical fixes, variants (filled/outline), metadata | GLM-flash | SVG + lint/geometry errors | SVG / tags | on demand |
| **screener** — visual pre-screen | GLM-flash (vision) | renders 16/24/48 + brief | score 0–10, ≤2-line critique, rank | per variant |
| **reviewer** — set-level consistency | Claude | one contact-sheet image (approved + candidates) + spec | per-icon flags, notes, rule suggestions | **one call per round** |
| **advisor** — escalation | Claude | icon history (briefs, rejected ideas, comments) | new concept/brief | when an icon is fully rejected twice, or user flags it |

Key constraint: **the drafter is blind**, so all visual feedback reaches it as text
(screener critique, reviewer notes, user comments) plus numeric geometry metrics.

Routing is configurable (§12); roles, not model names, appear in code.

---

## 4. Pipeline and rounds

### 4.1 Round flow (for every icon not yet approved)

```
[concept]  designer, only for new/restarted icons (batched)
    │
[generate] drafter → n+1 variants   (n from narrowing schedule)
    │
[gate]     deterministic: parse → svgo → svglint → geometry → render
    │        failures → fixer (max 2 attempts) → else drop
[screen]   screener scores survivors, keeps best n
    │
[review]   reviewer: one contact sheet for the whole round (skippable: --no-claude)
    │
[user]     review page → decisions.json
    │
[apply]    update pack.json, freeze approved, schedule next round
```

### 4.2 Narrowing schedule

- Default variants per round: **`[4, 2, 1]`** (configurable per pack).
- Round k for an icon uses `schedule[min(k, len-1)]`.
- **Kept** variants are refined (drafter gets the kept SVG + comments), not regenerated from scratch.
- **Approved** → icon frozen, SVG copied to `icons/`, optionally promoted to **anchor**.
- **All rejected** → icon resets to schedule[0] with comments + rejected ideas in the prompt.
  Second full rejection → **advisor** escalation.
- **User override wins**: `more N`, `like <variant> N`, `restart` reset the count for that icon only.

### 4.3 Icon state machine

```
todo → drafting → in_review → approved (frozen)
                     │  ↑            │
                     └──┘ (keep)     └→ reopened (explicit user action only)
          rejected ×2 → escalated → drafting
```

### 4.4 Rule promotion

When the same kind of comment recurs (≥2 icons, detected by reviewer or fixer),
the UI suggests promoting it to a pack rule ("door gap ≥ 2px"). Only user-confirmed
rules enter `pack.json.rules` and all future prompts / geometry checks where expressible.

---

## 5. Deterministic gate

All lint/optimizer configs are **generated from `pack.json` at runtime** (single source of truth).

| Step | Tool | Checks / actions |
|---|---|---|
| Parse | lxml | well-formed, single root `<svg>`, viewBox equals spec |
| Optimize | svgo (generated config) | keep viewBox & strokes, round coordinates to precision, remove metadata |
| Lint | svglint (generated rules) | allowed elements/attributes only, `stroke="currentColor"`, no inline styles, no transforms, no ids/classes unless allowed |
| Geometry | svgpathtools | bbox inside live area; uniform stroke width; coordinates snapped; node count ≤ max; min feature size / gap at 24px |
| Render | resvg | PNG at 16/24/48, light + dark (+ optional custom background); contact-sheet tiles |
| Similarity | imagehash | flag near-duplicates within a round and against approved icons |

Gate output per variant (`gate.json`): pass/fail, error list (machine + human readable),
metrics (bbox, node count, stroke widths, snap deviation). This report is what the
blind drafter and the fixer receive.

`picosvg` is **not** applied to the stroke source; it is used (a) as a check that the
icon converts cleanly and (b) at export for fill-only targets (fonts).

---

## 6. Review server and page

### 6.1 Server

- `iconpack review [--pack P] [--host 127.0.0.1] [--port 8765]`
- Small Python web server (FastAPI or stdlib — open decision) that:
  - generates the page on demand from `pack.json` + current round in `.runs/`
  - serves renders/SVGs from `.runs/`
  - accepts decisions via `POST /api/decision` and writes `decisions.json` immediately (resumable)
- Remote use: localhost at desk, Paseo browser preview (to be tested), or Tailscale/WireGuard.

### 6.2 Page

- Mobile-first. One row per icon; variants side by side.
- Each variant: renders at 16/24/48, light/dark toggle, screener score, reviewer note (hint).
- Per variant: **approve · keep · reject**, comment field.
- Per icon: **more N · like this N · restart**, free-text note.
- **Set view**: all approved icons + current picks on one sheet to spot outliers.
- Rule-promotion suggestions with confirm/dismiss.

### 6.3 Fallback (no server reachable)

`iconpack review --static` writes a single self-contained HTML file (SVGs inline).
If the page can't reach the API, it shows **"Copy decisions"**, producing a compact text
the user pastes into the agent chat; the agent (via skill) runs `iconpack decide --text`.

Compact grammar (ASCII, one icon per line):

```
<icon>: <items>        items separated by " · " or ";"
  <v> ok                approve variant v (e.g. a2)
  <v> keep ["comment"]  keep for refinement
  <v> no ["comment"]    reject
  * no                  reject all
  more <N>              N more variants
  like <v> <N>          N variants based on v
  restart ["note"]      back to concept
  note "text"           icon-level note
```

Example: `hut: a2 keep "thinner roof" · b1 no · more 2`

Both paths produce the same `decisions.json`; the pipeline only reads that file.

---

## 7. Data model

### 7.1 Pack layout

```
<design-repo>/iconpacks/<pack>/        e.g. ~/git/wodore/wodore-design/iconpacks/outdoor-poi/
  pack.json        # spec + registry (versioned, committed)
  icons/*.svg      # approved icons, final stroke source (committed)
  .runs/           # gitignored scratch
    r001/
      round.json         # icons in this round, n per icon, model routing used, costs
      <icon>/<variant>.svg
      <icon>/<variant>.gate.json
      <icon>/<variant>.screen.json
      renders/…png
      contact-sheet.png
      review.json        # reviewer output
      decisions.json     # user decisions
```

### 7.2 `pack.json` (sketch)

```json
{
  "schema": 1,
  "name": "outdoor-poi",
  "version": "0.1.0",
  "inherits": { "design_md": null },
  "spec": {
    "viewBox": "0 0 24 24",
    "live_area": { "padding": 2 },
    "stroke": { "width": 2, "linecap": "round", "linejoin": "round" },
    "corner_radius": 2,
    "fill": "none",
    "color": "currentColor",
    "allowed_elements": ["path", "circle", "rect", "line", "polyline", "polygon", "ellipse"],
    "precision": 0.5,
    "max_nodes": 40,
    "min_gap": 1.5
  },
  "style": {
    "description": "Calm, geometric, readable at 16px.",
    "anti_references": ["skeuomorphic detail", "hairline strokes"]
  },
  "rules": ["Door gap at least 2 units"],
  "schedule": [4, 2, 1],
  "anchors": ["hut"],
  "icons": {
    "hut": {
      "brief": "Alpine hut: steep roof, small door, no chimney",
      "tags": ["building", "shelter"],
      "status": "approved",
      "chosen": { "run": "r002", "variant": "a1" },
      "comments": [{ "round": "r001", "text": "thinner roof" }],
      "rejected_ideas": ["house with flag"]
    }
  }
}
```

JSON Schema lives in `src/iconpack/schema/` and is validated on every load.

### 7.3 `decisions.json` (per round)

```json
{
  "round": "r001",
  "decided_at": "2026-10-13T12:00:00+02:00",
  "source": "server",
  "icons": {
    "hut": {
      "variants": { "a2": { "action": "keep", "comment": "thinner roof" }, "b1": { "action": "reject" } },
      "request": { "type": "more", "n": 2 },
      "note": null
    }
  },
  "rules_confirmed": ["Door gap at least 2 units"]
}
```

---

## 8. DESIGN.md inheritance

- A pack may set `inherits.design_md` to a Stitch-format DESIGN.md (e.g. created by Impeccable).
- Used as **defaults and prompt context**: colors, corner rounding, mood, anti-references → designer/drafter prompts.
- Explicit values in `pack.json.spec` always win. DESIGN.md is never required.
- Validated with `@google/design.md lint` when present (warning only).
- Optional write-back: `iconpack link --write-design-md` adds a short **Iconography** prose
  section to a project's DESIGN.md naming the pack and its key rules, so other agents use
  the pack instead of inventing icons.

First consumer: **wodore-design** — the pack repo and the DESIGN.md it inherits are the
same repository, so `inherits.design_md` is a repo-relative path.

---

## 9. Project linking and export

```
<consuming project>/
  iconpack.toml          # pack name (or path), version/commit, export targets, output paths
```

Export targets (`iconpack export`):

| Target | Output |
|---|---|
| `svg` | optimized individual SVGs |
| `sprite-svg` | single SVG `<symbol>` sprite |
| `maplibre` | sprite PNG/JSON (+ SDF) via spreet, @1x/@2x |
| `iconify` | Iconify JSON collection |
| `font` (optional) | outlined via picosvg, then font tool (later) |

First consumer wiring (wodore): pack authored in `wodore-design/iconpacks/`;
`wodore-backend` holds the `iconpack.toml` and receives exports — MapLibre sprites into
`martin_sync/sprites/`, Iconify JSON importable by the backend icon-library packs at a
pinned ref. Direction is strictly one-way: design repo authors, backend consumes.

---

## 10. CLI

```
iconpack new <pack> [--from-design-md PATH]   # create pack, designer drafts spec + briefs
iconpack add <pack> <icon> [--brief TEXT]     # add icons to registry
iconpack bakeoff <pack> --models A,B --icons N  # step 0: compare drafters (§13)
iconpack round <pack> [--icons a,b] [--no-claude] [--dry-run]
iconpack review <pack> [--host H --port P | --static]
iconpack decide <pack> --text "…" | --file decisions.json
iconpack status <pack>                        # states, costs, open icons
iconpack gate <file.svg> --pack <pack>        # run gate on any SVG (debug / hand-made icons)
iconpack export <pack> --target T --out DIR
iconpack link [--write-design-md]             # in a project: create iconpack.toml
iconpack install-skill                        # symlink skill into ~/.agents/skills/ (+ ~/.claude/skills/)
```

All commands are non-interactive by default (agent- and Paseo-friendly); `--json` for machine output.
`<pack>` is a directory path or a name resolved from `packs_dir`.

---

## 11. Skill (`skill/SKILL.md`)

Instructions only, no logic. Source of truth is this repo — the skill is installed
(symlinked) by `iconpack install-skill`, never copied, so it never drifts from the CLI.

- Install targets: `~/.agents/skills/iconpack` (cross-agent: pi, codex, …) with a
  `~/.claude/skills/iconpack` symlink for Claude.
- When to use: creating/extending an icon pack, reviewing rounds, exporting into a project.
- Which commands to run, in which order (`round` → `review` → `decide` → repeat → `export`).
- How to convert pasted compact-decision text into `iconpack decide --text`.
- Never edit `pack.json` or `icons/` by hand; always via CLI.
- Escalation: when to call the advisor; keep Claude usage to designer/reviewer/advisor roles.
- Report to the user: review URL or static file path, round summary, cost.

---

## 12. Config (`~/.config/iconpack/config.toml`)

Managed by chezmoi (dotfiles). Contains **no secrets** — only key *names*; values come
from the environment (e.g. `my_envs.env`).

```toml
[models.glm]
kind = "openai_compat"
base_url = "https://…"
api_key_env = "GLM_API_KEY"

[models.claude]
kind = "anthropic"
api_key_env = "ANTHROPIC_API_KEY"

[roles]
designer = "claude:opus"
reviewer = "claude:sonnet"
advisor  = "claude:opus"
drafter  = "glm:glm-5.3"
fixer    = "glm:glm-5.3-flash"
screener = "glm:glm-5.3-flash"   # must support vision

[defaults]
schedule = [4, 2, 1]
max_fix_attempts = 2
packs_dir = "~/git/wodore/wodore-design/iconpacks"
```

Model identifiers are placeholders until configured.

---

## 13. Cost control

- Claude calls per round: ≤ 1 reviewer call + batched designer call for new icons + escalations.
- Prompt caching for spec, rules, anchors on all Claude calls.
- `--no-claude` rounds for cheap iterations (screener + user only).
- Per-round cost tracked in `round.json`; shown in `status` and on the review page.
- **Step 0 bake-off**: 5–10 representative icons, each candidate drafter, same spec.
  Metric: **cost per user-accepted icon** (plus gate pass rate, screener score).
  Decides drafter routing before the first real pack.

---

## 14. Open decisions

1. Style & grid for the first pack (stroke vs. filled, 24px?).
2. Scope: number of icons; existing set to match?
3. ~~Export targets needed first~~ → **resolved**: `svg` + `maplibre` first (wodore
   sprites), `iconify` when the backend icon-library importer lands.
4. Paseo: does its browser preview reach a localhost port? (decides server vs. static as default remote path)
5. Server framework: FastAPI vs. stdlib.
6. Exact vision-capable GLM-flash model and endpoints.
7. ~~Packs: one repo for all packs vs. one repo per pack; license for packs~~ →
   **resolved**: packs live inside the project's design repo
   (`wodore-design/iconpacks/<pack>/`); the tool is location-agnostic. Pack licensing
   follows the hosting design repo (MIT for wodore-design) unless a pack is later
   published separately.

---

## 15. Milestones

| # | Deliverable | LLMs |
|---|---|---|
| M0 | Bake-off script (generate + gate + screen + cost report) | GLM, Claude |
| M1 | Gate + render CLI on hand-made SVGs; config generation from pack.json | none |
| M2 | `round` with drafter, fixer, screener | GLM |
| M3 | Review server + static fallback + `decide --text` | none |
| M4 | Rounds, narrowing, state machine, anchors, rule promotion | GLM |
| M5 | Designer, reviewer, advisor roles; prompt caching; cost tracking | Claude |
| M6 | Export targets, project linking, DESIGN.md inheritance/write-back | none |
| M7 | Skill + `install-skill`; Docker image (optional) | — |

M1 and M3 need no models and can be built and tested first. M0 can start as soon as
M1's gate exists (it only needs generate + gate + screen).
