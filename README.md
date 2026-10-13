# iconpack

Multi-model pipeline for designing consistent SVG icon packs: cheap models draft
variants, deterministic tools gate them, and you decide each round in a review page.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

**Status:** scaffold — milestones M1 (gate + render CLI) and M3 (review server)
are the first builds. Commands below are the target surface; unimplemented ones
say so.

## Install

```bash
uv tool install --from git+https://github.com/burgdev/iconpack.git iconpack
iconpack install-skill   # symlink skill into ~/.agents/skills/ (+ ~/.claude/skills/)
```

## Usage

```bash
iconpack new ~/git/wodore/wodore-design/iconpacks/outdoor-poi
iconpack add <pack> hut --brief "Alpine hut: steep roof, small door, no chimney"
iconpack round <pack>          # generate → gate → screen → review
iconpack review <pack>         # open the review page (or --static for a file)
iconpack decide <pack> --text 'hut: a2 ok · b1 no · more 2'
iconpack export <pack> --target maplibre --out ~/git/wodore/wodore-backend/martin_sync/sprites/outdoor-poi
```

Packs live in the project's design repo (e.g. `wodore-design/iconpacks/`); this
tool is project-agnostic and can be pointed at any pack directory.

## Development

```bash
uv sync
uv run pytest
```

## License

MIT
