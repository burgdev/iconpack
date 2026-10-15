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


def draft_prompt(icon: dict, style, pack: dict) -> str:
    """Rich text-to-image prompt: icon brief, color world, style, rules.

    The brief is the single icon description (humans and agent share it);
    always names the main color and palette so Recraft lands in the pack's
    color world.
    """
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
    return ", ".join(p for p in parts if p)[:1000]


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
            "model": "recraftv4_styles",
            "match": match,
        },
    )
    if not out.get("id"):
        raise RecraftError(f"recraft returned no style id: {out}")
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
) -> list[str]:
    """Generate n SVG candidates; returns raw SVG texts (native Recraft grid).

    reference_urls: style references attached directly to the request
    (data URLs ok; +$0.005/request instead of a style_id).
    """
    if not 1 <= n <= 6:
        raise RecraftError(f"n must be 1-6, got {n}")
    if reference_urls and style_id:
        raise RecraftError("pass style_id OR reference_urls, not both")
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
    out = _request(token, "POST", "/images/generations", payload)
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


def normalize(svg: str, target_viewbox: str) -> str:
    """Rescale a Recraft SVG (native ~1024 grid) onto the pack's grid.

    Wraps content in ``<g transform="scale(k)">`` and rewrites the viewBox.
    Packed packs that forbid ``<g>`` in allowed_elements will fail the gate —
    by design: seeds are redrawn by the agent before certification.
    """
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
