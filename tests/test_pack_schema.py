"""Schema + semantic validator + gate slice tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from iconpilot.context import build_context
from iconpilot.gate.run import run_gate
from iconpilot.pack import PackError, _json_schema, load_pack
from iconpilot.styles import BUILTIN_STYLES, resolve_styles
from iconpilot.validate import validate_pack

SPEC = {
    "viewBox": "0 0 24 24",
    "live_area": {"padding": 2},
    "stroke": {"width": 2, "linecap": "round", "linejoin": "round"},
    "fill": "none",
    "allowed_elements": ["path", "circle", "rect", "line", "polyline", "polygon", "ellipse"],
    "precision": 0.5,
}


def example_pack() -> dict:
    return {
        "schema": 2,
        "name": "outdoor-poi",
        "version": "0.1.0",
        "provenance": {"created_by": "user"},
        "spec": copy.deepcopy(SPEC),
        "styles": {},
        "icons": {
            "hut": {
                "brief": "Alpine hut: steep roof, small door, no chimney",
                "prompt": "gable roof slightly asymmetric",
                "main_color": "#346751",
                "variants": {
                    "primitive": {"style": "primitive", "status": "todo", "anchor": True},
                    "mono": {"style": "mono-line", "status": "approved"},
                    "color": {
                        "style": "lineal-color",
                        "status": "in_review",
                        "reference": "hut#mono",
                    },
                },
            },
            "selfhut": {
                "brief": "Self-catering hut: hut plus cutlery mark",
                "variants": {
                    "primitive": {"link": "hut#primitive"},
                    "mono": {"style": "mono-line", "status": "todo", "reference": "hut#mono"},
                },
            },
        },
    }


# --- schema -----------------------------------------------------------------


def test_example_pack_schema_valid() -> None:
    jsonschema.validate(example_pack(), _json_schema())


def test_variant_cannot_be_both_style_and_link() -> None:
    bad = example_pack()
    bad["icons"]["selfhut"]["variants"]["mono"] = {
        "style": "mono-line",
        "status": "todo",
        "link": "hut#mono",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _json_schema())


def test_linked_variant_carries_no_state() -> None:
    bad = example_pack()
    bad["icons"]["selfhut"]["variants"]["primitive"] = {
        "link": "hut#primitive",
        "status": "approved",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _json_schema())


def test_tags_removed_in_v2() -> None:
    bad = example_pack()
    bad["icons"]["hut"]["tags"] = ["building"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _json_schema())


# --- semantic validator -----------------------------------------------------


def test_example_pack_semantically_valid() -> None:
    assert validate_pack(example_pack(), resolve_styles()) == []


def test_dangling_link_detected() -> None:
    bad = example_pack()
    bad["icons"]["selfhut"]["variants"]["primitive"] = {"link": "gone#primitive"}
    errs = validate_pack(bad, resolve_styles())
    assert any("dangling link" in e for e in errs)


def test_unknown_style_detected() -> None:
    bad = example_pack()
    bad["icons"]["hut"]["variants"]["mono"]["style"] = "no-such-style"
    errs = validate_pack(bad, resolve_styles())
    assert any("unknown style" in e for e in errs)


def test_dependency_cycle_detected() -> None:
    bad = example_pack()
    # hut#color -> hut#mono, hut#mono -> hut#color
    bad["icons"]["hut"]["variants"]["mono"]["reference"] = "hut#color"
    errs = validate_pack(bad, resolve_styles())
    assert any("cycle" in e for e in errs)


def test_color_link_requires_equal_main_color() -> None:
    bad = example_pack()
    bad["icons"]["hut"]["main_color"] = "#346751"
    bad["icons"]["selfhut"]["main_color"] = "#bf211e"
    bad["icons"]["selfhut"]["variants"]["color"] = {"link": "hut#color"}
    errs = validate_pack(bad, resolve_styles())
    assert any("main_color differs" in e for e in errs)


def test_designer_pack_must_be_todo_only() -> None:
    bad = example_pack()
    bad["provenance"] = {"created_by": "designer"}
    # hut#mono is 'approved' — forbidden for LLM-authored packs
    errs = validate_pack(bad, resolve_styles())
    assert any("todo-only" in e for e in errs)


def test_multiple_anchors_rejected() -> None:
    bad = example_pack()
    bad["icons"]["hut"]["variants"]["mono"]["anchor"] = True
    errs = validate_pack(bad, resolve_styles())
    assert any("multiple anchors" in e for e in errs)


# --- gate slice ---------------------------------------------------------------

VALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 11 L12 4 L20 11"/>
  <path d="M6 9.5 L6 20 L18 20 L18 9.5"/>
  <path d="M10 20 L10 15 L14 15 L14 20"/>
</svg>
"""

INVALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"
  fill="#f00" stroke="#123456" stroke-width="2">
  <text x="2" y="10" style="font-size:4px">hut</text>
  <g id="layer" transform="translate(1,1)"><path d="M2 40 L24 10 L46 40 Z"/></g>
