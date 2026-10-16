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
    # Recraft priority order (earlier = stronger): subject → color → style
    # → rules → layout → avoids
    parts = [f"vector icon of {icon.get('brief') or icon.get('description') or ''}"]
    if icon.get("main_color"):
        parts.append(f"dominant color {icon['main_color']}")
    if style.palette:
        parts.append("palette " + ", ".join(style.palette[:5]))
    parts += [f"{style.label} icon style", ", ".join(style.style_words[:4])]
    parts += pack.get("rules", [])[:3]
    parts.append("one centered icon, isolated on plain white background, no scene")
    if style.avoid:
        parts.append("avoid: " + ", ".join(style.avoid[:3]))
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


def sheet_prompt(prompt: str, grid: int, model: str | None = None) -> str:
    """One canvas, g×g cells: every cell a different take on the SAME icon.

    Same-subject semantics lead the prompt (earlier = higher priority per
    Recraft's guide); the draft prompt is embedded as the icon description;
    layout constraints close.
    """
    g = int(grid)
    n = g * g
    lim = prompt_limit(model or "")
    head = (
        f"Icon design sheet: {n} different design variations of ONE icon — "
        "every cell shows the same subject, each cell a different take on it "
        "(vary composition, proportions and detail arrangement, keep the "
        f"subject identical). {g} by {g} grid on one canvas, one variation "
        "per cell. Icon: "
    )
    tail = (
        " Generous clean margins between cells — no touching, no "
        "overlapping, each icon fully inside its own cell. Plain empty "
        "background, no grid lines, no borders, no labels, no numbers, "
        "no background color."
    )
    return (head + prompt[: lim - len(head) - len(tail)] + tail)[:lim]


def generate_refs_curated(
    token: str, style_id: str, subjects: list[str], grid: int = 3
) -> list[str]:
    """Generate style reference icons using Recraft's curated look.

    One sheet call with the curated `style` parameter (V2-vector icon
    styles), then split — cheap brand-consistent refs for round 0.
    """
    n = grid * grid
    prompt = pack_sheet_prompt(
        subjects[:n],
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


def pack_sheet_prompt(
    briefs: list[str], style_phrase: str, grid: int, model: str | None = None
) -> str:
    """One sheet of DIFFERENT icons, one per cell — the proven grid pattern.

    Variation happens ACROSS the n generated sheets (same icons, different
    takes), never within one image. Cell k of every sheet maps to icon k.
    """
    g = int(grid)
    cells = "; ".join(f"cell {i + 1}: {b}" for i, b in enumerate(briefs))
    body = (
        f"Icon set sheet: {len(briefs)} distinct icons in a {g} by {g} grid, "
        f"one icon per cell — {cells}. Style: {style_phrase}; same stroke "
        "weight, corner treatment and color system across all cells. "
        "Generous clean margins between cells — no touching, no overlapping. "
        "Plain empty background, no grid lines, no borders, no labels, no text."
    )
    return body[: prompt_limit(model or "")]


def pack_grid(n_icons: int) -> int:
    """Grid for a pack sheet: 2×2 for ≤4 icons, else 3×3 (chunk >9 upstream)."""
    return 2 if n_icons <= 4 else 3


def _serialize(els) -> str:
    """Serialize elements without namespace prefixes (svg:rect → rect)."""
    import re as _re2
    from xml.etree import ElementTree as _ET

    _ET.register_namespace("", "http://www.w3.org/2000/svg")
    out = "".join(_ET.tostring(e, encoding="unicode") for e in els)
    out = _re2.sub(r"</?svg:", lambda m: m.group(0).replace("svg:", ""), out)
    out = _re2.sub(r'\sxmlns:svg="[^"]*"', "", out)
    return out


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
