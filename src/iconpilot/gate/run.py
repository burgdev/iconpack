"""Deterministic gate — phase-1 slice: parse, lint, geometry.

Render (resvg) and similarity hash (imagehash) join in M1/M2; this slice
already enforces the spec/style rules the drafter must satisfy, so the
schema and style registry get validated by their real consumer.

The gate never talks to models. It is the only certifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree  # ty: ignore[unresolved-import]
from svgpathtools import parse_path

from iconpilot.render.render import (
    HASH_RENDER_SIZE,
    hash_file,
    ink_ratio,
    render_png,
)
from iconpilot.styles import Style

SVG_NS = "http://www.w3.org/2000/svg"

# node-count model for non-path shapes (rough, conservative)
_SHAPE_NODES = {"circle": 4, "ellipse": 4, "rect": 4, "line": 2}


@dataclass
class GateReport:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def fail(self, msg: str) -> None:
        self.passed = False
        self.errors.append(msg)

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "checks": self.checks,
            "metrics": self.metrics,
        }


def _parse(svg_path: Path, report: GateReport) -> etree._Element | None:
    try:
        tree = etree.parse(str(svg_path), parser=etree.XMLParser(remove_comments=True))
    except etree.XMLSyntaxError as exc:
        report.fail(f"parse: not well-formed XML ({exc})")
        return None
    root = tree.getroot()
    if etree.QName(root).localname != "svg":
        report.fail(f"parse: root element is <{etree.QName(root).localname}>, not <svg>")
        return None
    report.checks.append("parse: well-formed, single <svg> root")
    return root


def _viewbox(
    root, expected: str | None, report: GateReport
) -> tuple[float, float, float, float] | None:
    vb = root.get("viewBox")
    if not vb:
        report.fail("viewBox: missing — required for deterministic rendering")
        return None
    if expected and vb.strip() != expected.strip():
        report.fail(f"viewBox: '{vb}' does not match spec '{expected}'")
        return None
    parts = [float(p) for p in vb.replace(",", " ").split()]
    report.checks.append(f"viewBox: {vb} matches spec")
    return parts[0], parts[1], parts[2], parts[3]


def _lint(root, spec: dict, style: Style, report: GateReport) -> None:
    allowed = set(spec.get("allowed_elements", ["path"]))
    for el in root.iter():
        if el is root:
            continue
        name = etree.QName(el).localname
        if name not in allowed:
            report.fail(f"lint: <{name}> not in allowed_elements {sorted(allowed)}")
        if el.get("style"):
            report.fail(f"lint: <{name}> carries inline style attribute")
        if el.get("id") or el.get("class"):
            report.fail(f"lint: <{name}> carries id/class")
        if el.get("transform"):
            report.fail(f"lint: <{name}> carries transform — flatten to absolute paths")
    if root.get("style"):
        report.fail("lint: root <svg> carries inline style attribute")

    stroke = style.stroke
    if stroke:
        root_stroke = root.get("stroke")
        if root_stroke not in (None, "currentColor"):
            report.fail(f"lint: stroke must be currentColor (found '{root_stroke}')")
        width = root.get("stroke-width")
        if width is not None:
            try:
                if abs(float(width) - stroke["width"]) > 1e-6:
                    report.fail(f"lint: stroke-width {width} != style width {stroke['width']}")
            except ValueError:
                report.fail(f"lint: non-numeric stroke-width '{width}'")
    fill = style.fill or "none"
    if fill == "none" and root.get("fill") not in (None, "none"):
        report.fail(f"lint: fill must be none for outline styles (found '{root.get('fill')}')")
    report.checks.append(f"lint: elements/attributes conform to style '{style.id}'")


def _shape_bbox(el) -> tuple[float, float, float, float] | None:
    """True bbox for basic shapes (svgpathtools only handles <path>)."""
    name = etree.QName(el).localname
    try:
        if name == "circle":
            cx, cy, r = float(el.get("cx", 0)), float(el.get("cy", 0)), float(el.get("r", 0))
            return cx - r, cy - r, cx + r, cy + r
        if name == "ellipse":
            cx, cy = float(el.get("cx", 0)), float(el.get("cy", 0))
            rx, ry = float(el.get("rx", 0)), float(el.get("ry", 0))
            return cx - rx, cy - ry, cx + rx, cy + ry
        if name == "rect":
            x, y = float(el.get("x", 0)), float(el.get("y", 0))
            w, h = float(el.get("width", 0)), float(el.get("height", 0))
            return x, y, x + w, y + h
        if name == "line":
            x1, y1 = float(el.get("x1", 0)), float(el.get("y1", 0))
            x2, y2 = float(el.get("x2", 0)), float(el.get("y2", 0))
            return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        if name in ("polyline", "polygon"):
            nums = [float(n) for n in re.findall(r"[-+\d.]+", el.get("points", ""))]
            if len(nums) < 4:
                return None
            xs, ys = nums[0::2], nums[1::2]
            return min(xs), min(ys), max(xs), max(ys)
    except ValueError:
        return None
    return None


def _geometry(root, spec, style, viewbox, report):
    if not viewbox:
        return
    _, _, w, h = viewbox
    padding = spec.get("live_area", {}).get("padding", 0)
    x0, y0, x1, y1 = padding, padding, w - padding, h - padding

    nodes = 0
    bboxes: list[tuple[float, float, float, float]] = []
    for el in root.iter():
        name = etree.QName(el).localname
        if name == "path":
            d = el.get("d", "")
            try:
                segs = parse_path(d)
            except Exception as exc:  # noqa: BLE001 — svgpathtools raises assorted errors
                report.fail(f"geometry: unparseable path data: {exc}")
                continue
            nodes += sum(max(1, len(s)) for s in segs) or len(segs)
            for seg in segs:
                bx0, bx1, by0, by1 = seg.bbox()  # svgpathtools order: (xmin, xmax, ymin, ymax)
                bboxes.append((bx0, by0, bx1, by1))  # includes bezier control-point hull
        elif name in _SHAPE_NODES:
            nodes += _SHAPE_NODES[name]
            bb = _shape_bbox(el)
            if bb:
                bboxes.append(bb)
        elif name in ("polyline", "polygon"):
            nums = re.findall(r"[-+\d.]+", el.get("points", ""))
            nodes += max(1, len(nums) // 2)
            bb = _shape_bbox(el)
            if bb:
                bboxes.append(bb)

    report.metrics["node_count"] = nodes
    if nodes > style.max_nodes:
        report.fail(f"geometry: {nodes} nodes > style max {style.max_nodes} ({style.id})")

    if bboxes:
        xmin = min(b[0] for b in bboxes)
        ymin = min(b[1] for b in bboxes)
        xmax = max(b[2] for b in bboxes)
        ymax = max(b[3] for b in bboxes)
        report.metrics["bbox"] = [round(xmin, 2), round(ymin, 2), round(xmax, 2), round(ymax, 2)]
        if xmin < x0 - 1e-6 or ymin < y0 - 1e-6 or xmax > x1 + 1e-6 or ymax > y1 + 1e-6:
            report.fail(
                f"geometry: bbox [{xmin:.1f},{ymin:.1f},{xmax:.1f},{ymax:.1f}] "
                f"outside live area [{x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}]"
            )
        else:
            report.checks.append(
                f"geometry: bbox inside live area; {nodes}/{style.max_nodes} nodes"
            )


def _render(svg_path: Path, style: Style, report: GateReport) -> None:
    ratios: dict[int, float] = {}
    for size in style.render_sizes:
        try:
            img = render_png(svg_path, size)
        except Exception as exc:  # noqa: BLE001 — resvg raises assorted errors on broken SVG
            report.fail(f"render: {size}px failed ({exc})")
            return
        if img.size != (size, size):
            report.fail(f"render: requested {size}px, got {img.size}")
            return
        ratio = ink_ratio(img)
        ratios[size] = round(ratio, 4)
        if ratio == 0.0:
            report.fail(f"render: {size}px renders no ink (empty or invisible paths)")
        elif ratio > 0.9:
            report.fail(f"render: {size}px is nearly solid ({ratio:.0%} ink) — fill/counter error")
    report.metrics["ink_ratio"] = ratios
    report.metrics["phash"] = hash_file(svg_path)
    if report.passed:
        report.checks.append(
            f"render: {list(style.render_sizes)}px ok "
            f"(ink {', '.join(f'{s}px={r:.1%}' for s, r in ratios.items())}; "
            f"hash@{HASH_RENDER_SIZE}px)"
        )


def run_gate(svg_path: str | Path, pack: dict, style: Style) -> GateReport:
    """Run the deterministic gate on one SVG against a pack spec + style."""
    report = GateReport()
    path = Path(svg_path)
    if not path.is_file():
        report.fail(f"file: {path} not found")
        return report

    root = _parse(path, report)
    if root is None:
        return report

    viewbox = _viewbox(root, pack.get("spec", {}).get("viewBox"), report)
    _lint(root, pack.get("spec", {}), style, report)
    _geometry(root, pack.get("spec", {}), style, viewbox, report)
    _render(path, style, report)
    return report
