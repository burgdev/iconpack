# iconpilot

Multi-model pipeline for designing consistent SVG icon packs: cheap models draft
variants, deterministic tools gate them, and you decide each round in a review page.

**Status:** scaffold. The CLI surface below is the target; unimplemented commands
say so.

## Install

```bash
uv tool install iconpilot             # from PyPI (once published)
uv tool install --from . iconpilot    # from a checkout
iconpilot install-skill               # symlink skill into ~/.agents/skills/ (+ ~/.claude/skills/)
```

## Usage

```bash
iconpilot new <pack-dir>
iconpilot add <pack> hut --brief "Alpine hut: steep roof, small door, no chimney"
iconpilot round <pack>           # generate → gate → screen → review
iconpilot review <pack>          # open the review page (or --static for a file)
iconpilot decide <pack> --text 'hut: a2 ok · b1 no · more 2'
iconpilot export <pack> --target maplibre --out <dir>
```

A pack is just a directory (`pack.json` + `icons/`) — keep packs wherever your
project keeps design assets. Consuming projects link a pack and export from it
(SVG, SVG sprite, MapLibre sprite, Iconify JSON).

## Development

```bash
uv sync
uv run pytest
```

## License

MIT
