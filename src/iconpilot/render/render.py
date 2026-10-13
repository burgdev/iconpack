"""Deterministic rendering and perceptual hashing.

resvg renders every variant at the style's sizes (plus a fixed 48px hash
render for comparability); imagehash phash powers near-duplicate detection
and link suggestions. No LLMs in here — pixels and hashes only.
"""

from __future__ import annotations

import io
from pathlib import Path

import imagehash
import resvg_py
from PIL import Image

HASH_RENDER_SIZE = 48


def render_png(svg_path: str | Path, size: int, background: str | None = None) -> Image.Image:
    """Render an SVG to an RGBA PIL image at `size` × `size`."""
    png = resvg_py.svg_to_bytes(
        svg_path=str(svg_path), width=size, height=size, background=background
    )
    return Image.open(io.BytesIO(bytes(png))).convert("RGBA")


def render_png_text(svg_text: str, size: int, background: str | None = None) -> Image.Image:
    """Render an SVG *string* (post color-substitution) at size × size."""
    png = resvg_py.svg_to_bytes(svg_string=svg_text, width=size, height=size, background=background)
    return Image.open(io.BytesIO(bytes(png))).convert("RGBA")


def ink_ratio(img: Image.Image) -> float:
    """Fraction of non-transparent pixels (alpha > 0)."""
    alpha = img.getchannel("A")
    hist = alpha.histogram()
    ink = sum(hist[1:])
    return ink / (img.width * img.height)


def perceptual_hash(img: Image.Image) -> str:
    """64-bit phash as hex — always computed at HASH_RENDER_SIZE for comparability.

    The RGBA render must be composited onto a solid background first:
    currentColor strokes are black and the transparent canvas flattens to
    black too, so a naive convert("L") hashes a uniformly black image.
    """
    if img.mode == "RGBA":
        flat = Image.new("RGB", img.size, (255, 255, 255))
        flat.paste(img, mask=img.getchannel("A"))
        img = flat
    return str(imagehash.phash(img, hash_size=8))


def hash_file(svg_path: str | Path) -> str:
    return perceptual_hash(render_png(svg_path, HASH_RENDER_SIZE))


def hamming(a: str, b: str) -> int:
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)
