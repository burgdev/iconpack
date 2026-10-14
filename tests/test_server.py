"""Review server tests: decisions endpoint, live icon editing, locking."""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from iconpilot.server.server import pack_lock
from tests.test_pack_schema import VALID_SVG, example_pack


@pytest.fixture
def srvpack(tmp_path: Path) -> Path:
    d = tmp_path / "outdoor-poi"
    d.mkdir()
    (d / "pack.json").write_text(json.dumps(example_pack()))
    for icon, cand in [("hut", "a1"), ("hut", "a2")]:
        p = d / ".runs" / "r001" / "mono" / icon
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{cand}.svg").write_text(VALID_SVG)
    return d


class _Server:
    def __init__(self, pack_dir: Path):
        from http.server import ThreadingHTTPServer

        from iconpilot.server.server import ReviewHandler

        handler = type("H", (ReviewHandler,), {"pack_dir": pack_dir})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def get(self, path: str):
        import urllib.error

        try:
            with urllib.request.urlopen(self.base + path) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def req(self, method: str, path: str, payload: dict):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())


@pytest.fixture
def server(srvpack: Path) -> _Server:
    s = _Server(srvpack)
    yield s
    s.httpd.shutdown()


def test_pack_and_run_endpoints(server: _Server) -> None:
    code, body = server.get("/api/pack")
    assert code == 200
    pack = json.loads(body)["pack"]
    assert "hut" in pack["icons"]
    code, body = server.get("/api/run")
    assert json.loads(body)["round"] == "r001"
    assert len(json.loads(body)["candidates"]) == 2


def test_decision_via_server(server: _Server, srvpack: Path) -> None:
    code, data = server.req("POST", "/api/decision", {"text": "hut/mono: a1 ok"})
    assert code == 200, data
    assert data["rev"] >= 1
    assert (srvpack / "icons" / "hut" / "mono.svg").is_file()
    # rev is visible through /api/pack
    _, body = server.get("/api/pack")
    assert json.loads(body)["rev"] == data["rev"]


def test_decision_invalid_text_400(server: _Server) -> None:
    code, data = server.req("POST", "/api/decision", {"text": "hut/mono: z9 ok"})
    assert code == 400
    assert "z9" in data["error"]


def test_live_edit_icon_fields(server: _Server, srvpack: Path) -> None:
    code, data = server.req(
        "PUT",
        "/api/icon",
        {
            "icon": "hut",
            "brief": "Alpine hut: steep roof, tiny window",
            "main_color": "#224e3b",
        },
    )
    assert code == 200, data
    pack = json.loads((srvpack / "pack.json").read_text())
    assert pack["icons"]["hut"]["brief"] == "Alpine hut: steep roof, tiny window"
    assert pack["rev"] == data["rev"]


def test_live_edit_rejects_invalid_patch(server: _Server, srvpack: Path) -> None:
    before = (srvpack / "pack.json").read_text()
    code, data = server.req("PUT", "/api/icon", {"icon": "hut", "main_color": "green"})
    assert code == 400
    assert any("main_color" in e for e in data["errors"])
    assert (srvpack / "pack.json").read_text() == before  # nothing written


def test_live_edit_cannot_touch_status(server: _Server, srvpack: Path) -> None:
    code, _data = server.req(
        "PUT", "/api/icon", {"icon": "hut", "brief": "x", "status": "approved"}
    )
    assert code == 200
    pack = json.loads((srvpack / "pack.json").read_text())
    # status is not an editable field → dropped from patch, icon-level anyway
    assert "status" not in pack["icons"]["hut"]


