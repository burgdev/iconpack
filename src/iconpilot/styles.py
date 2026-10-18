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
        # ── reference-based styles (bundled refs from the design source) ──
        _s(
            "mono-line",
            label="Mono line",
            size=24,
            render_sizes=(24,),
            construction="outline",
            color_mode="mono",
            detail="medium",
            stroke={"width": 2, "linecap": "round", "linejoin": "round"},
            fill="none",
            max_nodes=48,
            min_gap=1.25,
            style_words=("clean line work", "uniform stroke", "no fill"),
            avoid=("filled areas", "double strokes"),
        ),
        _s(
            "mono-filled",
            label="Mono filled",
            size=24,
            render_sizes=(24,),
            construction="solid",
            color_mode="mono",
            detail="medium",
            fill="currentColor",
            max_nodes=48,
            min_gap=1.0,
            style_words=("solid silhouette", "single color fill", "no strokes"),
            avoid=("internal outlines", "gradients"),
        ),
        _s(
            "color-flat",
            label="Color flat",
            size=48,
            render_sizes=(24, 48),
            construction="solid",
            color_mode="color",
            detail="medium",
            fill="pack-palette",
            max_nodes=64,
            min_gap=1.0,
            palette=(
                "#d3d3d3",
                "#321b41",
                "#ffb02e",
                "#9b9b9b",
                "#636363",
                "#f92f60",
                "#00a6ed",
                "#212121",
                "#7d4533",
                "#0074ba",
            ),
            style_words=("flat fills", "2-4 colors per icon", "no gradients", "no outlines"),
            avoid=("gradients", "outlines", "shading"),
        ),
        _s(
            "color-broken-line",
            label="Color broken line",
            size=48,
            render_sizes=(24, 48),
            construction="solid",
            color_mode="color",
            detail="high",
            fill="pack-palette",
            max_nodes=72,
            min_gap=1.0,
            gate={"min_gap": False},
            palette=(
                "#e6e6e6",
                "#cccccc",
                "#49db95",
                "#ffca6c",
                "#4d4d4d",
                "#f2f2f2",
                "#dd852c",
                "#3cc681",
                "#e2ae5a",
                "#333333",
            ),
            style_words=(
                "segmented color shapes",
                "deliberate gaps between segments",
                "flat fills",
                "one accent color per icon",
            ),
            avoid=("continuous outlines", "gradients", "more than four colors"),
        ),
        _s(
            "color-gradient",
            label="Color gradient",
            size=48,
            render_sizes=(24, 48),
            construction="solid",
            color_mode="gradient",
            detail="high",
            fill="gradient",
            max_nodes=72,
            min_gap=1.0,
            palette=(
                "#70777d",
                "#eb4824",
                "#ffcd0f",
                "#ff6f47",
                "#ff921f",
                "#9c6cfe",
                "#2764e7",
                "#29c3ff",
                "#5b2ab5",
                "#4a43cb",
            ),
            style_words=("gradient fills", "smooth two-hue blends", "flat shape logic"),
            avoid=("hard shading", "outlines", "texture"),
        ),
        # ── geometric / kept styles ──
        _s(
            "color-isometric",
            label="Color isometric",
            size=48,
            render_sizes=(48,),
            construction="solid",
            color_mode="color",
            detail="high",
            fill="pack-palette",
            max_nodes=72,
            min_gap=1.0,
            palette=(
                "#4a86c5",
                "#2b6cb0",
                "#1f5894",
                "#2f855a",
                "#236443",
                "#4bb07d",
                "#e08a4a",
                "#c05621",
            ),
            style_words=("isometric projection", "three faces per volume", "flat shading per face"),
            avoid=("perspective", "curved volumes"),
        ),
        _s(
            "color-offset-fill",
            label="Color offset fill",
            size=48,
            render_sizes=(24, 48),
            construction="outline+fill",
            color_mode="color",
            detail="medium",
            stroke={"width": 2, "linecap": "round", "linejoin": "round"},
            fill="pack-palette",
            max_nodes=56,
            min_gap=1.0,
            palette=(
                "#e8a825",
                "#2b6cb0",
                "#2f855a",
                "#c05621",
            ),
            style_words=("outline with offset color fill", "duotone layering"),
            avoid=("aligned fill", "more than two colors"),
        ),
        _s(
            "mono-primitive",
            label="Mono primitive",
            size=24,
            render_sizes=(24,),
            construction="solid",
            color_mode="mono",
            detail="low",
            fill="currentColor",
            max_nodes=20,
            min_gap=2.0,
            style_words=(
                "geometric primitives",
                "circle square triangle only",
                "extreme reduction",
            ),
            avoid=("detail", "curves beyond primitives"),
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
    """Build a Style from a config/pack dict, merged over a base when given.

    Unknown keys (snapshot extras like recraft_style_id/recraft_style_hash,
    extends lineage) are ignored — they live in the pack snapshot, not the
    Style dataclass.
    """
    import dataclasses as _dc

    fields = {f.name for f in _dc.fields(Style)}
    src = base.as_dict() if base else {"id": style_id}
    src.update({k: v for k, v in d.items() if k != "id" and k in fields})
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
