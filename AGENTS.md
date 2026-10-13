# AGENTS.md — iconpack

Multi-model SVG icon-pack pipeline: drafters generate variants, deterministic
gates check them, a screener pre-ranks them, the user decides each round.

## Commands

```bash
uv sync            # install deps (uv is the only supported workflow)
uv run pytest      # tests
uv run iconpack --help
```

## Conventions

- Python ≥3.12, stdlib + pinned deps only.
- Keep the tool **project-agnostic**: no hardcoded paths, orgs, or project
  names anywhere — packs are plain directories passed by path (or resolved
  from the user's `packs_dir` config).
- Refer to model **roles** (designer / drafter / fixer / screener / reviewer /
  advisor), never model names, in code; routing lives in user config.
- JSON Schemas in `src/iconpack/schema/` are validated on every pack load;
  extend them together with any `pack.json` format change and add a test.
- The skill (`skill/SKILL.md`) is instructions only — no logic. It is installed
  by symlink, never copied; keep it in sync with the CLI surface.
- PR titles are changelog-ready: imperative, capitalized, no conventional-commit tags.
