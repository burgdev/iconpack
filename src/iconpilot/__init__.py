"""iconpilot — deterministic tooling + state for designing SVG icon packs.

The AI agent is the model layer; this package never calls LLMs. Public API:

    from iconpilot import load_pack, run_gate, collect_exportables, export_maplibre

Pack model (pack.json v2): icons with independent variant siblings
(primitive/mono/color ...) bound to styles from a three-tier registry;
`anchor` marks the family form baseline, `reference` a sibling to visually
match, `link` an alias of another icon's variant. Round state lives per
variant; `decide` is the only writer of state transitions.
"""

from iconpilot.context import build_context, render_markdown
from iconpilot.decide import apply_decisions, parse_decision_text
from iconpilot.export.export import (
    Entry,
    collect_exportables,
    export_iconify,
    export_maplibre,
    export_sprite_svg,
    export_svg,
    tidy,
)
from iconpilot.gate.run import GateReport, run_gate
from iconpilot.pack import PackError, load_pack, revalidate, schema_errors, write_pack_atomic
from iconpilot.render.contact import contact_sheet
from iconpilot.render.render import (
    hamming,
    hash_file,
    ink_ratio,
    perceptual_hash,
    render_png,
)
from iconpilot.styles import BUILTIN_STYLES, Style, resolve_styles
from iconpilot.validate import validate_pack

__version__ = "0.1.0a1"

__all__ = [
    "BUILTIN_STYLES",
    "Entry",
    "GateReport",
    "PackError",
    "Style",
    "apply_decisions",
    "build_context",
    "collect_exportables",
    "contact_sheet",
    "export_iconify",
    "export_maplibre",
    "export_sprite_svg",
    "export_svg",
    "hamming",
    "hash_file",
    "ink_ratio",
    "load_pack",
    "parse_decision_text",
    "perceptual_hash",
    "render_markdown",
    "render_png",
    "resolve_styles",
    "revalidate",
    "run_gate",
    "schema_errors",
    "tidy",
    "validate_pack",
    "write_pack_atomic",
]
