# AGENTS.md — iconpack

Multi-model SVG icon-pack pipeline. Canonical design doc: `ARCHITECTURE.md`
(read it before changing pipeline/gate/data-model behavior).

## Commands

```bash
uv sync            # install deps (uv is the only supported workflow)
uv run pytest      # tests
uv run iconpack --help
```

## Conventions

- Python ≥3.12, stdlib + the pinned deps only. Node tools are deferred to M6
  (ARCHITECTURE.md §2.2) — do not add npm dependencies before that milestone.
- Roles, not model names, appear in code (§3); routing lives in config (§12).
- JSON Schemas in `src/iconpack/schema/` are validated on every pack load;
  extend them together with any `pack.json` format change and add a test.
- The skill (`skill/SKILL.md`) is instructions only — no logic. It is installed
  by symlink, never copied; keep it in sync with the CLI surface.
- PR titles are changelog-ready: imperative, capitalized, no conventional-commit tags.
