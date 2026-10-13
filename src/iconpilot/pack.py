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
    text = resources.files("iconpilot.schema").joinpath("pack.schema.json").read_text()
    return json.loads(text)


def schema_errors(pack: dict) -> list[str]:
    """JSON-Schema errors as readable strings (empty = shape ok)."""
    validator = jsonschema.Draft202012Validator(_json_schema())
    return [
        f"/{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
        for e in sorted(validator.iter_errors(pack), key=lambda e: list(e.absolute_path))
    ]


def revalidate(pack: dict) -> tuple[dict[str, Style], list[str]]:
    """Validate an in-memory pack dict; returns (styles, errors)."""
    errors = schema_errors(pack)
    styles = resolve_styles(pack.get("styles"))
    if not errors:  # semantics only meaningful when shape is ok
        errors = validate_pack(pack, styles)
    return styles, errors


def load_pack(path: str | Path) -> tuple[dict, dict[str, Style]]:
    """Load and fully validate a pack. Raises PackError with all problems."""
    pack_path = Path(path)
    try:
        pack = json.loads(pack_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(f"cannot read pack {pack_path}: {exc}") from exc

    styles, errors = revalidate(pack)
    if errors:
        raise PackError("invalid pack:\n  - " + "\n  - ".join(errors))

    return pack, styles


def write_pack_atomic(pack_dir: Path, pack: dict) -> None:
    """Atomic pack.json write (tmp + rename). Callers hold the pack lock."""
    pack["rev"] = pack.get("rev", 0) + 1
    tmp = pack_dir / "pack.json.tmp"
    tmp.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(pack_dir / "pack.json")
