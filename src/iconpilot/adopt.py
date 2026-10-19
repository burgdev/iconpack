"""Adopt: deterministic Recraft-seed → pack-icon conversion.

No LLM, no hard gating — mechanical post-processing that gets a seed as
close to the style contract as geometry allows, then reports whatever the
gate still objects to. The user decides (approval is always theirs).

Pipeline: strip metadata → drop background rects → bake transforms →
snap colors to the palette (currentColor for mono, gradients collapse to
their middle stop) → rescale to the style design grid, centered → snap to
the precision grid → simplify to the node budget (Douglas-Peucker) → gate.
"""

from __future__ import annotations

import math
import re
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET

# affine = (a, b, c, d, e, f) mapping (x, y) → (a·x + c·y + e, b·x + d·y + f)
Affine = tuple[float, float, float, float, float, float]

IDENTITY: Affine = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

_NUM = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
_TRANSFORM_RE = re.compile(r"(translate|scale|rotate|matrix)\s*\(([^)]*)\)")
_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

SHAPE_TAGS = ("rect", "circle", "ellipse", "line", "polyline", "polygon")


def _compose(m1: Affine, m2: Affine) -> Affine:
    """m1 ∘ m2 — apply m2 first, then m1."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply(m: Affine, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _parse_transform(value: str) -> Affine:
    m = IDENTITY
    for name, args in _TRANSFORM_RE.findall(value or ""):
        nums = [float(n) for n in re.findall(_NUM, args)]
        if name == "translate" and nums:
            m = _compose(m, (1, 0, 0, 1, nums[0], nums[1] if len(nums) > 1 else 0))
        elif name == "scale" and nums:
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            m = _compose(m, (sx, 0, 0, sy, 0, 0))
        elif name == "rotate" and nums:
            ang = math.radians(nums[0])
            cx, cy = (nums[1], nums[2]) if len(nums) > 2 else (0.0, 0.0)
            cos, sin = math.cos(ang), math.sin(ang)
            r = (cos, sin, -sin, cos, 0, 0)
            t1 = (1, 0, 0, 1, cx, cy)
            t2 = (1, 0, 0, 1, -cx, -cy)
            m = _compose(m, _compose(_compose(t1, r), t2))
        elif name == "matrix" and len(nums) >= 6:
            m = _compose(m, (nums[0], nums[1], nums[2], nums[3], nums[4], nums[5]))
    return m


def _nums(value: str | None, default: float = 0.0) -> list[float]:
    if not value:
        return []
    return [float(n) for n in re.findall(_NUM, value)]


def _shape_to_d(el: ET.Element) -> str | None:
    """Convert a basic shape to path data (source coordinates)."""
    tag = el.tag.split("}")[-1]
    n = _nums
    if tag == "rect":
        x, y = float(el.get("x", 0) or 0), float(el.get("y", 0) or 0)
        w, h = float(el.get("width", 0) or 0), float(el.get("height", 0) or 0)
        if w <= 0 or h <= 0:
            return None
        return f"M{x} {y}H{x + w}V{y + h}H{x}Z"
    if tag == "circle":
        v = {
            "cx": float(el.get("cx", 0) or 0),
            "cy": float(el.get("cy", 0) or 0),
            "r": float(el.get("r", 0) or 0),
        }
        if v["r"] <= 0:
            return None
        r = v["r"]
        return (
            f"M{v['cx'] - r} {v['cy']}A{r} {r} 0 1 0 {v['cx'] + r} {v['cy']}"
            f"A{r} {r} 0 1 0 {v['cx'] - r} {v['cy']}Z"
        )
    if tag == "ellipse":
        cx, cy = float(el.get("cx", 0) or 0), float(el.get("cy", 0) or 0)
        rx, ry = float(el.get("rx", 0) or 0), float(el.get("ry", 0) or 0)
        if rx <= 0 or ry <= 0:
            return None
        return f"M{cx - rx} {cy}A{rx} {ry} 0 1 0 {cx + rx} {cy}A{rx} {ry} 0 1 0 {cx - rx} {cy}Z"
    if tag == "line":
        v = n(el.get("x1")) + n(el.get("y1")) + n(el.get("x2")) + n(el.get("y2"))
        if len(v) < 4:
            return None
        return f"M{v[0]} {v[1]}L{v[2]} {v[3]}"
    if tag in ("polyline", "polygon"):
        pts = n(el.get("points"))
        if len(pts) < 4:
            return None
        d = f"M{pts[0]} {pts[1]}" + "".join(
            f"L{pts[i]} {pts[i + 1]}" for i in range(2, len(pts), 2)
        )
        return d + ("Z" if tag == "polygon" else "")
    return None


def _flatten_d(d: str, m: Affine) -> list[tuple[float, float]]:
    """Flatten path data through an affine into a dense polyline."""
    from svgpathtools import Arc, CubicBezier, Line, QuadraticBezier, parse_path

    try:
        path = parse_path(d)
    except Exception:  # noqa: BLE001 — unparseable seed data degrades to skip
        return []
    pts: list[tuple[float, float]] = []
    for seg in path:
        if isinstance(seg, Arc):
            try:
                segs = seg.as_cubic_curves()
            except Exception:  # noqa: BLE001, S112 — bad arcs degrade to skip
                continue
        else:
            segs = [seg]
        for s in segs:
            if isinstance(s, Line):
                samples = [s.start, s.end]
            elif isinstance(s, QuadraticBezier):
                samples = [s.point(t / 8) for t in range(9)]
            elif isinstance(s, CubicBezier):
                samples = [s.point(t / 12) for t in range(13)]
            else:
                continue
            for p in samples:
                x, y = _apply(m, p.real, p.imag)
                pts.append((x, y))
    return pts


def _dp(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Douglas-Peucker polyline simplification."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = points[i]
        bx, by = points[j]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        best, best_d = -1, -1.0
        for k in range(i + 1, j):
            px, py = points[k]
            dist = abs((px - ax) * dy - (py - ay) * dx) / norm
            if dist > best_d:
                best, best_d = k, dist
        if best_d > tol:
            keep[best] = True
            stack.append((i, best))
            stack.append((best, j))
    return [p for p, k in zip(points, keep) if k]


def _hex_to_rgb(h: str) -> tuple[int, int, int] | None:
    h = (h or "").strip()
    if _HEX_RE.match(h):
        h = h[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        try:
            return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            return None
    m = re.match(r"^rgba?\(([^)]+)\)", h)
    if m:
        try:
            parts = [int(float(p)) for p in m.group(1).split(",")[:3]]
            if len(parts) == 3:
                return tuple(parts)  # type: ignore[return-value]
        except ValueError:
            return None
    named = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "red": (255, 0, 0),
        "green": (0, 128, 0),
        "blue": (0, 0, 255),
        "gray": (128, 128, 128),
    }
    return named.get(h)


def _snap_color(value: str, palette: list[tuple[int, int, int]]) -> tuple[str, bool]:
    """Snap a color string to the nearest palette entry. → (hex, changed)."""
    rgb = _hex_to_rgb(value)
    if rgb is None:
        return value, False
    if rgb in palette:
        return "#{:02x}{:02x}{:02x}".format(*rgb), False
    best = min(palette, key=lambda p: sum((a - b) ** 2 for a, b in zip(p, rgb)))
    return "#{:02x}{:02x}{:02x}".format(*tuple(best)), True


def adopt_svg(
    svg_text: str, style, pack: dict, gate_check: bool = True
) -> tuple[str, list[str], list[str]]:
    """Deterministic seed → pack-icon conversion. Returns (svg, fixes, gate_errors).

    Never raises on content — geometry that can't meet the node budget is
    reported, not blocked (approval is the user's).
    """
    from iconpilot.recraft import strip_metadata

    fixes: list[str] = []
    rects_before = svg_text.lower().count("<rect")
    svg_text = strip_metadata(svg_text)
    dropped = rects_before - svg_text.lower().count("<rect")
    if dropped:
        fixes.append(f"removed {dropped} background rect(s)")
    root = ET.fromstring(svg_text)

    vb = _nums(root.get("viewBox") or "0 0 24 24")
    src_w = vb[2] if len(vb) >= 4 else 24.0

    # gradient stops: gradient id → representative (middle-offset) color
    grad_colors: dict[str, tuple[int, int, int]] = {}
    for el in root.iter():
        if el.tag.split("}")[-1].split(":")[-1] in ("linearGradient", "radialGradient"):
            stops = [
                _hex_to_rgb(el2.get("stop-color") or "")
                for el2 in el
                if el2.tag.split("}")[-1].split(":")[-1] == "stop"
            ]
            stops = [s for s in stops if s]
            if stops:
                grad_colors["#" + (el.get("id") or "")] = stops[len(stops) // 2]

    mono = style.color_mode == "mono"
    palette: list[tuple[int, int, int]] = []
    if not mono:
        from iconpilot.recraft import hex_to_rgb as _h2r

        palette = [c for c in (_h2r(x) for x in (style.palette or ())) if c]
        if not palette:  # no palette → keep colors as-is
            palette = []

    # ── collect drawn elements with accumulated transforms; drop backgrounds ──
    drawn: list[tuple[str, list[tuple[float, float]]]] = []  # (fill, polyline)
    bg_removed = 0

    def local_tag(el: ET.Element) -> str:
        # handles both {ns}tag and prefix:tag (Recraft emits svg:path)
        return el.tag.split("}")[-1].split(":")[-1]

    def walk(el: ET.Element, m: Affine) -> None:
        nonlocal bg_removed
        for child in el:
            tag = local_tag(child)
            if tag in ("defs", "linearGradient", "radialGradient", "metadata"):
                continue
            cm = _compose(m, _parse_transform(child.get("transform")))
            if tag in ("g", "svg"):  # groups and nested svg roots recurse
                walk(child, cm)
                continue
            if tag == "path":
                d = child.get("d") or ""
            elif tag in SHAPE_TAGS:
                d = _shape_to_d(child)
            else:
                continue
            if not d:
                continue
            pts = _flatten_d(d, cm)
            if len(pts) < 2:
                continue
            # background detection: painted element covering ≥88% of canvas
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            cover = (max(xs) - min(xs)) * (max(ys) - min(ys)) / (src_w * src_w)
            fill = (child.get("fill") or "").strip()
            if cover >= 0.88 and fill and fill.lower() not in ("none",):
                bg_removed += 1
                continue
            drawn.append((fill, pts))

    walk(root, IDENTITY)
    if bg_removed:
        fixes.append(f"removed {bg_removed} background rect(s)")
    transforms_baked = svg_text.count("transform=")
    if transforms_baked:
        fixes.append(f"baked {transforms_baked} transform(s) into absolute paths")
    shapes = svg_text.count("<rect") + svg_text.count("<circle") + svg_text.count("<ellipse")
    if shapes:
        fixes.append(f"converted {shapes} shape(s) to paths")

    if not drawn:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"/>',
            fixes + ["ERROR: no drawable content"],
            ["adopt: no drawable content"],
        )

    # ── colors ──
    snapped = 0
    paths_out: list[tuple[str, list[tuple[float, float]]]] = []
    for fill, pts in drawn:
        if mono:
            paths_out.append(("currentColor" if fill.lower() not in ("none",) else "none", pts))
            continue
        f = fill
        if f.startswith("url("):
            gid = f[4:-1]
            rep = grad_colors.get(gid)
            f = "#{:02x}{:02x}{:02x}".format(*tuple(rep)) if rep else "#000000"
        if f and f.lower() != "none" and palette:
            f2, changed = _snap_color(f, palette)
            snapped += changed
            f = f2
        paths_out.append((f, pts))
    if mono:
        fixes.append("mono: fills → currentColor")
    elif snapped:
        fixes.append(f"snapped {snapped} color(s) to the style palette")
    grad_count = len(grad_colors)
    if grad_count and not mono:
        fixes.append(f"collapsed {grad_count} gradient(s) to mid-stop colors")

    # ── node budget: drop micro-paths, then DP-simplify if still over ──
    def node_count(items) -> int:
        # gate metric: sum(max(1, len(seg))) ≈ 2 per polyline segment
        return sum(2 * max(0, len(pts) - 1) for _, pts in items)

    budget = getattr(style, "max_nodes", None) or 64
    pruned = [
        i
        for i in paths_out
        if math.hypot(
            max(p[0] for p in i[1]) - min(p[0] for p in i[1]),
            max(p[1] for p in i[1]) - min(p[1] for p in i[1]),
        )
        >= 0.75
    ]
    dropped = len(paths_out) - len(pruned)
    if dropped:
        fixes.append(f"dropped {dropped} micro-path(s)")
    paths_out = pruned

    nodes = node_count(paths_out)
    if nodes > budget:
        best = paths_out
        for tol in (0.1, 0.25, 0.5, 0.75, 1.0):
            simplified = [(f, _dp(pts, tol)) for f, pts in paths_out]
            simplified = [i for i in simplified if len(i[1]) >= 2]
            if node_count(simplified) < node_count(best):
                best = simplified
            if node_count(simplified) <= budget:
                break
        paths_out = best  # always take the best — never keep the unsimplified set
        if node_count(paths_out) <= budget:
            fixes.append(f"simplified {nodes} → {node_count(paths_out)} nodes")
        else:
            fixes.append(
                f"simplified {nodes} → {node_count(paths_out)} nodes — "
                f"budget {budget} still exceeded, needs redraw"
            )
    else:
        fixes.append(f"node budget ok ({nodes}/{budget})")

    # ── rescale to the style design grid, centered, precision-snapped ──
    target = float(getattr(style, "size", None) or 24)
    precision = float(pack.get("spec", {}).get("precision", 0.5) or 0.5)
    xs = [p[0] for _, pts in paths_out for p in pts]
    ys = [p[1] for _, pts in paths_out for p in pts]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    k = (target * 0.85) / max(x1 - x0, y1 - y0, 1e-9)
    tx = (target - (x1 - x0) * k) / 2 - x0 * k
    ty = (target - (y1 - y0) * k) / 2 - y0 * k

    def rnd(v: float) -> float:
        return round(round(v / precision) * precision, 3)

    body = []
    for fill, pts in paths_out:
        raw = [(rnd(x * k + tx), rnd(y * k + ty)) for x, y in pts]
        snapped_pts = [raw[0]]
        for p in raw[1:]:  # rounding collapses near points — drop duplicates
            if p != snapped_pts[-1]:
                snapped_pts.append(p)
        if len(snapped_pts) == 1:
            continue
        d = "M" + "L".join(f"{x} {y}" for x, y in snapped_pts)
        if len(snapped_pts) > 2 and snapped_pts[-1] == snapped_pts[0]:
            d += "Z"
        body.append(f'<path fill="{fill}" d="{d}"/>')

    out = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {target:g} {target:g}">'
        + "".join(body)
        + "</svg>"
    )

    # ── gate (informational — no hard gating) ──
    gate_errors: list[str] = []
    if gate_check:
        try:
            from iconpilot.gate.run import run_gate

            with NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
                f.write(out)
                tmp = f.name
            rep = run_gate(tmp, pack, style)
            gate_errors = rep.errors
        except Exception as exc:  # noqa: BLE001 — gate failure shouldn't block adopt
            gate_errors = [f"gate could not run: {exc}"]

    return out, fixes, gate_errors
