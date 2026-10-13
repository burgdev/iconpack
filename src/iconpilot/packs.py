"""Pack discovery across configured roots.

Config: ~/.config/iconpilot/config.toml (optional)

    [packs]
    dirs = ["~/iconpacks", "~/git/wodore/wodore-backend--iconpacks/iconpacks"]

Packs are any directory containing pack.json. When a command needs a pack and
none is given, agents list candidates via `iconpilot packs` and ASK the user.
"""

from __future__ import annotations

from pathlib import Path
from tomllib import load as tomllib_load

DEFAULT_ROOTS = ("~/iconpacks",)


def config_path() -> Path:
    return Path.home() / ".config" / "iconpilot" / "config.toml"


def pack_roots() -> list[Path]:
    roots: list[Path] = []
    cfg = config_path()
    if cfg.is_file():
        with cfg.open("rb") as fh:
            data = tomllib_load(fh)
        for d in (data.get("packs") or {}).get("dirs") or []:
            roots.append(Path(d).expanduser())
    for d in DEFAULT_ROOTS:
        p = Path(d).expanduser()
        if p not in roots:
            roots.append(p)
    return [r for r in roots if r.is_dir()]


def discover_packs() -> list[dict]:
    """All packs under configured roots (shallow scan), newest-free, sorted."""
    seen: dict[str, dict] = {}
    for root in pack_roots():
        for pack_json in root.glob("*/pack.json"):
            d = pack_json.parent
            seen[str(d)] = {
                "path": str(d),
                "name": d.name,
            }
    return [seen[k] for k in sorted(seen)]


def summarize(path: str) -> str:
    """One-line status summary for `iconpilot packs` (errors tolerated)."""
    try:
        from iconpilot.pack import load_pack

        pack, _ = load_pack(Path(path) / "pack.json")
        counts: dict[str, int] = {}
        for icon in pack["icons"].values():
            for v in icon["variants"].values():
                if "style" in v:
                    st = v.get("status", "todo")
                    counts[st] = counts.get(st, 0) + 1
        summary = " · ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "empty"
        return f"{pack['name']}: {summary}"
    except Exception as exc:  # noqa: BLE001 — listing must not die on one bad pack
        return f"invalid: {str(exc).splitlines()[0][:80]}"
