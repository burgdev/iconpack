"""Built-in style registry and three-tier style resolution.

Tiers (lowest to highest precedence):
  1. BUILTIN_STYLES shipped with iconpilot
  2. user registry  ~/.config/iconpilot/styles.toml
  3. pack-local     pack.json "styles" block

A style carries BOTH gate thresholds (max_nodes, min_gap, stroke/fill rules)
and prompt vocabulary (style_words / avoid) — one definition drives gates and
prompts. LLMs may reference or extend styles; they never author thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from tomllib import load as tomllib_load

CONSTRUCTIONS = ("outline", "solid", "outline+fill", "hand-drawn")
COLOR_MODES = ("mono", "bicolor", "color", "gradient")
DETAILS = ("low", "medium", "high")


@dataclass(frozen=True)
class Style:
    id: str
    label: str
    construction: str
    color_mode: str
    detail: str
    stroke: dict | None = None  # {"width": float, "linecap": str, "linejoin": str}
    fill: str | None = None  # "none" | "currentColor" | "accent"
    weight: str | None = None  # thin | regular | bold
    terminals: str = "round"
    max_nodes: int = 40
    min_gap: float = 1.5
    style_words: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    render_sizes: tuple[int, ...] = (16, 24, 48)
    size: int | None = None  # design grid px; None = inherit the pack spec viewBox
    palette: tuple[str, ...] = ()  # allowed hex colors for colored styles; empty = any
    guidance: str | None = None  # optional freeform prose rendered into context when set
    gate: dict | None = None  # per-check toggles, e.g. {"min_gap": false} for broken lines
    note: str | None = None

    def __post_init__(self) -> None:
        if self.construction not in CONSTRUCTIONS:
            raise ValueError(f"style '{self.id}': unknown construction '{self.construction}'")
        if self.color_mode not in COLOR_MODES:
            raise ValueError(f"style '{self.id}': unknown color_mode '{self.color_mode}'")
        if self.detail not in DETAILS:
            raise ValueError(f"style '{self.id}': unknown detail '{self.detail}'")

    def as_dict(self) -> dict:
        d: dict = {}
        for k, v in self.__dict__.items():
            if v is None or v == ():
                continue
            if isinstance(v, tuple):
                v = list(v)
            d[k] = v
        return d


def _s(style_id: str, **kw) -> Style:
    return Style(id=style_id, **kw)


BUILTIN_STYLES: dict[str, Style] = {
    s.id: s
    for s in [
        _s(
            "primitive",
            label="Primitive",
            construction="solid",
            color_mode="mono",
            detail="low",
            fill="currentColor",
            terminals="round",
            max_nodes=14,
            min_gap=2.5,
            style_words=(
                "ultra-minimal form",
                "2-3 shapes maximum",
                "generous counters",
                "readable at 12px",
            ),
            avoid=("fine detail", "thin strokes", "texture", "text", "perspective"),
            render_sizes=(12, 16, 24),
            size=24,
        ),
        _s(
            "mono-line",
            label="Mono line",
            construction="outline",
            color_mode="mono",
            detail="medium",
            weight="regular",
            stroke={"width": 2, "linecap": "round", "linejoin": "round"},
            fill="none",
            style_words=(
                "geometric",
                "uniform 2px stroke",
                "round terminals",
                "flat single plane",
            ),
            avoid=("gradients", "3D", "text", "hairlines", "perspective", "shading"),
            size=24,
        ),
        _s(
            "mono-line-thin",
            label="Mono line thin",
            construction="outline",
            color_mode="mono",
            detail="medium",
            weight="thin",
            stroke={"width": 1.5, "linecap": "round", "linejoin": "round"},
            fill="none",
            max_nodes=44,
            min_gap=1.25,
            style_words=("elegant", "airy", "uniform 1.5px stroke"),
            avoid=("gradients", "dense detail", "text"),
        ),
        _s(
            "mono-bold",
            label="Mono bold",
            construction="outline",
            color_mode="mono",
            detail="low",
            weight="bold",
            stroke={"width": 2.5, "linecap": "round", "linejoin": "round"},
            fill="none",
            max_nodes=28,
            min_gap=2.0,
            style_words=("bold", "chunky", "high contrast at small sizes"),
            avoid=("fine detail", "dense interiors", "text"),
        ),
        _s(
            "filled",
            label="Filled",
            construction="solid",
            color_mode="mono",
            detail="medium",
            fill="currentColor",
            max_nodes=40,
            style_words=(
                "solid silhouette",
                "crisp counters cut with even-odd fill",
                "punchy at 16px",
            ),
            avoid=("hairline strokes", "texture", "half tones"),
        ),
        _s(
            "duotone",
            label="Duotone",
            palette=("#000000", "#8C8C8C"),
            construction="solid",
            color_mode="bicolor",
            detail="medium",
            fill="currentColor",
            max_nodes=48,
            min_gap=1.25,
            style_words=(
                "two tones",
                "primary shape plus accent layer at ~45% opacity",
                "depth without noise",
            ),
            avoid=("more than two tones", "gradients", "texture"),
        ),
        _s(
            "lineal-color",
            label="Lineal color",
            palette=("#C05621", "#2B6CB0", "#4A5568", "#E2E8F0"),
            construction="outline+fill",
            color_mode="color",
            detail="high",
            stroke={"width": 2, "linecap": "round", "linejoin": "round"},
            fill="pack-palette",
            max_nodes=60,
            min_gap=1.25,
            style_words=(
                "colored flat fills",
                "dark outer stroke",
                "flat colors",
                "playful but precise",
            ),
            avoid=("gradients", "shading", "text", "photo-realism"),
            size=48,
        ),
        _s(
            "flat-color",
            label="Flat color",
            palette=("#C05621", "#2B6CB0", "#2F855A", "#4A5568"),
            construction="solid",
            color_mode="color",
            detail="high",
            fill="pack-palette",
            max_nodes=60,
            min_gap=1.25,
            style_words=("flat colored shapes", "no outline", "bright, friendly"),
            avoid=("outlines", "gradients", "shading"),
            size=48,
        ),
        _s(
            "broken-line",
            label="Broken line",
            construction="outline",
            color_mode="mono",
            detail="medium",
            stroke={"width": 2, "linecap": "round", "linejoin": "round"},
            fill="none",
            max_nodes=36,
            gate={"min_gap": False},  # gaps ARE the style
            style_words=("outline with intentional gaps", "sketch energy", "rhythm of breaks"),
            avoid=("closed heavy outlines", "fills", "texture"),
        ),
        _s(
            "colored-outline",
            label="Colored outline",
            palette=("#2B6CB0", "#C05621", "#2F855A"),
            construction="outline+fill",
            color_mode="color",
            detail="medium",
            stroke={"width": 2, "linecap": "round", "linejoin": "round"},
            fill="pack-palette",
            size=48,
            max_nodes=48,
            style_words=("currentColor line work", "one or two small color pops", "line-dominant"),
            avoid=("full fills", "gradients", "many colors"),
        ),
        _s(
            "isometric",
            label="Isometric",
            palette=("#E8A87C", "#C05621", "#7B341E"),
            construction="solid",
            color_mode="color",
            detail="medium",
            fill="pack-palette",
            size=48,
            max_nodes=60,
            min_gap=1.0,
            style_words=("30-degree isometric planes", "three-face shading", "precise edges"),
            avoid=("perspective", "curves where planes meet", "gradients"),
        ),
        _s(
            "offset-fill",
            label="Offset fill",
            palette=("#C05621", "#4A5568", "#E2E8F0"),
            construction="solid",
            color_mode="color",
            detail="medium",
            fill="pack-palette",
            size=48,
            max_nodes=60,
            gate={"min_gap": False},  # layered duplicates sit close by design
            style_words=("flat shape with offset twin", "fake depth", "sticker-like drop layer"),
            avoid=("gradients", "outlines", "blur"),
        ),
        _s(
            "pixel",
            label="Pixel",
            construction="solid",
            color_mode="mono",
            detail="low",
            fill="currentColor",
            size=24,
            max_nodes=480,
            min_gap=0.5,
            style_words=("chunky pixel grid", "8-bit clarity", "2px units"),
            avoid=("curves", "diagonals", "anti-aliasing detail"),
        ),
        _s(
            "doodle",
            label="Doodle",
            construction="outline",
            color_mode="mono",
            detail="medium",
            stroke={"width": 2, "linecap": "round", "linejoin": "round"},
            fill="none",
            max_nodes=40,
            gate={"min_gap": False, "grid": False},  # wobble is the point
            style_words=("hand-drawn wobble", "sketchy confidence", "slightly off geometry"),
            avoid=("perfect geometry", "fills", "rulers"),
        ),
        _s(
            "gradient-color",
            label="Gradient color",
            palette=("#2B6CB0", "#63B3ED"),
            construction="solid",
            color_mode="gradient",
            detail="high",
            fill="gradient",
            max_nodes=60,
            note="Marketing sizes only — gradients smear at 16px; gate flags render at 16.",
            render_sizes=(24, 48),
            size=48,
        ),
    ]
}


def user_styles_path() -> Path:
    return Path.home() / ".config" / "iconpilot" / "styles.toml"


def bundled_refs_path() -> Path:
    """Reference icons shipped with the tool, per style id."""
    return Path(__file__).parent / "style_refs"


def style_refs(pack_dir: Path, style_id: str) -> list[Path]:
    """Reference icons for a style: pack-local (.style-refs/) beat bundled."""
    own = sorted((pack_dir / ".style-refs" / style_id).glob("*.svg"))
    if own:
        return own
    bundled = sorted((bundled_refs_path() / style_id).glob("*.svg"))
    return bundled


def snapshot_style(pack: dict, style_id: str) -> None:
    """Copy the resolved style definition into pack.styles.

    Packs stay independent of registry edits: once used, the style lives in
    the pack. 'extends' keeps the lineage traceable.
    """
    resolved = resolve_styles(pack.get("styles"))
    if style_id in (pack.get("styles") or {}):
        return  # already snapshotted or user-customized
    st = resolved.get(style_id)
    if st is None:
        raise ValueError(f"unknown style '{style_id}'")
    d = st.as_dict()
    d.pop("id", None)
    d["extends"] = style_id
    pack.setdefault("styles", {})[style_id] = d


def _style_from_dict(style_id: str, d: dict, base: Style | None) -> Style:
    """Build a Style from a config/pack dict, merged over a base when given."""
    src = base.as_dict() if base else {"id": style_id}
    src.update({k: v for k, v in d.items() if k != "id"})
    src["id"] = style_id
    for tuple_key in ("style_words", "avoid", "render_sizes", "palette"):
        if tuple_key in src and isinstance(src[tuple_key], list):
            src[tuple_key] = tuple(src[tuple_key])
    if "stroke" in src and isinstance(src["stroke"], dict) and base and base.stroke:
        merged = dict(base.stroke)
        merged.update(src["stroke"])
        src["stroke"] = merged
    return Style(**src)


def resolve_styles(pack_local: dict | None = None) -> dict[str, Style]:
    """Resolve the style registry: built-ins < user config < pack-local."""
    registry: dict[str, Style] = dict(BUILTIN_STYLES)

    path = user_styles_path()
    if path.is_file():
        with path.open("rb") as fh:
            user = tomllib_load(fh)
        for style_id, d in (user.get("styles") or {}).items():
            registry[style_id] = _style_from_dict(style_id, d, registry.get(style_id))

    for style_id, d in (pack_local or {}).items():
        d = dict(d)
        extends = d.pop("extends", None)
        base = registry.get(extends) if extends else registry.get(style_id)
        if extends and base is None:
            raise ValueError(f"style '{style_id}': unknown extends '{extends}'")
        registry[style_id] = _style_from_dict(style_id, d, base)

    # enforced default: mono styles always carry a black palette — Recraft
    # styles bake it in at seed time; final pack icons use currentColor
    # (theme-colorable) regardless. An explicit palette still wins.
    for style_id, style in list(registry.items()):
        if style.color_mode == "mono" and not style.palette:
            registry[style_id] = replace(style, palette=("#000000",))
    return registry