</svg>
"""


@pytest.fixture
def pack_dir(tmp_path: Path) -> Path:
    d = tmp_path / "outdoor-poi"
    d.mkdir()
    (d / "pack.json").write_text(json.dumps(example_pack()))
    return d


def test_gate_passes_valid_svg(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "hut.svg"
    svg.write_text(VALID_SVG)
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert report.passed, report.errors
    assert report.metrics["node_count"] <= styles["mono-line"].max_nodes
    assert set(report.metrics["ink_ratio"]) == set(styles["mono-line"].render_sizes)
    assert 0.0 < report.metrics["ink_ratio"][24] < 0.9
    assert len(report.metrics["phash"]) == 16  # 64-bit phash as hex


def test_gate_empty_render_fails(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "empty.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2">'
        '<path d="M4 11 M12 4 M20 11"/></svg>'
    )
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert any("no ink" in e for e in report.errors)


def test_similarity_detects_duplicate_and_difference(tmp_path: Path, pack_dir: Path) -> None:
    from iconpilot.render.render import hamming, hash_file

    dupe = pack_dir / "icons" / "selfhut" / "primitive.svg"
    dupe.parent.mkdir(parents=True)
    dupe.write_text(VALID_SVG)
    original = tmp_path / "hut.svg"
    original.write_text(VALID_SVG)
    other = tmp_path / "other.svg"
    other.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="8"/></svg>'
    )

    h_orig = hash_file(original)
    assert hamming(h_orig, hash_file(dupe)) == 0
    assert hamming(h_orig, hash_file(other)) > 8


def test_gate_fails_invalid_svg(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "bad.svg"
    svg.write_text(INVALID_SVG)
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert not report.passed
    joined = " | ".join(report.errors)
    assert "viewBox" in joined
    assert "<text>" in joined
    assert "inline style" in joined
    assert "transform" in joined
    assert "currentColor" in joined


def test_gate_bbox_outside_live_area(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "wide.svg"
    svg.write_text(VALID_SVG.replace("M4 11 L12 4 L20 11", "M1 11 L12 1 L23 11"))
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert any("live area" in e for e in report.errors)


def test_load_pack_raises_on_semantic_error(tmp_path: Path) -> None:
    d = tmp_path / "badpack"
    d.mkdir()
    bad = example_pack()
    bad["icons"]["hut"]["variants"]["mono"]["style"] = "no-such-style"
    (d / "pack.json").write_text(json.dumps(bad))
    with pytest.raises(PackError, match="unknown style"):
        load_pack(d / "pack.json")


def test_builtin_styles_complete() -> None:
    expected = {
        "primitive",
        "mono-line",
        "mono-line-thin",
        "mono-bold",
        "filled",
        "duotone",
        "lineal-color",
        "flat-color",
        "gradient-color",
    }
    assert expected == set(BUILTIN_STYLES)


# --- 0.0.1 backlog: enforced checks ------------------------------------------

NEAR_MISS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 6 L19 6"/><path d="M5 6.8 L19 6.8"/></svg>'
)

OFFGRID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5.13 6 L19 6 L19 18"/></svg>'
)


def test_gate_flags_near_miss_gap(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "near.svg"
    svg.write_text(NEAR_MISS_SVG)
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert any("near-miss gap" in e for e in report.errors)


def test_gate_allows_touching_strokes(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "touch.svg"
    svg.write_text(NEAR_MISS_SVG.replace("6.8", "6.25"))  # 0.25 ≤ contact eps
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert not any("near-miss" in e for e in report.errors)


def test_gate_flags_offgrid_coordinates(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "off.svg"
    svg.write_text(OFFGRID_SVG)
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert any("grid" in e for e in report.errors)
    assert report.metrics["precision_deviation"] > 0


def test_resolve_default_variant_single_rule() -> None:
    from iconpilot.pack import resolve_default_variant

    icon = {
        "variants": {
            "primitive": {"style": "primitive", "status": "approved"},
            "mono": {"style": "mono-line", "status": "approved"},
            "color": {"style": "lineal-color", "status": "todo"},
        }
    }
    assert resolve_default_variant(icon) == "color"  # single non-approved
    icon["variants"]["mono"]["status"] = "todo"
    assert resolve_default_variant(icon) == "mono"  # mono wins ties
    assert resolve_default_variant({"variants": {}}) is None


# --- per-style design grids ---------------------------------------------------

COLOR_GRID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M8 22 L24 8 L40 22"/><path d="M12 22 L12 40 L36 40 L36 22"/></svg>'
)


def test_style_grid_overrides_pack_viewbox(tmp_path: Path, pack_dir: Path) -> None:
    # pack spec is 24; lineal-color designs on its own 48 grid
    svg = tmp_path / "color.svg"
    svg.write_text(COLOR_GRID_SVG)
    pack, styles = load_pack(pack_dir / "pack.json")
    report = run_gate(svg, pack, styles["lineal-color"])
    assert report.passed, report.errors
    # the same 48px SVG must FAIL against a 24-grid style
    report = run_gate(svg, pack, styles["mono-line"])
    assert any("viewBox" in e for e in report.errors)


# --- palette + design_md context ---------------------------------------------

PALETTE_STYLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="#ff0000" stroke="#224e3b" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 11 L12 4 L20 11"/></svg>'
)


def test_palette_enforced_in_lint(tmp_path: Path, pack_dir: Path) -> None:
    svg = tmp_path / "p.svg"
    svg.write_text(PALETTE_STYLE_SVG)
    pack, styles = load_pack(pack_dir / "pack.json")
    # lineal-color with a palette that excludes #ff0000
    lc = styles["lineal-color"]
    styled = type(lc)(**{**lc.as_dict(), "palette": ("#346751", "#9dd9d2")})
    report = run_gate(svg, pack, styled)
    assert any("palette" in e for e in report.errors)


def test_context_surfaces_palette_and_design_md(pack_dir: Path) -> None:
    import json as _json

    pack = _json.loads((pack_dir / "pack.json").read_text())
    pack["inherits"] = {"design_md": "../../DESIGN.md"}
    pack["styles"] = {"lineal-color": {"palette": ["#346751", "#9dd9d2"]}}
    (pack_dir / "pack.json").write_text(_json.dumps(pack))
    pack_data, styles = load_pack(pack_dir / "pack.json")
    ctx = build_context(pack_dir, pack_data, styles, "hut", "color")
    assert ctx["palette"] == ["#346751", "#9dd9d2"]
    assert ctx["design_md"] == "../../DESIGN.md"
