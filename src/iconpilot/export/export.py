"""Export targets: svg, sprite-svg, maplibre, iconify.

Shared materialization: approved authored variants + links whose master is
approved. Everything is deterministic; outputs are regenerated, never
hand-edited. Python-side tidy only (svgo stays an optional future pass —
no Node dependency in the core loop).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from lxml import etree  # ty: ignore[unresolved-import]
from PIL import Image

from iconpilot.render.render import render_png

SVG_NS = "http://www.w3.org/2000/svg"


@dataclass(frozen=True)
class Entry:
    icon: str
    variant: str
    path: Path
    master: tuple[str, str] | None = None  # set when materialized via link


def collect_exportables(pack_dir: Path, pack: dict) -> tuple[list[Entry], list[str]]:
    """Approved variants (+ links to approved masters); skips are reported."""
    entries: list[Entry] = []
    skipped: list[str] = []
    for icon_id, icon in pack["icons"].items():
        for vid, v in icon["variants"].items():
            if "link" in v:
                mi, _, mv = v["link"].partition("#")
                master = pack["icons"].get(mi, {}).get("variants", {}).get(mv)
                if master and master.get("status") == "approved":
                    entries.append(
                        Entry(icon_id, vid, pack_dir / "icons" / mi / f"{mv}.svg", (mi, mv))
                    )
                else:
                    skipped.append(f"{icon_id}#{vid} (master not approved)")
            elif v.get("status") == "approved":
                entries.append(Entry(icon_id, vid, pack_dir / "icons" / icon_id / f"{vid}.svg"))
            else:
                skipped.append(f"{icon_id}#{vid} ({v.get('status', 'todo')})")
    return entries, skipped


def tidy(svg_text: str) -> str:
    """Whitespace/comment minify without touching geometry."""
    text = re.sub(r"<!--.*?-->", "", svg_text, flags=re.DOTALL)
    text = re.sub(r">\s+<", "><", text.strip())
    return text + "\n"


def _inner(svg_path: Path) -> tuple[etree._Element, list[etree._Element]]:
    root = etree.parse(str(svg_path)).getroot()
    return root, list(root)


def export_svg(entries: list[Entry], out: Path) -> list[Path]:
    written: list[Path] = []
    for e in entries:
        dest = out / e.variant / f"{e.icon}.svg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tidy(e.path.read_text()))
        written.append(dest)
    return written


def export_sprite_svg(entries: list[Entry], out: Path) -> Path:
    sprite = etree.Element(f"{{{SVG_NS}}}svg", nsmap={None: SVG_NS})
    defs = etree.SubElement(sprite, f"{{{SVG_NS}}}defs")
    for e in sorted(entries, key=lambda e: (e.variant, e.icon)):
        root, children = _inner(e.path)
        sym = etree.SubElement(
            defs,
            f"{{{SVG_NS}}}symbol",
            id=f"{e.variant}-{e.icon}",
            viewBox=root.get("viewBox", "0 0 24 24"),
        )
        for attr in ("fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"):
            if root.get(attr):
                sym.set(attr, root.get(attr))
        for child in children:
            sym.append(child)
    dest = out / "sprite.svg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(
        etree.tostring(sprite, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    )
    return dest


def export_maplibre(entries: list[Entry], out: Path, size: int = 24) -> list[Path]:
    """Sprite PNG/JSON at @1x and @2x (no SDF — spreet stays optional)."""
    if not entries:
        raise ValueError("no approved icons to sprite")
    written: list[Path] = []
    for ratio, px in ((1, size), (2, size * 2)):
        ordered = sorted(entries, key=lambda e: (e.variant, e.icon))
        cols = max(1, math.ceil(math.sqrt(len(ordered))))
        rows = math.ceil(len(ordered) / cols)
        atlas = Image.new("RGBA", (cols * px, rows * px), (0, 0, 0, 0))
        layout: dict[str, dict] = {}
        for i, e in enumerate(ordered):
            col, row = i % cols, i // cols
            img = render_png(e.path, px)
            atlas.paste(img, (col * px, row * px), img)
            layout[f"{e.variant}-{e.icon}"] = {
                "x": col * px,
                "y": row * px,
                "width": px,
                "height": px,
                "pixelRatio": ratio,
                "sdf": False,
            }
        suffix = "" if ratio == 1 else f"@{ratio}x"
        atlas.save(out / f"sprite{suffix}.png")
        (out / f"sprite{suffix}.json").write_text(json.dumps(layout, indent=2))
        written += [out / f"sprite{suffix}.png", out / f"sprite{suffix}.json"]
    return written


def export_iconify(entries: list[Entry], out: Path, pack: dict) -> Path:
    icons: dict[str, dict] = {}
    aliases: dict[str, dict] = {}
    for e in entries:
        name = f"{e.icon}-{e.variant}"
        if e.master is not None:
            aliases[name] = {"parent": f"{e.master[0]}-{e.master[1]}"}
            continue
        root, children = _inner(e.path)
        vb = root.get("viewBox", "0 0 24 24").replace(",", " ").split()
        g = etree.Element(f"{{{SVG_NS}}}g")
        for attr in ("fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"):
            if root.get(attr):
                g.set(attr, root.get(attr))
        for child in children:
            g.append(child)
        body = etree.tostring(g).decode()
        icons[name] = {"body": body, "width": int(float(vb[2])), "height": int(float(vb[3]))}
    collection = {
        "prefix": pack["name"],
        "icons": icons,
        "aliases": aliases,
        "width": 24,
        "height": 24,
    }
    dest = out / f"{pack['name']}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(collection, indent=2) + "\n")
    return dest


TARGETS = {
    "svg": export_svg,
    "sprite-svg": export_sprite_svg,
    "maplibre": export_maplibre,
    "iconify": export_iconify,
}
