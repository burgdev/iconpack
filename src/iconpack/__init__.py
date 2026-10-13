"""iconpack — multi-model pipeline for designing consistent SVG icon packs."""

__version__ = "0.0.1"

MILESTONES: dict[str, str] = {
    "new": "M4/M5 (state machine, designer role)",
    "add": "M4 (registry)",
    "bakeoff": "M0 (drafter comparison)",
    "round": "M2 (drafter, fixer, screener)",
    "review": "M3 (review server + static page)",
    "decide": "M3 (decision parsing)",
    "status": "M4 (round tracking)",
    "gate": "M1 (deterministic gate)",
    "export": "M6 (export targets)",
    "link": "M6 (project linking)",
    "install-skill": "M7 (skill installation)",
}
