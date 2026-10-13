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
