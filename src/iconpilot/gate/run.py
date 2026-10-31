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
from svgpathtools import CubicBezier, Line, QuadraticBezier, parse_path

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

    def waive(self, msg: str, reason: str) -> None:
        """Drop a failure with a documented reason (config or waiver)."""
        if msg in self.errors:
            self.errors.remove(msg)
        self.checks.append(f"waived: {msg} ({reason})")
        self.passed = not self.errors

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


def _lint(
    root, spec: dict, style: Style, report: GateReport, icon_colors: tuple | list | None = None
) -> None:
    allowed = set(spec.get("allowed_elements", ["path"]))
    # gradient styles need <defs>/<linearGradient>/<stop>; their id is an
    # internal fill reference, not a CSS/JS hook — allowed on gradients only
    gradient_els = {"defs", "linearGradient", "radialGradient", "stop"}
    if style.fill == "gradient":
        allowed |= gradient_els
    for el in root.iter():
        if el is root:
            continue
        name = etree.QName(el).localname
        if name not in allowed:
            report.fail(f"lint: <{name}> not in allowed_elements {sorted(allowed)}")
        if el.get("style"):
            report.fail(f"lint: <{name}> carries inline style attribute")
        is_gradient = name in {"linearGradient", "radialGradient"}
        if (el.get("id") or el.get("class")) and not is_gradient:
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
    if icon_colors or style.palette:
        source = list(icon_colors) if icon_colors else list(style.palette)
        allowed = {c.lower() for c in source}
        used = set()
        named = {
            "white": "#ffffff",
            "black": "#000000",
            "red": "#ff0000",
            "green": "#008000",
            "blue": "#0000ff",
            "gray": "#808080",
        }
        for el in root.iter():
            for attr in ("fill", "stroke", "stop-color"):
                v = (el.get(attr) or "").strip().lower()
                if not v or v in ("none", "currentcolor"):
                    continue
                if v.startswith("#") and len(v) in (4, 7):
                    used.add(v)
                elif v.startswith(("rgb(", "rgba(")):
                    # Recraft v4 returns rgb(r,g,b) / rgba(r,g,b,a) — normalize
                    try:
                        parts = [
                            min(255, max(0, int(p))) for p in v[v.index("(") + 1 : -1].split(",")
                        ]
                        if len(parts) >= 3:
                            used.add("#{:02x}{:02x}{:02x}".format(*parts[:3]))
                    except (ValueError, TypeError):
                        pass
                elif v in named:
                    used.add(named[v])
        rogue = used - allowed - {"#fff", "#ffffff"}  # white halo tolerated
        scope = "icon colors" if icon_colors else "style palette"
        if rogue:
            report.fail(f"lint: colors outside the {scope}: {sorted(rogue)}")
        elif used and not (used - {"#fff", "#ffffff"}):
            # every fill is tolerated-white → a blank icon would pass silently
            report.fail("lint: all-white icon — no ink color at all")
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
            nodes += sum(
                max(1, len(s)) if isinstance(s, (Line, CubicBezier, QuadraticBezier)) else 4
                for s in segs
            ) or len(segs)
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

    _precision(root, spec, report)
    _min_gap(root, style, report)


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


_NUM_ATTRS = {
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "rect": ("x", "y", "width", "height"),
    "line": ("x1", "y1", "x2", "y2"),
}


def _coord_values(root):
    """Yield every designer-placed coordinate: path anchors/controls + shape attrs."""
    for el in root.iter():
        name = etree.QName(el).localname
        if name == "path":
            d = el.get("d", "")
            try:
                segs = parse_path(d)
            except Exception:  # noqa: BLE001, S112 — reported by geometry
                continue
            for seg in segs:
                for pt in (
                    seg.start,
                    seg.end,
                    getattr(seg, "control1", None),
                    getattr(seg, "control2", None),
                ):
                    if pt is not None:
                        yield pt.real
                        yield pt.imag
        elif name in _NUM_ATTRS:
            for attr in _NUM_ATTRS[name]:
                if el.get(attr) is not None:
                    try:
                        yield float(el.get(attr))
                    except ValueError:
                        continue


