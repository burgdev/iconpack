# iconpack

Multi-model pipeline for designing consistent SVG icon packs: cheap models draft
variants, deterministic tools gate them, and you decide each round in a review page.

**Status:** scaffold. The CLI surface below is the target; unimplemented commands
say so.

## Install

```bash
uv tool install iconpack             # from PyPI (once published)
uv tool install --from . iconpack    # from a checkout
iconpack install-skill               # symlink skill into ~/.agents/skills/ (+ ~/.claude/skills/)
```

## Usage

```bash
iconpack new <pack-dir>
iconpack add <pack> hut --brief "Alpine hut: steep roof, small door, no chimney"
iconpack round <pack>           # generate → gate → screen → review
iconpack review <pack>          # open the review page (or --static for a file)
iconpack decide <pack> --text 'hut: a2 ok · b1 no · more 2'
iconpack export <pack> --target maplibre --out <dir>
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
