# Quickstart

## Install

```bash
uv tool install --from git+https://github.com/burgdev/iconpilot.git iconpilot
iconpilot install-skill   # link the skill for your agents (~/.agents/skills)
```

Python ≥ 3.12. No API keys — models are provided by the agent harness, not
this tool.

## Create a pack

```bash
iconpilot new ~/packs/alpine
iconpilot add ~/packs/alpine hut --brief "Alpine hut: steep roof, small door, no chimney" \
    --variant primitive:primitive --variant mono:mono-line --variant color:lineal-color
iconpilot check ~/packs/alpine
```

A pack is a plain directory — keep it wherever your project keeps design
assets:

```
alpine/
  pack.json        # spec + icons + state (written by the CLI only)
  icons/hut/*.svg  # originals — hand-editable between rounds
  .runs/r001/      # candidates + gate reports (gitignored)
  export/          # regenerated assets — never hand-edited
```

## Gate an SVG

The gate is deterministic and needs no models:

```bash
iconpilot gate my-icon.svg --pack ~/packs/alpine
```

```
  ✓ parse: well-formed, single <svg> root
  ✓ viewBox: 0 0 24 24 matches spec
  ✓ lint: elements/attributes conform to style 'mono-line'
  ✓ geometry: bbox inside live area; 16/40 nodes
  ✓ render: [16, 24, 48]px ok (ink 16px=33.6%, …; hash@48px)
```

## Run a round (with your agent)

In any agent session (the `iconpilot` skill is installed):

> "run an iconpilot round on hut/mono"

The agent will:

1. `iconpilot context … --icon hut --variant mono` — the deterministic
   drafting contract (brief, style vocabulary, gate thresholds, anchors)
2. write candidates to `.runs/r001/mono/hut/a1.svg …`
3. `iconpilot gate .runs/r001 --pack …` — fix until survivors pass
4. `iconpilot contact-sheet .runs/r001 --pack …` — screen visually
5. hand **you** the decision: review page or compact text

```bash
iconpilot decide ~/packs/alpine --text 'hut/mono: a2 keep "thinner roof" · b1 no · more 2'
```

Approval is always your action. Rinse until every variant is `approved`.

## Export

```bash
iconpilot export ~/packs/alpine --target maplibre --out sprites/   # sprite @1x/@2x
iconpilot export ~/packs/alpine --target iconify --out dist/       # collection JSON
```

Approved variants (and links to approved masters) materialize per icon name;
nothing approved means nothing exported — check `iconpilot status`.
