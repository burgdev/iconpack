# Changelog

## 0.1.0a1 (unreleased)

Alpha — deterministic tooling + state for designing SVG icon packs,
agent-driven (no LLM calls in the tool).

- Pack schema v2: variant siblings, styles, anchor/reference DAG, links, per-variant state
- Three-tier style registry (built-ins, user config, pack-local) with validated vocabularies
- Deterministic gate: parse, lint, true geometry (bezier-aware bbox, shapes),
  node budget, near-miss gap check, coordinate-grid precision check, resvg
  renders, ink checks, phash
- Semantic validator: link targets, DAG cycles, color-link soundness, todo-only
  designer packs
- Agent loop: `context` (drafting contract), batch gate, `contact-sheet`,
  `decide` (decision grammar + state machine, transitive staleness, hand-edit
  detection via content hashes)
- Review server: live per-icon editing, decisions through one code path,
  flock-serialized writes, rev polling
- Exports: svg, sprite-svg, maplibre sprites (@1x/@2x), iconify JSON with aliases
- Skill (SKILL.md + craft.md), zensical docs, CI (ruff/ty/pytest), Docker image
