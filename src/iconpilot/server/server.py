"""Review server: live pack editing + decisions, stdlib only.

Write path (advisor-reviewed design):
  - advisory flock (.iconpilot.lock) around every pack.json mutation;
    CLI decide and the server share the same lock
  - decisions (ok/keep/no) go through the same decide pipeline as the CLI
  - live edits patch per-icon fields only (brief/prompt/main_color/style ref
    is read-only here); every write revalidates schema+semantics first
  - atomic writes + monotonic rev; the page polls rev and reloads on change
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from iconpilot.decide import apply_decisions, parse_decision_text
from iconpilot.pack import load_pack, revalidate, write_pack_atomic
from iconpilot.render.contact import contact_sheet
from iconpilot.render.render import render_png

EDITABLE_FIELDS = ("brief", "prompt", "main_color")


@contextlib.contextmanager
def pack_lock(pack_dir: Path, timeout: float = 5.0):
    lockfile = pack_dir / ".iconpilot.lock"
    fh = open(lockfile, "w")  # noqa: SIM115 — closed in finally; this IS the context manager
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"pack is locked ({lockfile})")
                time.sleep(0.1)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def _safe_svg(pack_dir: Path, rel: str) -> Path | None:
    """Constrain render endpoints to icons/ or .runs/ inside the pack."""
    try:
        p = (pack_dir / rel).resolve()
    except (ValueError, OSError):
        return None
    root = pack_dir.resolve()
    if root not in p.parents:
        return None
    if p.suffix != ".svg":
        return None
    rel_parts = p.relative_to(root).parts
    if rel_parts[0] not in ("icons", ".runs"):
        return None
    return p if p.is_file() else None


class ReviewHandler(BaseHTTPRequestHandler):
    pack_dir: Path  # set via subclass/partial

    # --- helpers ---------------------------------------------------------
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else {}

    def log_message(self, format: str, *args: Any) -> None:  # quiet
        # base class signature (format, *args: Any); quiet by default
        pass

    # --- routes ------------------------------------------------------------
    def do_GET(self) -> None:
        url = urlparse(self.path)
        q = parse_qs(url.query)

        if url.path == "/" or url.path == "/index.html":
            from iconpilot.server.page import PAGE

            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if url.path == "/api/pack":
            try:
                pack, _ = load_pack(self.pack_dir / "pack.json")
                self._json(200, {"rev": pack.get("rev", 0), "pack": pack})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return

        if url.path == "/api/run":
            runs = sorted(p.name for p in (self.pack_dir / ".runs").glob("r*") if p.is_dir())
            entries = []
            if runs:
                for svg in sorted((self.pack_dir / ".runs" / runs[-1]).rglob("*.svg")):
                    rel = svg.relative_to(self.pack_dir / ".runs" / runs[-1]).parts
                    if len(rel) == 3:
                        entries.append({"variant": rel[0], "icon": rel[1], "cand": rel[2][:-4]})
            self._json(200, {"round": runs[-1] if runs else None, "candidates": entries})
            return

        if url.path == "/api/render":
            rel = (q.get("p") or [""])[0]
            size = int((q.get("size") or ["48"])[0])
            bg = (q.get("bg") or ["light"])[0]
            svg = _safe_svg(self.pack_dir, rel)
            if svg is None:
                self._json(404, {"error": "not found"})
                return
            img = render_png(svg, size, background="#ffffff" if bg == "light" else "#112119")
            import io

            buf = io.BytesIO()
            img.save(buf, "PNG")
            body = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if url.path == "/api/sheet":
            runs = sorted(p.name for p in (self.pack_dir / ".runs").glob("r*") if p.is_dir())
            if not runs:
                self._json(404, {"error": "no runs"})
                return
            run_dir = self.pack_dir / ".runs" / runs[-1]
            out = run_dir / "contact-sheet.png"
            svgs = sorted(run_dir.rglob("*.svg"))
            if not svgs:
                self._json(404, {"error": "empty run"})
                return
            contact_sheet([s for s in svgs], out, title=runs[-1])
            body = out.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self._json(404, {"error": "no such route"})

    def do_POST(self) -> None:
        url = urlparse(self.path)
        if url.path != "/api/decision":
            self._json(404, {"error": "no such route"})
            return
        data = self._body()
        text = data.get("text", "")
        round_id = data.get("round")
        try:
            decisions = parse_decision_text(text)
            with pack_lock(self.pack_dir):
                pack, styles = load_pack(self.pack_dir / "pack.json")
                if round_id is None:
                    runs = sorted(
                        p.name for p in (self.pack_dir / ".runs").glob("r*") if p.is_dir()
                    )
                    if not runs:
                        raise ValueError("no rounds under .runs/")
                    round_id = runs[-1]
                log = apply_decisions(
                    self.pack_dir, pack, styles, decisions, round_id, source="server"
                )
            self._json(200, {"rev": pack.get("rev", 0), "log": log})
        except (ValueError, KeyError) as exc:
            self._json(400, {"error": str(exc)})
        except TimeoutError as exc:
            self._json(423, {"error": str(exc)})
        except Exception as exc:  # invalid pack after load etc.
            self._json(500, {"error": str(exc)})

    def do_PUT(self) -> None:
        url = urlparse(self.path)
        if url.path != "/api/icon":
            self._json(404, {"error": "no such route"})
            return
        data = self._body()
        icon_id = data.get("icon")
        patch = {k: data[k] for k in EDITABLE_FIELDS if k in data}
        if not icon_id or not patch:
            self._json(400, {"error": "need icon and at least one editable field"})
            return
        try:
            with pack_lock(self.pack_dir):
                pack, _ = load_pack(self.pack_dir / "pack.json")
                icon = pack["icons"].get(icon_id)
                if icon is None:
                    self._json(404, {"error": f"unknown icon {icon_id}"})
                    return
                icon.update(patch)
                _, errors = revalidate(pack)
                if errors:
                    self._json(400, {"errors": errors})
                    return
                write_pack_atomic(self.pack_dir, pack)
            self._json(200, {"rev": pack.get("rev", 0)})
        except TimeoutError as exc:
            self._json(423, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": str(exc)})


def serve(pack_dir: str | Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    pack_dir = Path(pack_dir)
    handler = type("BoundHandler", (ReviewHandler,), {"pack_dir": pack_dir})
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"iconpilot review — http://{host}:{port}  (pack: {pack_dir})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