def _precision(root, spec, report) -> None:
    step = spec.get("precision")
    if not step:
        return
    worst = 0.0
    for v in _coord_values(root):
        dev = abs(v - round(v / step) * step)
        worst = max(worst, dev)
    report.metrics["precision_deviation"] = round(worst, 4)
    if worst > 0.01:
        report.fail(
            f"geometry: coordinates off the {step} grid by up to {worst:.2f} "
            f"(snap anchors and control points to {step})"
        )
    else:
        report.checks.append(f"geometry: coordinates on the {step} grid (max dev {worst:.2f})")


def _element_points(root, per_segment: int = 12):
    """Sampled point cloud per top-level drawn element, for gap measurement."""
    import svgpathtools as spt

    for el in root.iter():
        name = etree.QName(el).localname
        pts: list[tuple[float, float]] = []
        if name == "path":
            try:
                segs = spt.parse_path(el.get("d", ""))
            except Exception:  # noqa: BLE001, S112
                continue
            for seg in segs:
                for i in range(per_segment + 1):
                    p = seg.point(i / per_segment)
                    pts.append((p.real, p.imag))
        else:
            bb = _shape_bbox(el)
            if not bb:
                continue
            x0, y0, x1, y1 = bb
            for fx in (0.0, 0.5, 1.0):
                for fy in (0.0, 0.5, 1.0):
                    pts.append((x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)))
        if len(pts) >= 2:
            yield el, pts


def _min_gap(root, style, report) -> None:
    gap = style.min_gap
    if not gap or gap <= 0:
        return
    contact_eps = 0.5  # closer than this counts as touching, not a gap
    clouds = [pts for _, pts in _element_points(root)]
    if len(clouds) < 2:
        return
    worst_gap = None
    for i in range(len(clouds)):
        for j in range(i + 1, len(clouds)):
            d = _min_distance(clouds[i], clouds[j])
            if contact_eps < d < gap and (worst_gap is None or d < worst_gap):
                worst_gap = d
    if worst_gap is not None:
        report.fail(
            f"geometry: near-miss gap {worst_gap:.2f} < min_gap {gap} "
            f"(join the strokes or open the gap)"
        )
    else:
        report.checks.append(f"geometry: no near-miss gaps below {gap}")


