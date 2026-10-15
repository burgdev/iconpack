"""Recraft API client — SVG seed drafting for iconpilot.

Recraft (https://recraft.ai) is a hosted image/SVG generation service.
iconpilot uses it as a *seeder*: Recraft proposes shape language, the
agent redraws on-grid, the gate certifies. No LLM calls happen here —
this is a plain REST client behind the user's own API token.

Token resolution order:
1. ``RECRAFT_API_TOKEN`` environment variable
2. ``[recraft] token`` in ``~/.config/iconpilot/models.toml``

Example ``models.toml``::

    [recraft]
    token = "xxxxxxxx-xxxx-xxxx"
    model = "recraftv4_styles_vector"
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://external.api.recraft.ai/v1"
DEFAULT_MODEL = "recraftv4_styles_vector"  # cheapest vector WITH custom styles
FALLBACK_MODEL = "recraftv2_vector"  # cheapest vector overall ($0.044, has "Icon" style)
TIMEOUT_S = 180

# USD per image (Recraft list prices, 2026). Used for cost estimates everywhere.
MODEL_PRICES: dict[str, float] = {
    "recraftv2_vector": 0.044,
    "recraftv3_vector": 0.08,
    "recraftv4_vector": 0.08,
    "recraftv4_1_vector": 0.08,
    "recraftv4_1_utility_vector": 0.08,
    "recraftv4_styles_vector": 0.05,
    "recraftv4_1_pro_vector": 0.30,
    "recraftv4_styles_pro_vector": 0.12,
}
STYLE_CREATE_PRICE = 0.005


def refs_hash(refs: list[str]) -> str:
    """Stable hash over ref contents — changes when any ref changes."""
    import hashlib

    h = hashlib.sha256()
    for svg in sorted(refs):  # sorted = order-independent
        h.update(svg.encode())
    return h.hexdigest()[:16]


def max_versions(grid: int) -> int:
    """How many icon versions fit in a grid: 1×1 = 6 (n-mode), NxN = grid²."""
    return 6 if grid == 1 else grid * grid


def prompt_limit(model: str) -> int:
    """Max prompt chars per model: V4/V4.1 = 10,000; V2/V3 = 1,000."""
    return 10000 if "v4" in model else 1000


# our style ids → Recraft V2-vector CURATED icon styles (by name). Used to
# generate reference icons in exactly that look via the `style` parameter.
# Suggested vector model per style family (V4 for detail/gradient, V2 for classic line styles)
STYLE_MODEL_SUGGESTIONS = {
    "primitive": "recraftv2_vector",
    "mono-line": "recraftv2_vector",
    "mono-line-thin": "recraftv2_vector",
    "mono-bold": "recraftv2_vector",
    "filled": "recraftv2_vector",
    "duotone": "recraftv4_1_vector",
    "lineal-color": "recraftv4_1_vector",
    "flat-color": "recraftv4_1_vector",
    "gradient-color": "recraftv4_1_vector",
    "broken-line": "recraftv2_vector",
    "colored-outline": "recraftv4_1_vector",
    "isometric": "recraftv4_1_vector",
    "offset-fill": "recraftv4_1_vector",
    "pixel": "recraftv2_vector",
    "doodle": "recraftv2_vector",
}

CURATED_STYLE_MAP = {
    "mono-line": "Outline",
    "mono-line-thin": "Thin",
    "mono-bold": "Bold stroke",
    "filled": "Icon",
    "broken-line": "Broken line",
    "doodle": "Doodle",
    "colored-outline": "Colored outline",
    "offset-fill": "Offset fill",
    "gradient-color": "Gradient shape",
    "flat-color": "Colored shape",
    "pixel": "Pictogram",
    "primitive": "Pictogram",
    "lineal-color": "Colored outline",
    "duotone": "Colored shape",
    "isometric": "Colored shape",
}
STYLE_REF_PRICE = 0.005  # per request attaching style_reference_urls instead of style_id

# every API model that returns editable SVG (model param must be one of these)
VECTOR_MODELS = (
    "recraftv2_vector",
    "recraftv3_vector",
    "recraftv4_vector",
    "recraftv4_1_vector",
    "recraftv4_1_utility_vector",
    "recraftv4_styles_vector",
    "recraftv4_1_pro_vector",
    "recraftv4_1_utility_pro_vector",
    "recraftv4_styles_pro_vector",
)


def draft_prompt(icon: dict, style, pack: dict, model: str | None = None) -> str:
    """Rich text-to-image prompt: icon brief, color world, style, rules.

    The brief is the single icon description (humans and agent share it);
    always names the main color and palette so Recraft lands in the pack's
    color world. Truncated to the model's prompt limit.
    """
    limit = prompt_limit(model or "")
    # one field: the brief describes the icon for humans AND the agent
    parts = [
        icon.get("brief") or icon.get("description") or "",
        f"{style.label} style",
        ", ".join(style.style_words[:4]),
    ]
    if icon.get("main_color"):
        parts.append(f"dominant color {icon['main_color']}")
    if style.palette:
        parts.append("palette " + ", ".join(style.palette[:5]))
    if style.avoid:
        parts.append("avoid: " + ", ".join(style.avoid[:3]))
    parts += pack.get("rules", [])[:3]
    parts.append("no background, transparent background, isolated icon on plain white")
    return ", ".join(p for p in parts if p)[:limit]


def price_per_image(model: str) -> float:
    """Estimated USD per generated image for a model (unknown → v4 price)."""
    return MODEL_PRICES.get(model, 0.08)


class RecraftError(Exception):
    """Any Recraft API or configuration failure."""


def models_path() -> Path:
    return Path.home() / ".config" / "iconpilot" / "models.toml"


def resolve_token(models_file: Path | None = None) -> str | None:
    """API token from env or models.toml; None when unconfigured."""
    env = os.environ.get("RECRAFT_API_TOKEN")
    if env:
        return env
    path = models_file or models_path()
    if not path.is_file():
        return None
    try:
        import tomllib

        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError) as exc:
        raise RecraftError(f"cannot read {path}: {exc}") from exc
    token = data.get("recraft", {}).get("token")
    return str(token) if token else None


def _data_url(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _request(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    """One HTTP call; raises RecraftError with the API's message on failure."""
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(  # fixed https host
        url, data=data, method=method
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:400]
        raise RecraftError(f"recraft {exc.code} on {path}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RecraftError(f"recraft request failed ({path}): {exc}") from exc


def create_style(token: str, svg_texts: list[str], match: str = "precise") -> dict:
    """Create a custom style from 1-10 reference SVGs; returns the style dict."""
    if not 1 <= len(svg_texts) <= 10:
        raise RecraftError(f"styles need 1-10 references, got {len(svg_texts)}")
    out = _request(
        token,
        "POST",
        "/styles",
        {
            "image_urls": [_data_url(s) for s in svg_texts],
            "model": "recraftv2_vector" if match == "regular" else "recraftv4_styles",
            "style": "icon",  # tell Recraft this style is for icons
            "match": match,
        },
    )
    if not out.get("id"):
        raise RecraftError(f"recraft returned no style id: {out}")
    return out


SHEET_PROMPT_SUFFIX = (
    ", arranged as a {g} by {g} grid of {n} distinct icons on one canvas. "
    "IMPORTANT: wrap each icon in its own group element like <g id='icon1'>, "
    "<g id='icon2'>, … <g id='icon{n}'> (row by row), each icon drawn at the "
    "same size centered in its cell. Plain empty background, no grid lines, "
    "no borders, no labels, no numbers"
)


def sheet_prompt(prompt: str, grid: int, model: str | None = None) -> str:
    """Wrap a drafting prompt so one image carries grid x grid variants."""
    g = int(grid)
    lim = prompt_limit(model or "")
    tail = SHEET_PROMPT_SUFFIX.format(g=g, n=g * g)
    return (prompt[: lim - len(tail)] + tail)[:lim]


def generate_refs_curated(
    token: str, style_id: str, subjects: list[str], grid: int = 3
) -> list[str]:
    """Generate style reference icons using Recraft's curated look.

    One sheet call with the curated `style` parameter (V2-vector icon
    styles), then split — cheap brand-consistent refs for round 0.
    """
    n = grid * grid
    prompt = batch_prompt(
        subjects[:n],
        1,
        f"Recraft curated '{CURATED_STYLE_MAP.get(style_id, 'Icon')}' icon style",
        grid,
    )
    payload: dict = {
        "prompt": prompt,
        "model": "recraftv2_vector",
        "n": 1,
        "size": "1:1",
        "response_format": "b64_json",
        "style": CURATED_STYLE_MAP.get(style_id, "Icon"),
    }
    out = _request(token, "POST", "/images/generations/vector", payload)
    import base64 as _b64

    svg = _b64.b64decode(out["data"][0]["b64_json"]).decode()
    return split_sheet(svg, grid, target=24.0)


def batch_prompt(
    icon_prompts: list[str], vpi: int, style_phrase: str, grid: int, model: str | None = None
) -> str:
    """One sheet prompt for several icons x variants per icon.

    Cell assignment is row-major: icon k occupies cells k*vpi+1 .. (k+1)*vpi.
    The named-group request (<g id='iconN'>) matches the splitter.
    """
    n = grid * grid
    assigns = []
    for k, desc in enumerate(icon_prompts):
        first, last = k * vpi + 1, (k + 1) * vpi
        assigns.append(f"cells {first}-{last}: {desc}")
    body = (
        f"{n} icons in a {grid} by {grid} grid, {vpi} distinct variants per subject. "
        + "; ".join(assigns)
        + f". Style: {style_phrase}."
    )
    tail = SHEET_PROMPT_SUFFIX.format(g=grid, n=n)
    lim = prompt_limit(model or "")
    return (body[: lim - len(tail)] + tail)[:lim]


def plan_batch(calls_by_style: dict[str, list[str]], vpi: int) -> list[dict]:
    """Pack (style -> icon prompts) into as few sheet calls as possible.

    Rules: one call per style (refs/style_id differ); never split an icon's
    variants across calls unless vpi alone exceeds the grid; grid is the
    smallest that fits (2x2/3x3/4x4; vpi<=4 avoids splits up to 16 cells).
    """
    vpi = max(1, min(int(vpi), 6))
    plans = []
    for style_id, prompts in calls_by_style.items():
        if not prompts:
            continue
        per_sheet = (
            max(1, (grid * grid) // max(vpi, 1)) if (grid := _fit_grid(len(prompts) * vpi)) else 1
        )
        chunks = [prompts[i : i + per_sheet] for i in range(0, len(prompts), per_sheet)]
        for chunk in chunks:
            grid = _fit_grid(len(chunk) * vpi)
            plans.append(
                {
                    "style": style_id,
                    "icons": chunk,
                    "vpi": vpi,
                    "grid": grid,
                    "cells": len(chunk) * vpi,
                }
            )
    return plans


def _fit_grid(cells: int) -> int:
    for g in (1, 2, 3, 4):
        if g * g >= cells:
            return g
    return 4


def _true_bbox(el) -> tuple[float, float, float, float] | None:
    """Bezier-aware bbox using svgpathtools (same as the gate)."""
    from svgpathtools import parse_path as _pp

    tag = el.tag.split("}")[-1]
    if tag == "path" and el.get("d"):
        try:
            p = _pp(el.get("d"))
            xmin, xmax, ymin, ymax = p.bbox()
            return (xmin, ymin, xmax, ymax)
        except (ValueError, TypeError):
            return None
    if tag == "circle" and el.get("cx") is not None:
        cx, cy, rr = float(el.get("cx", 0)), float(el.get("cy", 0)), float(el.get("r", 0))
        return (cx - rr, cy - rr, cx + rr, cy + rr)
    if tag == "rect" and el.get("x") is not None:
        x, y = float(el.get("x", 0)), float(el.get("y", 0))
        return (x, y, x + float(el.get("width", 0)), y + float(el.get("height", 0)))
    if tag == "ellipse" and el.get("cx") is not None:
        cx, cy = float(el.get("cx", 0)), float(el.get("cy", 0))
        rx, ry = float(el.get("rx", 0)), float(el.get("ry", 0))
        return (cx - rx, cy - ry, cx + rx, cy + ry)
    # polyline/polygon: parse points
    pts = el.get("points", "")
    if pts:
        nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", pts)]
        if len(nums) >= 4:
            xs, ys = nums[0::2], nums[1::2]
            return (min(xs), min(ys), max(xs), max(ys))
    return None


def split_sheet(svg: str, grid: int, target: float = 24.0) -> list[str]:
    """Split a grid SVG into per-cell candidate SVGs using true vector bboxes.

    Uses svgpathtools for bezier-aware bounding boxes (same as the gate),
    clusters elements by bbox center into grid cells, then extracts each
    cell as a separate SVG. Pure vector math — no rasterization.
    """
    from xml.etree import ElementTree as _ET

    g = int(grid)
    root = _ET.fromstring(strip_metadata(svg))
    vb = re.search(r"viewBox=\"([0-9.eE+-]+)[ ,]+([0-9.eE+-]+)[ ,]+([0-9.eE+-]+)", svg)
    if not vb:
        raise RecraftError("sheet svg has no viewBox")
    x0, y0, cw = float(vb.group(1)), float(vb.group(2)), float(vb.group(3))
    cell = cw / g

    # collect (element, bbox) pairs with true vector bboxes
    items: list[tuple[_ET.Element, tuple[float, float, float, float]]] = []
    for el in root.iter():
        if el is root:
            continue
        bb = _true_bbox(el)
        if bb is None:
            continue
        tag = el.tag.split("}")[-1]
        if tag in ("defs", "linearGradient", "radialGradient", "stop", "g"):
            continue
        items.append((el, bb))

    if not items:
        return []

    # cluster into cells by bbox center
    cells: dict[tuple[int, int], list[tuple[_ET.Element, tuple]]] = {}
    for el, bb in items:
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        gx = min(g - 1, max(0, int((cx - x0) // cell)))
        gy = min(g - 1, max(0, int((cy - y0) // cell)))
        cells.setdefault((gx, gy), []).append((el, bb))

    # extract each cell
    out = []
    for gx, gy in sorted(cells):
        entries = cells[(gx, gy)]
        bbs = [bb for _, bb in entries]
        ix0, iy0 = min(b[0] for b in bbs), min(b[1] for b in bbs)
        ix1, iy1 = max(b[2] for b in bbs), max(b[3] for b in bbs)
        w, h = max(ix1 - ix0, 1e-6), max(iy1 - iy0, 1e-6)
        k = (target * 0.85) / max(w, h)
        tx = (target - w * k) / 2 - ix0 * k
        ty = (target - h * k) / 2 - iy0 * k
        inner = _serialize([el for el, _ in entries])
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {target:g} {target:g}">'
            f'<g transform="translate({tx:.3f} {ty:.3f}) scale({k:.6f})">{inner}</g></svg>'
        )
    return out
    """Split a grid SVG into per-cell candidate SVGs.

    Prefers named groups when the model followed the prompt (<g id='iconN'>):
    deterministic extraction. Falls back to bbox clustering otherwise. Either
    way every output still has to pass the gate — and the agent redraws seeds.
    """
    grouped = _split_by_groups(svg, target)
    if grouped and len(grouped) >= grid:  # model complied well enough
        return grouped
    return _split_by_clustering(svg, grid, target)


def _split_by_groups(svg: str, target: float = 24.0) -> list[str]:
    """Extract <g id='iconN'> groups; returns [] when the model ignored it."""
    import re as _re
    from xml.etree import ElementTree as _ET

    try:
        root = _ET.fromstring(svg)
    except _ET.ParseError:
        return []
    out = []
    for g in root.iter():
        tag = g.tag.split("}")[-1]
        gid = g.get("id") or ""
        if tag != "g" or not _re.match(r"icon\d+$", gid):
            continue
        els = [e for e in g if e.tag.split("}")[-1] not in ("defs",)]
        if not els:
            continue
        bs = []
        for e in els:
            b = _el_bbox(e)
            if b:
                bs.append(b)
        if not bs:
            continue
        x0, y0 = min(b[0] for b in bs), min(b[1] for b in bs)
        x1, y1 = max(b[2] for b in bs), max(b[3] for b in bs)
        w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        k = (target * 0.85) / max(w, h)
        tx = (target - w * k) / 2 - x0 * k
        ty = (target - h * k) / 2 - y0 * k
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {target:g} {target:g}">'
            f'<g transform="translate({tx:.3f} {ty:.3f}) scale({k:.6f})">'
            f"{_serialize(els)}</g></svg>"
        )
    return out


def _el_bbox(el) -> tuple[float, float, float, float] | None:
    """Crude bbox from numeric attributes; None for non-drawing elements."""
    import re as _re

    tag = el.tag.split("}")[-1]
    if tag in ("defs", "linearGradient", "radialGradient", "stop"):
        return None
    if tag == "circle" and el.get("cx") is not None:
        cx, cy, rr = float(el.get("cx", 0)), float(el.get("cy", 0)), float(el.get("r", 0))
        return (cx - rr, cy - rr, cx + rr, cy + rr)
    if tag == "rect" and el.get("x") is not None:
        x, y = float(el.get("x", 0)), float(el.get("y", 0))
        return (x, y, x + float(el.get("width", 0)), y + float(el.get("height", 0)))
    nums = [float(n) for n in _re.findall(r"-?\d+\.?\d*", " ".join(el.attrib.values()))]
    if len(nums) < 4:
        return None
    xs, ys = nums[0::2], nums[1::2]
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _split_by_clustering(svg: str, grid: int, target: float = 24.0) -> list[str]:
    import re as _re
    from xml.etree import ElementTree as _ET

    g = int(grid)
    root = _ET.fromstring(svg)
    vb = _re.search(r"viewBox=\"([0-9.eE+-]+)[ ,]+([0-9.eE+-]+)[ ,]+([0-9.eE+-]+)", svg)
    if not vb:
        raise RecraftError("sheet svg has no viewBox")
    x0, y0, cw = float(vb.group(1)), float(vb.group(2)), float(vb.group(3))
    cell = cw / g

    # cluster elements into cells
    cells: dict[tuple[int, int], list[_ET.Element]] = {}
    for el in root.iter():
        if el is root:
            continue
        b = _el_bbox(el)
        if b is None:
            continue
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        gx = min(g - 1, max(0, int((cx - x0) // cell)))
        gy = min(g - 1, max(0, int((cy - y0) // cell)))
        cells.setdefault((gx, gy), []).append(el)

    out = []
    for gx, gy in sorted(cells):
        els = cells[(gx, gy)]
        # ink bbox of the cell
        bs = [_el_bbox(e) for e in els]
        bs = [b for b in bs if b]
        if not bs:
            continue
        ix0, iy0 = min(b[0] for b in bs), min(b[1] for b in bs)
        ix1, iy1 = max(b[2] for b in bs), max(b[3] for b in bs)
        w, h = max(ix1 - ix0, 1e-6), max(iy1 - iy0, 1e-6)
        k = (target * 0.85) / max(w, h)  # 15% live-area margin
        tx = (target - w * k) / 2 - ix0 * k
        ty = (target - h * k) / 2 - iy0 * k
        inner = _serialize(els)
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {target:g} {target:g}">'
            f'<g transform="translate({tx:.3f} {ty:.3f}) scale({k:.6f})">{inner}</g></svg>'
        )
    return out


def _serialize(els) -> str:
    """Serialize elements without namespace prefixes (svg:rect → rect)."""
    import re as _re2
    from xml.etree import ElementTree as _ET

    _ET.register_namespace("", "http://www.w3.org/2000/svg")
    out = "".join(_ET.tostring(e, encoding="unicode") for e in els)
    out = _re2.sub(r"</?svg:", lambda m: m.group(0).replace("svg:", ""), out)
    out = _re2.sub(r'\sxmlns:svg="[^"]*"', "", out)
    return out


def _svg_data_url(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def generate(
    token: str,
    prompt: str,
    n: int = 4,
    style_id: str | None = None,
    model: str | None = None,
    reference_urls: list[str] | None = None,
    curated_style: str | None = None,
) -> list[str]:
    """Generate n SVG candidates; returns raw SVG texts (native Recraft grid).

    reference_urls: style references attached directly to the request
    (data URLs ok; +$0.005/request instead of a style_id). V4-only.
    curated_style: a curated style NAME for V2/V3 models (e.g. "Outline").
    """
    if not 1 <= n <= 6:
        raise RecraftError(f"n must be 1-6, got {n}")
    if reference_urls and style_id:
        raise RecraftError("pass style_id OR reference_urls, not both")

    if model and "v4" not in model:
        # V2/V3: use the `style` parameter with a curated name, drop refs
        reference_urls = None
        if curated_style:
            pass  # will be set in payload below
    elif reference_urls:
        pass  # V4: refs are fine
    model = model or (DEFAULT_MODEL if (style_id or reference_urls) else FALLBACK_MODEL)
    if model not in VECTOR_MODELS:
        raise RecraftError(f"model must be a vector model, got '{model}'")
    payload: dict = {
        "prompt": prompt,
        "model": model,
        "n": n,
        "size": "1:1",  # vector models accept ratios only
        "response_format": "b64_json",
    }
    if style_id:
        payload["style_id"] = style_id
        payload["style_match"] = "precise"
    if reference_urls:
        payload["style_reference_urls"] = reference_urls
    elif curated_style and model and "v4" not in model:
        payload["style"] = curated_style
    out = _request(token, "POST", "/images/generations/vector", payload)
    svgs: list[str] = []
    for item in out.get("data", []):
        b64 = item.get("b64_json")
        if not b64:
            raise RecraftError("recraft returned an image without b64_json")
        svgs.append(base64.b64decode(b64).decode())
    if not svgs:
        raise RecraftError(f"recraft returned no images: {json.dumps(out)[:200]}")
    return svgs


# --- normalization -----------------------------------------------------------


def _viewbox_size(svg: str) -> float:
    """Source grid size: from viewBox, else width/height, else 1024."""
    m = re.search(r'viewBox="([\d.eE+-]+)[ ,]+([\d.eE+-]+)[ ,]+([\d.eE+-]+)', svg)
    if m:
        return float(m.group(3))
    m = re.search(r'width="([\d.]+)', svg)
    if m:
        return float(m.group(1))
    return 1024.0


def _inner(svg: str) -> str:
    """Content between the outer <svg> tags."""
    m = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.DOTALL)
    return m.group(1) if m else svg


def strip_metadata(svg: str) -> str:
    """Remove Recraft's C2PA watermark, comments, and non-drawing elements."""
    import re as _re

    # strip <metadata>…</metadata> (C2PA manifest, provenance data)
    svg = _re.sub(r"<metadata[\s\S]*?</metadata>", "", svg)
    # strip <title> and <desc>
    svg = _re.sub(r"<title[\s\S]*?</title>", "", svg)
    svg = _re.sub(r"<desc[\s\S]*?</desc>", "", svg)
    # strip XML comments
    svg = _re.sub(r"<!--[\s\S]*?-->", "", svg)
    # strip processing instructions
    svg = _re.sub(r"<\?[^>]*\?>", "", svg)
    # strip full-canvas background rects (Recraft sometimes adds these)
    svg = _re.sub(
        r'<rect[^>]*width="(?:1024|1000|\d{3,})"[^>]*height="(?:1024|1000|\d{3,})"[^>]*/>', "", svg
    )
    # strip large filled rects that cover the whole viewBox
    svg = _re.sub(
        r'<rect[^>]*fill="(?:#(?:fff|f00|000|ffffff|000000)[^"]*)"[^>]*width="\d{2,}"[^>]*/>',
        "",
        svg,
    )
    return svg.strip()


def normalize(svg: str, target_viewbox: str) -> str:
    """Rescale a Recraft SVG (native ~1024 grid) onto the pack's grid.

    Strips C2PA metadata first (Recraft embeds provenance watermarks that
    break renderers), then wraps content in ``<g transform="scale(k)">``
    and rewrites the viewBox. Packed packs that forbid ``<g>`` in
    allowed_elements will fail the gate — by design: seeds are redrawn
    by the agent before certification.
    """
    svg = strip_metadata(svg)
    tm = re.match(r"0 0 ([\d.]+) ([\d.]+)", target_viewbox.strip())
    if not tm:
        raise RecraftError(f"unsupported target viewBox: {target_viewbox!r}")
    target = float(tm.group(1))
    source = _viewbox_size(svg)
    if source <= 0:
        raise RecraftError("cannot determine source grid size")
    k = round(target / source, 6)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{target_viewbox}">'
        f'<g transform="scale({k})">{_inner(svg)}</g></svg>'
    )
