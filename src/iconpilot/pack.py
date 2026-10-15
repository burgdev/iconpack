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


def advance_feedback(pack: dict, new_round_dir: Path) -> list[dict]:
    """Archive live feedback into the new round's dir; clear the live list.

    Called by `next` / `_start_round` when a new round begins. The archived
    `.runs/<round>/feedback.json` is the immutable history of what that round
    was drafted against. Legacy icon/variant `note` strings migrate into
    feedback items once, then are removed from pack.json.
    """
    import uuid

    feedback = list(pack.get("feedback", []))
    # one-time migration: legacy icon/variant notes become feedback items
    for iid, icon in pack.get("icons", {}).items():
        legacy = icon.pop("note", None)
        if legacy:
            feedback.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "scope": "icon",
                    "icon": iid,
                    "text": legacy,
                    "author": "user",
                    "round": "legacy",
                }
            )
        for vid, v in icon.get("variants", {}).items():
            vlegacy = v.pop("note", None)
            if vlegacy:
                feedback.append(
                    {
                        "id": uuid.uuid4().hex[:8],
                        "scope": "variant",
                        "icon": iid,
                        "variant": vid,
                        "text": vlegacy,
                        "author": "user",
                        "round": "legacy",
                    }
                )
    if feedback:
        (new_round_dir / "feedback.json").write_text(json.dumps(feedback, indent=2))
    pack["feedback"] = []
    return feedback


def next_run_id(runs_dir: Path) -> str:
    """Gap-safe monotonic run id: max existing number + 1.

    Count-based ids (len(runs)+1) silently clobber an existing round when the
    numbering has gaps (e.g. manual deletion).
    """
    import re as _re

    nums = [
        int(m.group(1))
        for p in runs_dir.glob("r*")
        if p.is_dir() and (m := _re.match(r"r(\d+)$", p.name))
    ]
    return f"r{max(nums, default=0) + 1:03d}"


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


def resolve_default_variant(icon: dict) -> str | None:
    """One rule for every caller: the icon's single non-approved authored
    variant, else 'mono' when authored, else the first authored variant."""
    authored = [v for v, d in icon.get("variants", {}).items() if "style" in d]
    if not authored:
        return None
    open_variants = [v for v in authored if icon["variants"][v].get("status") != "approved"]
    if len(open_variants) == 1:
        return open_variants[0]
    if "mono" in authored:
        return "mono"
    return authored[0]


def file_sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_pack_atomic(pack_dir: Path, pack: dict) -> None:
    """Atomic pack.json write (tmp + rename). Callers hold the pack lock."""
    pack["rev"] = pack.get("rev", 0) + 1
    tmp = pack_dir / "pack.json.tmp"
    tmp.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(pack_dir / "pack.json")
