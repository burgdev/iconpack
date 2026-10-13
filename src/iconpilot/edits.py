"""Hand-edit detection: compare icons/*.svg against the content_hash
recorded at the last decision. Read-only detection; state changes are
applied only by `decide` (the sanctioned writer)."""

from __future__ import annotations

from pathlib import Path

from iconpilot.pack import file_sha256


def detect_edits(pack_dir: Path, pack: dict) -> list[dict]:
    """Variants whose icons/<icon>/<variant>.svg differs from content_hash."""
    edited = []
    for icon_id, icon in pack["icons"].items():
        for vid, v in icon["variants"].items():
            if "link" in v or "content_hash" not in v:
                continue
            f = pack_dir / "icons" / icon_id / f"{vid}.svg"
            if f.is_file() and file_sha256(f) != v["content_hash"]:
                edited.append({"icon": icon_id, "variant": vid})
    return edited