def test_render_endpoint_guarded(server: _Server, srvpack: Path) -> None:
    code, _ = server.get("/api/render?p=" + urllib.parse.quote("../pack.json"))
    assert code == 404
    code, body = server.get("/api/render?p=.runs/r001/mono/hut/a1.svg&size=24")
    assert code == 200
    assert body[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic


def test_pack_lock_blocks_concurrent_writer(srvpack: Path) -> None:
    import time

    with pack_lock(srvpack):
        t0 = time.monotonic()
        with pytest.raises(TimeoutError), pack_lock(srvpack, timeout=0.4):
            pass
        assert time.monotonic() - t0 < 2


# --- vue page + new endpoints ---------------------------------------------------


def test_styles_endpoint(server: _Server) -> None:
    code, body = server.get("/api/styles")
    assert code == 200
    styles = json.loads(body)
    assert "mono-line" in styles and styles["mono-line"]["stroke"]["width"] == 2


def test_variant_style_switch(server: _Server, srvpack: Path) -> None:
    code, data = server.req(
        "PUT",
        "/api/variant",
        {
            "icon": "hut",
            "variant": "mono",
            "style": "mono-bold",
        },
    )
    assert code == 200, data
    pack = json.loads((srvpack / "pack.json").read_text())
    assert pack["icons"]["hut"]["variants"]["mono"]["style"] == "mono-bold"
    # unknown style → 400, nothing written
    code, data = server.req(
        "PUT", "/api/variant", {"icon": "hut", "variant": "mono", "style": "nope"}
    )
    assert code == 400


def test_ai_status_endpoint(server: _Server, srvpack: Path) -> None:
    status_dir = srvpack / ".runs"
    (status_dir / ".ai-status").write_text("drafting hut/mono — 4 candidates\n")
    _code, body = server.get("/api/ai-status")
    assert json.loads(body) == {"status": "drafting hut/mono — 4 candidates", "active": True}
    (status_dir / ".ai-status").unlink()
    _code, body = server.get("/api/ai-status")
    assert json.loads(body) == {"status": "", "active": False}


def test_render_with_custom_colors(server: _Server, srvpack: Path) -> None:
    import urllib.parse

    p = urllib.parse.quote(".runs/r001/mono/hut/a1.svg")
    code, body = server.get(f"/api/render?p={p}&size=24&bg=%231c1c1c&color=%23346751")
    assert code == 200 and body[:4] == b"\x89PNG"


def test_page_has_no_bare_state_refs() -> None:
    # regression: attribute bindings kept bare refs (ai.text crashed at mount).
    # Scan ONLY binding contexts: {{ ... }} mustaches and attr="..." values.
    import re as _re

    from iconpilot.server.page import PAGE

    template = PAGE.split("<script")[0]
    bindings = " ".join(_re.findall(r"\{\{(.*?)\}\}", template))
    bindings += " " + " ".join(_re.findall(r'="([^"]*)"', template))
    states = [
        "pack",
        "rev",
        "round",
        "candidates",
        "styles",
        "ai",
        "decisions",
        "manual",
        "manualText",
        "msg",
        "msgClass",
        "editing",
        "dlg",
        "bgs",
        "grouped",
        "lines",
        "decisionText",
        "version",
        "set",
    ]
    for name in states:
        pat = _re.compile(r"(?<![\w.'])" + name + r"(?![\w])")
        bare = [
            m
            for m in pat.finditer(bindings)
            if not bindings[max(0, m.start() - 2) : m.start()].endswith("S.")
        ]
        assert not bare, f"binding has bare state ref '{name}'"


def test_pack_endpoint_reports_version(server: _Server) -> None:
    _, body = server.get("/api/pack")
    import iconpilot

    assert json.loads(body)["version"] == iconpilot.__version__


def test_put_pack_settings(server: _Server, srvpack: Path) -> None:
    code, data = server.req(
        "PUT",
        "/api/pack",
        {
            "version": "0.2.0",
            "rules": ["Door gap at least 2 units"],
            "spec": {"stroke": {"width": 2.5}, "live_area": {"padding": 2}, "precision": 0.5},
        },
    )
    assert code == 200, data
    pack = json.loads((srvpack / "pack.json").read_text())
    assert pack["version"] == "0.2.0"
    assert pack["spec"]["stroke"]["width"] == 2.5
    assert pack["rules"] == ["Door gap at least 2 units"]
    # invalid spec is rejected, nothing written
    before = (srvpack / "pack.json").read_text()
    code, data = server.req("PUT", "/api/pack", {"spec": {"stroke": {"width": "fat"}}})
    assert code == 400
    assert (srvpack / "pack.json").read_text() == before  # rejected → nothing written


def test_notes_flow(server: _Server, srvpack: Path) -> None:
    # per-icon persistent note
    code, data = server.req("PUT", "/api/icon", {"icon": "hut", "note": "no chimneys, ever"})
    assert code == 200, data
    # pack-global note
    code, data = server.req("PUT", "/api/pack", {"note": "calm geometry across the set"})
    assert code == 200, data
    pack = json.loads((srvpack / "pack.json").read_text())
    assert pack["icons"]["hut"]["note"] == "no chimneys, ever"
    assert pack["note"] == "calm geometry across the set"
    # instructions ride along with a decision apply
    code, data = server.req(
        "POST",
        "/api/decision",
        {"text": "hut/mono: a1 ok", "instructions": "try steeper roofs next time"},
    )
    assert code == 200, data
    dec = json.loads((srvpack / ".runs" / "r001" / "decisions.json").read_text())
    assert dec["instructions"] == "try steeper roofs next time"
    # context surfaces both notes
    from iconpilot.context import build_context
    from iconpilot.pack import load_pack

    p, styles = load_pack(srvpack / "pack.json")
    ctx = build_context(srvpack, p, styles, "hut", "mono")
    assert ctx.get("pack_note") == "calm geometry across the set"
    assert ctx.get("icon_note") == "no chimneys, ever"


def test_variant_note_and_svg_path(server: _Server, srvpack: Path) -> None:
    # variant-level note via PUT /api/variant
    code, data = server.req(
        "PUT",
        "/api/variant",
        {
            "icon": "hut",
            "variant": "mono",
            "note": "stroke slightly heavier",
        },
    )
    assert code == 200, data
    pack = json.loads((srvpack / "pack.json").read_text())
    assert pack["icons"]["hut"]["variants"]["mono"]["note"] == "stroke slightly heavier"

    # svg path endpoint
    code, body = server.get("/api/svg-path?icon=hut&variant=mono")
    assert code == 200
    path = json.loads(body)["path"]
    assert "hut" in path and path.endswith(".svg")


def test_history_endpoint(server: _Server, srvpack: Path) -> None:
    # apply a decision first so r001 has decisions.json
    server.req("POST", "/api/decision", {"text": "hut/mono: a1 ok"})
    code, body = server.get("/api/history")
    assert code == 200
    rounds = json.loads(body)["rounds"]
    assert len(rounds) >= 1
    r = rounds[-1]
    assert r["round"] == "r001"
    assert r["decided"] is True
    assert "hut" in str(r["icons"])


def test_pinned_variant(server: _Server, srvpack: Path) -> None:
    code, data = server.req(
        "PUT",
        "/api/variant",
        {
            "icon": "hut",
            "variant": "mono",
            "pinned": True,
        },
    )
    assert code == 200, data
    pack = json.loads((srvpack / "pack.json").read_text())
    assert pack["icons"]["hut"]["variants"]["mono"]["pinned"] is True


def test_context_auto_brief_from_sibling(srvpack: Path) -> None:
    from iconpilot.context import build_context
    from iconpilot.pack import load_pack

    # approve hut/mono so it becomes an auto-reference for hut/color
    pack, styles = load_pack(srvpack / "pack.json")
    pack["icons"]["hut"]["variants"]["mono"]["status"] = "approved"
    d = srvpack / "icons" / "hut"
    d.mkdir(parents=True, exist_ok=True)
    (d / "mono.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"/>')
    ctx = build_context(srvpack, pack, styles, "hut", "color")
    # color has reference: hut#mono explicitly, so reference_svg should exist
    assert "reference_svg" in ctx


def test_context_pinned_references(srvpack: Path) -> None:
    from iconpilot.context import build_context
    from iconpilot.pack import load_pack

    pack, styles = load_pack(srvpack / "pack.json")
    # pin hut/mono as a style reference
    pack["icons"]["hut"]["variants"]["mono"]["pinned"] = True
    pack["icons"]["hut"]["variants"]["mono"]["status"] = "approved"
    d = srvpack / "icons" / "hut"
    d.mkdir(parents=True, exist_ok=True)
    (d / "mono.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"/>')
    # build context for a DIFFERENT icon
    ctx = build_context(srvpack, pack, styles, "selfhut", "mono")
    assert "pinned_references" in ctx
    assert any("hut#mono" in pr["id"] for pr in ctx["pinned_references"])


def test_anchor_suggestions_endpoint(server: _Server) -> None:
    code, body = server.get("/api/anchor-suggestions")
    assert code == 200
    data = json.loads(body)
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
