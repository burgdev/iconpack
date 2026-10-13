# Library API

iconpilot is a plain Python package with no CLI coupling — embed it in build
steps, management commands, or deploy pipelines.

```bash
uv add iconpilot --git https://github.com/burgdev/iconpilot.git
```

Everything public is importable from the package root:

```python
from iconpilot import (
    load_pack, run_gate, build_context,
    collect_exportables, export_maplibre, export_iconify,
)
```

## Load and validate

```python
from pathlib import Path
from iconpilot import load_pack, PackError

try:
    pack, styles = load_pack(Path("iconpacks/accommodation/pack.json"))
except PackError as e:
    ...  # schema + semantic errors, one per line
```

Raises `PackError` with *all* problems (JSON schema shape, style resolution,
link targets, DAG cycles), never just the first.

## Gate an SVG

```python
from iconpilot import run_gate

report = run_gate("candidate.svg", pack, styles["mono-line"])
report.passed      # bool
report.errors      # ["geometry: 47 nodes > style max 40 (mono-line)", …]
report.checks      # what passed
report.metrics     # {"node_count": 47, "bbox": [...], "ink_ratio": {...}, "phash": "…"}
```

## Export from source (the "commit only sources" pattern)

Commit `iconpacks/<pack>/` (pack.json + `icons/`); generate everything else
at build time into ignored directories:

```python
from pathlib import Path
from iconpilot import load_pack, collect_exportables, export_maplibre

repo = Path(__file__).resolve().parents[2]
pack_dir = repo / "iconpacks" / "accommodation"
pack, _ = load_pack(pack_dir / "pack.json")
entries, skipped = collect_exportables(pack_dir, pack)   # approved + approved links
export_maplibre(entries, repo / "martin_sync/sprites/accommodation", size=48)
```

As a Django management command this regenerates sprites on deploy; the
`Entry` dataclass tells you what each export came from (`master` is set when
an entry materialized through a link).

## Similarity & context

```python
from iconpilot import hash_file, hamming, build_context, render_markdown

if hamming(hash_file("a.svg"), hash_file("b.svg")) <= 8:
    ...  # near-duplicate → suggest a link (human confirms intent)

ctx = build_context(pack_dir, pack, styles, "hut", "mono")
prompt = render_markdown(ctx)   # feed verbatim to a drafting model
```

## API index

| Symbol | Purpose |
|---|---|
| `load_pack`, `revalidate`, `schema_errors`, `PackError` | load + validate packs |
| `Style`, `BUILTIN_STYLES`, `resolve_styles`, `validate_pack` | style registry & semantics |
| `run_gate`, `GateReport` | deterministic gate |
| `render_png`, `hash_file`, `hamming`, `perceptual_hash`, `ink_ratio`, `contact_sheet` | renders & similarity |
| `build_context`, `render_markdown` | drafting contracts |
| `parse_decision_text`, `apply_decisions` | decision grammar & state machine |
| `collect_exportables`, `Entry`, `export_svg`, `export_sprite_svg`, `export_maplibre`, `export_iconify`, `tidy` | exports |

No stability guarantees before `1.0`; pin your git dependency.
