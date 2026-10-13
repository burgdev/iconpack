"""Pack loading: JSON Schema + semantic validation + style resolution."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import jsonschema

from iconpilot.styles import Style, resolve_styles
from iconpilot.validate import validate_pack


class PackError(Exception):
    """Raised when a pack fails schema or semantic validation."""


def _json_schema() -> dict:
    text = (
        resources.files("iconpilot.schema").joinpath("pack.schema.json").read_text()
    )
    return json.loads(text)


def load_pack(path: str | Path) -> tuple[dict, dict[str, Style]]:
    """Load and fully validate a pack. Raises PackError with all problems."""
    pack_path = Path(path)
    try:
        pack = json.loads(pack_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(f"cannot read pack {pack_path}: {exc}") from exc

    try:
        jsonschema.validate(pack, _json_schema())
    except jsonschema.ValidationError as exc:
        loc = "/".join(str(p) for p in exc.absolute_path) or "<root>"
        raise PackError(f"schema error at /{loc}: {exc.message}") from exc

    styles = resolve_styles(pack.get("styles"))
    errors = validate_pack(pack, styles)
    if errors:
        raise PackError("invalid pack:\n  - " + "\n  - ".join(errors))

    return pack, styles