def _min_distance(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    best = float("inf")
    for xa, ya in a:
        for xb, yb in b:
            best = min(best, ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5)
    return best


def run_gate(
    svg_path: str | Path,
    pack: dict,
    style: Style,
    icon_colors: tuple[str, ...] | list[str] | None = None,
) -> GateReport:
    """Run the deterministic gate on one SVG against a pack spec + style.

    Pack `strictness` (0-1) scales tolerances: low = forgiving (early rounds),
    high = strict (final polish). Defaults to 1 (full strictness).
    icon_colors: per-icon subset — when set, colors must stay inside it
    instead of the full style palette.
    """
    report = GateReport()
    strictness = pack.get("strictness", 1.0)
    if strictness < 1.0:
        # Loose mode: LOWER min_gap (at strictness=0 disable near-miss check entirely)
        import dataclasses

        style = dataclasses.replace(style, min_gap=style.min_gap * strictness)

    path = Path(svg_path)
    if not path.is_file():
        report.fail(f"file: {path} not found")
        return report

    root = _parse(path, report)
    if root is None:
        return report

    expected_vb = (
        f"0 0 {style.size} {style.size}" if style.size else pack.get("spec", {}).get("viewBox")
    )
    viewbox = _viewbox(root, expected_vb, report)
    _lint(root, pack.get("spec", {}), style, report, icon_colors=icon_colors)
    _geometry(root, pack.get("spec", {}), style, viewbox, report)
    _render(path, style, report)
    _apply_overrides(report, pack, style, path)
    return report


# check keys → failure-message prefixes they can disable/waive
_CHECK_PREFIXES = {
    "min_gap": ("near-miss",),
    "grid": ("off the", "grid"),
    "live_area": ("outside live area",),
    "max_nodes": ("nodes",),
    "palette": ("outside the style palette",),
}


def _apply_overrides(report: GateReport, pack: dict, style: Style, path: Path) -> None:
    """Style gate config (toggles) and pack waivers (documented exceptions).

    Toggles: style.gate = {"min_gap": false, ...} disables a check for the
    whole style — config, not exception. Waivers: pack.waivers records a
    reason per icon#variant (or style:<id>) and appears in the report.
    """
    gate_cfg = getattr(style, "gate", None) or {}
    for key, prefixes in _CHECK_PREFIXES.items():
        if gate_cfg.get(key) is False:
            for err in list(report.errors):
                if any(p in err for p in prefixes):
                    report.waive(err, f"style config: {key} off")

    # target = icon#variant derived from the path (icons/<i>/<v>.svg or
    # .runs/<r>/<v>/<i>/<c>.svg)
    parts = path.parts
    target = ""
    if "icons" in parts:
        i = parts.index("icons")
        if len(parts) >= i + 3:
            target = f"{parts[i + 1]}#{parts[i + 2].removesuffix('.svg')}"
    elif ".runs" in parts:
        i = parts.index(".runs")
        if len(parts) >= i + 5:
            target = f"{parts[i + 3]}#{parts[i + 2]}"
    if not target:
        return
    for w in pack.get("waivers", []):
        w_target = w.get("target", "")
        if w_target not in (target, f"style:{style.id}"):
            continue
        key = w.get("check", "")
        prefixes = _CHECK_PREFIXES.get(key)
        if not prefixes:
            continue
        for err in list(report.errors):
            if any(p in err for p in prefixes):
                report.waive(err, f"waiver by {w.get('by', '?')}: {w.get('reason', '')}")


def fix_svg(svg_path: Path, precision: float = 0.5) -> tuple[str, int]:
    """Round all coordinates to the nearest grid step, preserving subpaths.

    Uses Path.continuous_subpaths() to correctly handle compound paths
    (multiple M commands, Z closures). Returns (fixed_svg_text, n_changes).
    """
    import svgpathtools as spt

    root = etree.parse(str(svg_path)).getroot()
    changes = 0

    def snap(v: float) -> float:
        nonlocal changes
        snapped = round(v / precision) * precision
        if abs(snapped - v) > 1e-9:
            changes += 1
        return snapped

    decimals = max(0, -int(f"{precision:e}".split("e")[-1]) if precision < 1 else 0)

    def fmt(v: float) -> str:
        s = f"{v:.{max(decimals, 1)}f}".rstrip("0").rstrip(".")
        return s if s else "0"

    for el in root.iter():
        name = etree.QName(el).localname
        if name == "path":
            d = el.get("d", "")
            if not d:
                continue
            try:
                full_path = spt.Path(d)
            except Exception:  # noqa: BLE001, S112 — gate reports these separately
                continue

            parts: list[str] = []
            for subpath in full_path.continuous_subpaths():
                if not subpath:
                    continue
                # M at the subpath start
                sx, sy = snap(subpath[0].start.real), snap(subpath[0].start.imag)
                parts.append(f"M{fmt(sx)} {fmt(sy)}")
                for seg in subpath:
                    cls = type(seg).__name__
                    ex, ey = snap(seg.end.real), snap(seg.end.imag)
                    if cls == "Line":
                        parts.append(f"L{fmt(ex)} {fmt(ey)}")
                    elif cls == "CubicBezier":
                        c1x, c1y = snap(seg.control1.real), snap(seg.control1.imag)
                        c2x, c2y = snap(seg.control2.real), snap(seg.control2.imag)
                        parts.append(
                            f"C{fmt(c1x)} {fmt(c1y)} {fmt(c2x)} {fmt(c2y)} {fmt(ex)} {fmt(ey)}"
                        )
                    elif cls == "QuadraticBezier":
                        qx, qy = snap(seg.control.real), snap(seg.control.imag)
                        parts.append(f"Q{fmt(qx)} {fmt(qy)} {fmt(ex)} {fmt(ey)}")
                    elif cls == "Arc":
                        parts.append(
                            f"A{fmt(seg.radius.real)} {fmt(seg.radius.imag)} {fmt(seg.rotation)} "
                            f"{int(seg.large_arc)} {int(seg.sweep)} {fmt(ex)} {fmt(ey)}"
                        )
                # preserve Z if the subpath was closed
                if subpath.isclosed():
                    parts.append("Z")

            if parts:
                el.set("d", " ".join(parts))
        elif name in _NUM_ATTRS:
            for attr in _NUM_ATTRS[name]:
                val = el.get(attr)
                if val is not None:
                    try:
                        v = float(val)
                        sv = snap(v)
                        if sv != v:
                            el.set(attr, fmt(sv))
                    except ValueError:
                        continue

    xml = etree.tostring(root, encoding="unicode")
    return xml, changes
