"""Contact sheets: one PNG grid of candidates (+ approved icons) for
vision screening by the agent and set review by the user."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from iconpilot.render.render import render_png

TILE = 96
PAD = 10
COLS = 6


def contact_sheet(svg_paths: list[Path], out_path: Path, title: str = "") -> Path:
    if not svg_paths:
        raise ValueError("no SVGs to compose")
    rows = (len(svg_paths) + COLS - 1) // COLS
    header = 24 if title else 0
    sheet = Image.new("RGB", (COLS * TILE, header + rows * (TILE + 18)), "white")
    draw = ImageDraw.Draw(sheet)
    if title:
        draw.text((8, 6), title, fill="black")
    for i, svg in enumerate(svg_paths):
        col, row = i % COLS, i // COLS
        x, y = col * TILE + PAD, header + row * (TILE + 18) + PAD
        img = render_png(svg, TILE - 2 * PAD, background="#ffffff")
        sheet.paste(img, (x, y), img)
        draw.text((col * TILE + PAD, y + TILE - 2 * PAD + 4),
                  svg.stem, fill="black")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path
