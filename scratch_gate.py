import sys
from iconpilot.styles import resolve_styles
from iconpilot.gate.run import run_gate

SPEC = {
    "viewBox": "0 0 24 24",
    "live_area": {"padding": 2},
    "stroke": {"width": 2, "linecap": "round", "linejoin": "round"},
    "fill": "none",
    "allowed_elements": ["path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "defs", "linearGradient", "stop"],
    "precision": 0.5,
}

styles = resolve_styles({})
for arg in sys.argv[1:]:
    svg, sid = arg.rsplit(":", 1)
    r = run_gate(svg, {"icons": {}, "spec": SPEC}, styles[sid])
    status = "PASS" if r.passed else "FAIL"
    extra = ""
    if not r.passed:
        extra = " :: " + "; ".join(r.errors)
    m = r.metrics
    print(f"{status} {svg} [{sid}] nodes={m.get('node_count')} bbox={m.get('bbox')} ink={m.get('ink_ratio')}{extra}")
