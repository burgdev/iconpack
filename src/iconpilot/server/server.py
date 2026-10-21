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

from iconpilot import __version__
from iconpilot.decide import apply_decisions, parse_decision_text
from iconpilot.pack import (
    advance_feedback,
    load_pack,
    next_run_id,
    prune_runs,
    revalidate,
    write_pack_atomic,
)
from iconpilot.render.contact import contact_sheet
from iconpilot.render.render import render_png_text


def run_gate_svg(svg_text: str, pack: dict, styles: dict, icon_id: str, variant_id: str) -> bool:
    """Quick gate check for a raw SVG string."""
    import tempfile

    from iconpilot.gate.run import run_gate as _gate

    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
        f.write(svg_text)
        path = f.name
    try:
        icon = pack["icons"][icon_id]
        style_id = icon["variants"][variant_id]["style"]
        return _gate(path, pack, styles[style_id], icon_colors=icon.get("colors") or None).passed
    except (KeyError, Exception):
        return False
    finally:
        import os

        os.unlink(path)


EDITABLE_FIELDS = ("brief", "prompt", "main_color", "colors", "note", "description")


_HEX_RE = __import__("re").compile(r"^#[0-9a-fA-F]{6}$")


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
            self.send_header("Cache-Control", "no-cache, must-revalidate")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if url.path == "/api/pack":
            try:
                pack, _ = load_pack(self.pack_dir / "pack.json")
                files = {
                    f"{iid}/{vid}": (self.pack_dir / "icons" / iid / f"{vid}.svg").is_file()
                    for iid, ic in pack.get("icons", {}).items()
                    for vid, vd in ic.get("variants", {}).items()
                }
                import iconpilot.recraft as _rc

                self._json(
                    200,
                    {
                        "rev": pack.get("rev", 0),
                        "version": __version__,
                        "pack": pack,
                        "svg_files": files,
                        "recraft_ready": _rc.resolve_token() is not None,
                    },
                )
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return

        if url.path == "/api/run":
            runs = sorted(p.name for p in (self.pack_dir / ".runs").glob("r*") if p.is_dir())
            wanted = (q.get("round") or [None])[0]
            active = wanted if wanted in runs else (runs[-1] if runs else None)
            entries = []
            _pk: dict = {}
            try:
                _pk, _ = load_pack(self.pack_dir / "pack.json")
            except Exception:  # orphan filter is best-effort
                _pk = {"icons": {}}
            if active:
                for svg in sorted((self.pack_dir / ".runs" / active).rglob("*.svg")):
                    rel = svg.relative_to(self.pack_dir / ".runs" / active).parts
                    if len(rel) != 3:
                        continue
                    var = _pk.get("icons", {}).get(rel[1], {}).get("variants", {}).get(rel[0])
                    if var is None or "style" not in var:
                        continue  # orphan: variant not authored in the pack
                    entries.append({"variant": rel[0], "icon": rel[1], "cand": rel[2][:-4]})
            focus = None
            if active:
                rj = self.pack_dir / ".runs" / active / "round.json"
                if rj.is_file():
                    try:
                        focus = json.loads(rj.read_text()).get("open")
                    except (ValueError, OSError):
                        pass
            # open/locked per icon+variant so the page can badge locked work
            locked: dict[str, bool] = {}
            try:
                pack, _ = load_pack(self.pack_dir / "pack.json")
                for iid, icon in pack["icons"].items():
                    for vid, var in icon.get("variants", {}).items():
                        locked[f"{iid}/{vid}"] = var.get("status") == "approved"
            except Exception:  # badges are cosmetic
                locked = {}
            self._json(
                200,
                {
                    "round": active,
                    "latest": runs[-1] if runs else None,
                    "candidates": entries,
                    "locked": locked,
                    "focus": focus,
                },
            )
            return

        if url.path == "/static/vue.esm-browser.prod.js":
            body = (Path(__file__).parent / "static" / "vue.esm-browser.prod.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.send_header("Cache-Control", "max-age=86400")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if url.path == "/api/render":
            rel = (q.get("p") or [""])[0]
            size = int((q.get("size") or ["48"])[0])
            bg = (q.get("bg") or [""])[0]
            color = (q.get("color") or [""])[0]
            svg = _safe_svg(self.pack_dir, rel)
            if svg is None:
                self._json(404, {"error": "not found"})
                return
            text = svg.read_text()
            if _HEX_RE.match(color):
                text = text.replace("currentColor", color)
            background = bg if _HEX_RE.match(bg) else ("#112119" if bg == "dark" else "#ffffff")
            img = render_png_text(text, size, background=background)
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

        if url.path == "/api/style-detail":
            sid = (q.get("style") or [""])[0]
            try:
                pack, all_styles = load_pack(self.pack_dir / "pack.json")
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            if sid not in all_styles:
                self._json(404, {"error": f"unknown style '{sid}'"})
                return
            from iconpilot.styles import style_refs

            refs = [
                {"name": f.stem, "own": str(f).startswith(str(self.pack_dir))}
                for f in style_refs(self.pack_dir, sid)
            ]
            pinned = [
                {"icon": iid, "variant": vid}
                for iid, icon in pack.get("icons", {}).items()
                for vid, vd in icon.get("variants", {}).items()
                if vd.get("pinned") and vd.get("status") == "approved" and vd.get("style") == sid
            ]
            self._json(
                200,
                {
                    "def": all_styles[sid].as_dict(),
                    "snapshot": (pack.get("styles", {})).get(sid),
                    "refs": refs,
                    "pinned": pinned,
                    "recraft_style_id": (pack.get("recraft", {}).get("style_ids", {}) or {}).get(
                        sid
                    ),
                },
            )
            return
        if url.path == "/api/style-refs":
            from iconpilot.styles import style_refs

            try:
                pack, all_styles = load_pack(self.pack_dir / "pack.json")
            except Exception:
                pack, all_styles = {"icons": {}}, {}
            used = {
                vd.get("style")
                for icon in pack.get("icons", {}).values()
                for vd in icon.get("variants", {}).values()
                if vd.get("style")
            }
            from iconpilot.styles import bundled_refs_path

            out = {}
            for sid in sorted(set(all_styles) | used):
                bundled = sorted((bundled_refs_path() / sid).glob("*.svg"))
                own_dir = self.pack_dir / ".style-refs" / sid
                own = sorted(own_dir.glob("*.svg")) if own_dir.is_dir() else []
                if not bundled and not own:
                    continue
                out[sid] = {
                    "source": "own" if own else "bundled",
                    "bundled": [{"name": f.stem} for f in bundled],
                    "own": [{"name": f.stem} for f in own],
                    "icons": [{"name": f.stem} for f in (own or bundled)],
                }
            self._json(200, out)
            return
        if url.path == "/api/style-ref-file":
            # serve one style reference icon (own or bundled) for rendering
            sid = (q.get("style") or [""])[0]
            name = (q.get("name") or [""])[0]
            if not sid or not name or "/" in sid or "/" in name or ".." in name:
                self._json(400, {"error": "bad style ref request"})
                return
            from iconpilot.styles import style_refs

            for f in style_refs(self.pack_dir, sid):
                if f.stem == name:
                    body = f.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/svg+xml")
                    self.send_header("Cache-Control", "max-age=86400")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
            self._json(404, {"error": "no such reference"})
            return
        if url.path == "/api/recraft-style-request":
            import iconpilot.recraft as _rcs

            sid = (q.get("style") or [""])[0]
            try:
                pack, styles = load_pack(self.pack_dir / "pack.json")
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            if sid not in styles:
                self._json(404, {"error": f"unknown style {sid}"})
                return
            style = styles[sid]
            from iconpilot.styles import style_refs as _sr

            refs = [f.read_text() for f in _sr(self.pack_dir, sid)][:10]
            cfg = pack.get("recraft", {})
            cached = (cfg.get("style_ids", {}) or {}).get(sid) or cfg.get("style_id")
            snap = pack.get("styles", {}).get(sid, {}) or {}
            h = _rcs.refs_hash(refs) if refs else None
            fresh = bool(cached and (not refs or not h or h == snap.get("recraft_style_hash")))
            match = snap.get("recraft_match") or "precise"
            model = "recraftv2_vector" if match == "regular" else "recraftv4_styles"
            request: dict = {"model": model, "match": match}
            if refs:
                request["image_urls"] = [f"<{len(refs)} SVG data URLs>"]
            if model.startswith("recraftv2"):
                request["style"] = "icon"
            ptxt = _rcs.style_prompt_text(style)
            if ptxt:
                request["prompt"] = ptxt
            cols = [c for c in (_rcs.hex_to_rgb(x) for x in list(style.palette or [])[:10]) if c]
            if cols:
                request["palette"] = {"colors": [{"rgb": c} for c in cols]}
            self._json(
                200,
                {
                    "endpoint": _rcs.API_BASE + "/styles",
                    "request": request,
                    "refs_count": len(refs),
                    "cached_id": cached or "",
                    "fresh": fresh,
                    "cost_usd": _rcs.STYLE_CREATE_PRICE,
                },
            )
            return
        if url.path == "/api/recraft-models":
            import iconpilot.recraft as _rc

            self._json(
                200,
                {
                    "prices": dict(_rc.MODEL_PRICES),
                    "suggestions": dict(_rc.STYLE_MODEL_SUGGESTIONS),
                },
            )
            return
        if url.path == "/api/recraft-request":
            icon_id = (q.get("icon") or [""])[0]
            variant = (q.get("variant") or [""])[0]
            import iconpilot.recraft as _rc_mv

            try:
                n = max(1, min(int((q.get("n") or ["4"])[0]), 16))
            except ValueError:
                n = 4
            grid = max(1, min(int((q.get("grid") or ["0"])[0] or 0), 4))
            if grid == 0:
                grid = next((g for g in (1, 2, 3, 4) if _rc_mv.max_versions(g) >= n), 4)
            n = min(n, _rc_mv.max_versions(grid))
            try:
                pack, styles = load_pack(self.pack_dir / "pack.json")
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            icon = pack["icons"].get(icon_id)
            if icon is None or "style" not in icon.get("variants", {}).get(variant, {}):
                self._json(404, {"error": f"no authored variant {icon_id}#{variant}"})
                return
            import iconpilot.recraft as rc
            from iconpilot.context import build_prompt

            plan = self._recraft_plan(icon_id, variant, n_in=n)
            model_override = (q.get("model") or [None])[0]
            # grid-aware: sheet mode for grid>=2, n-mode for grid==1
            if model_override:
                import iconpilot.recraft as _rc2

                if model_override not in _rc2.VECTOR_MODELS:
                    self._json(400, {"error": f"not a vector model: {model_override}"})
                    return
                plan["model"] = model_override
                import iconpilot.recraft as _rc3

                plan["cost"] = round(
                    _rc3.price_per_image(model_override) * plan["n"]
                    + (_rc3.STYLE_REF_PRICE if plan["refs"] else 0),
                    4,
                )
            # build the EXACT request that will be sent
            if grid >= 2:
                actual_prompt = rc.sheet_prompt(plan["prompt"], grid, model=plan["model"])
            else:
                actual_prompt = plan["prompt"]
            req = {
                "model": plan["model"],
                "prompt": actual_prompt,
                "size": "1:1",
                "response_format": "b64_json",
            }
            if grid == 1:
                req["n"] = plan["n"]
            else:
                req["n"] = 1  # one sheet image
            if plan["style_id"]:
                req["style_id"] = plan["style_id"]
                req["style_match"] = "precise" if "v4" in plan["model"] else "regular"
            elif plan.get("curated") and "v4" not in plan["model"]:
                req["style"] = plan["curated"]
            elif plan["refs"]:
                req["style_reference_urls"] = [
                    f"<{len(plan['refs'])} PNG refs, ${rc.STYLE_REF_PRICE}/req>"
                ]
            _ic = (pack["icons"].get(icon_id) or {}).get("colors") or []
            if _ic:
                req["colors"] = list(_ic)  # per-icon subset (Recraft colors control)
            self._json(
                200,
                {
                    "endpoint": rc.API_BASE + "/images/generations/vector",
                    "request": req,
                    "style_refs_attached": len(plan["refs"]),
                    "full_prompt": build_prompt(
                        self.pack_dir, plan["pack"], plan["styles"], icon_id, variant, n=plan["n"]
                    ),
                    "est_cost_usd": plan["cost"],
                    "grid": grid,
                    "versions": plan["n"],
                    "models": list(rc.VECTOR_MODELS),
                },
            )
            return

        if url.path == "/api/icon-runs":
            icon_id = (q.get("icon") or [""])[0]
            runs_dir = self.pack_dir / ".runs"
            out = []
            if runs_dir.is_dir():
                for run in sorted(
                    (p.name for p in runs_dir.glob("r*") if p.is_dir()), reverse=True
                ):
                    for svg in sorted((runs_dir / run).rglob("*.svg")):
                        rel = svg.relative_to(runs_dir / run).parts
                        if len(rel) == 3 and rel[1] == icon_id:
                            out.append(
                                {
                                    "round": run,
                                    "variant": rel[0],
                                    "icon": rel[1],
                                    "cand": rel[2][:-4],
                                    "path": f".runs/{run}/{rel[0]}/{rel[1]}/{rel[2]}",
                                }
                            )
            self._json(200, {"candidates": out})
            return

        if url.path == "/api/prompt":
            icon_id = (q.get("icon") or [""])[0]
            variant = (q.get("variant") or [""])[0]
            try:
                n = int((q.get("n") or ["2"])[0])
            except ValueError:
                n = 2
            n = max(1, min(n, 4))
            try:
                pack, styles = load_pack(self.pack_dir / "pack.json")
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            icon = pack["icons"].get(icon_id)
            if icon is None or "style" not in icon.get("variants", {}).get(variant, {}):
                self._json(404, {"error": f"no authored variant {icon_id}#{variant}"})
                return
            from iconpilot.context import build_prompt

            self._json(
                200, {"prompt": build_prompt(self.pack_dir, pack, styles, icon_id, variant, n=n)}
            )
            return

        if url.path == "/api/styles":
            _, styles = load_pack(self.pack_dir / "pack.json")
            self._json(
                200,
                {
                    sid: {
                        k: v
                        for k, v in st.as_dict().items()
                        if k
                        in (
                            "label",
                            "construction",
                            "color_mode",
                            "stroke",
                            "fill",
                            "size",
                            "palette",
                            "detail",
                            "max_nodes",
                            "min_gap",
                            "guidance",
                        )
                    }
                    for sid, st in styles.items()
                },
            )
            return

        if url.path == "/api/svg-path":
            icon_id = (q.get("icon") or [""])[0]
            variant_id = (q.get("variant") or [""])[0]
            f = self.pack_dir / "icons" / icon_id / f"{variant_id}.svg"
            if f.is_file():
                self._json(200, {"path": str(f.resolve())})
            else:
                # try the latest run candidate
                runs = (
                    sorted(p.name for p in (self.pack_dir / ".runs").glob("r*") if p.is_dir())
                    if (self.pack_dir / ".runs").is_dir()
                    else []
                )
                if runs:
                    cand = (q.get("cand") or ["a1"])[0]
                    f = self.pack_dir / ".runs" / runs[-1] / variant_id / icon_id / f"{cand}.svg"
                    if f.is_file():
                        self._json(200, {"path": str(f.resolve())})
                        return
                self._json(404, {"error": "svg not found"})
            return

        if url.path == "/api/undo":
            try:
                with pack_lock(self.pack_dir):
                    # find the latest backup
                    backup = self.pack_dir / ".pack-backup.json"
                    if not backup.is_file():
                        self._json(404, {"error": "no backup to undo"})
                        return
                    pack = json.loads(backup.read_text())
                    _, errors = revalidate(pack)
                    if errors:
                        self._json(400, {"errors": errors})
                        return
                    write_pack_atomic(self.pack_dir, pack)
                    backup.unlink()
                self._json(200, {"rev": pack.get("rev", 0), "undone": True})
            except TimeoutError as exc:
                self._json(423, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return

        if url.path == "/api/history":
            rounds = []
            runs_dir = self.pack_dir / ".runs"
            try:
                pack, _ = load_pack(self.pack_dir / "pack.json")
            except Exception:
                pack = {"icons": {}}
            if runs_dir.is_dir():
                for run in sorted(p.name for p in runs_dir.glob("r*") if p.is_dir()):
                    info = {
                        "round": run,
                        "decided": False,
                        "icons": {},
                        "instructions": None,
                        "cost_usd": 0.0,
                    }
                    fb_file = runs_dir / run / "feedback.json"
                    if fb_file.is_file():
                        try:
                            info["feedback"] = [
                                {
                                    "author": i.get("author"),
                                    "scope": i.get("scope"),
                                    "icon": i.get("icon"),
                                    "variant": i.get("variant"),
                                    "text": str(i.get("text", "")),
                                    "created": i.get("created"),
                                }
                                for i in json.loads(fb_file.read_text())
                            ]
                        except (ValueError, OSError):
                            pass
                    rj = runs_dir / run / "round.json"
                    if rj.is_file():
                        try:
                            info["cost_usd"] = float(
                                json.loads(rj.read_text()).get("estimated_cost_usd", 0)
                            )
                        except (ValueError, OSError):
                            pass
                    dec = runs_dir / run / "decisions.json"
                    if dec.is_file():
                        try:
                            d = json.loads(dec.read_text())
                            info["decided"] = True
                            info["instructions"] = d.get("instructions")
                            info["icons"] = d.get("icons", {})
                        except (ValueError, OSError):
                            pass
                    if not info["decided"]:
                        cands = [c.stem for c in (runs_dir / run).rglob("*.svg")]
                        info["candidates"] = len(cands)
                    # quality metrics from gate reports
                    gates = list((runs_dir / run).rglob("*.gate.json"))
                    n_pass = 0
                    for g in gates:
                        try:
                            if json.loads(g.read_text()).get("passed"):
                                n_pass += 1
                        except (ValueError, OSError):
                            pass  # mid-write gate file
                    info["metrics"] = {
                        "gate_total": len(gates),
                        "gate_passed": n_pass,
                        "gate_rate": round(n_pass / len(gates), 2) if gates else None,
                    }
                    # approval metrics from pack state
                    approved = sum(
                        1
                        for icon in pack.get("icons", {}).values()
                        for vv in icon.get("variants", {}).values()
                        if vv.get("chosen", {}).get("run") == run
                    )
                    info["metrics"]["approved"] = approved
                    rounds.append(info)
            self._json(200, {"rounds": rounds})
            return

        if url.path == "/api/anchor-suggestions":
            pack, _ = load_pack(self.pack_dir / "pack.json")
            suggestions = []
            for iid, icon in pack["icons"].items():
                for vid, v in icon.get("variants", {}).items():
                    if "style" not in v or v.get("status") != "approved":
                        continue
                    # count positive comments mentioning quality
                    comments = v.get("comments", [])
                    high_scores = sum(
                        1
                        for c in comments
                        if "rated 9" in c.get("text", "") or "rated 10" in c.get("text", "")
                    )
                    if high_scores >= 1 and not v.get("anchor"):
                        suggestions.append(
                            {
                                "icon": iid,
                                "variant": vid,
                                "reason": f"scored 9+ {high_scores} time(s)",
                            }
                        )
            self._json(200, {"suggestions": suggestions})
            return

        if url.path == "/api/ai-status":
            f = self.pack_dir / ".runs" / ".ai-status"
            status = ""
            if f.is_file():
                try:
                    status = f.read_text().strip()
                except OSError:
                    status = ""
            # phase-accurate status: whose turn is it?
            runs = sorted(p.name for p in (self.pack_dir / ".runs").glob("r*") if p.is_dir())
            if runs:
                latest = self.pack_dir / ".runs" / runs[-1]
                has_svgs = any(latest.rglob("*.svg"))
                if (latest / "decisions.json").is_file():
                    status = (
                        f"{runs[-1]} applied — waiting: start the next pass (agent drafts after)"
                    )
                elif not has_svgs:
                    rj = latest / "round.json"
                    open_n = 0
                    if rj.is_file():
                        try:
                            open_n = len(json.loads(rj.read_text()).get("open", []))
                        except (ValueError, OSError):
                            pass
                    status = (
                        f"{runs[-1]} waiting for the agent to draft"
                        f" ({open_n} open variant(s)) — your decisions are applied"
                    )
            phase = "idle"
            if runs:
                latest_p = self.pack_dir / ".runs" / runs[-1]
                if (latest_p / "decisions.json").is_file():
                    phase = "applied"
                elif any(latest_p.rglob("*.svg")):
                    phase = "review"
                else:
                    phase = "agent"
            self._json(200, {"status": status, "active": bool(status), "phase": phase})
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

    def _save_sheets(
        self,
        run: str,
        tag: str,
        grid: int,
        sheets: list[str],
        prompt: str,
        input_svg: str | None = None,
    ) -> None:
        """Keep the raw grid SVGs the pack was seeded from.

        Split cells become candidates, but the un-split sheet (cell layout,
        take numbering, generator quirks) is often exactly what a later
        refine or LLM pass wants. Stored under .runs/<round>/sheets/ with a
        prompt sidecar so the cell→icon mapping stays recoverable.
        """
        import re as _re

        sheets_dir = self.pack_dir / ".runs" / run / "sheets"
        sheets_dir.mkdir(parents=True, exist_ok=True)
        safe_tag = _re.sub(r"[^a-z0-9_.-]", "-", tag.lower())
        g = int(grid)
        if input_svg:
            (sheets_dir / f"{safe_tag}-{g}x{g}-input.svg").write_text(input_svg)
        for i, s in enumerate(sheets):
            (sheets_dir / f"{safe_tag}-{g}x{g}-t{i + 1}.svg").write_text(s)
        prompt_file = sheets_dir / f"{safe_tag}-{g}x{g}.prompt.txt"
        if not prompt_file.is_file():
            prompt_file.write_text(prompt)

    def _ensure_round(self) -> str:
        """Latest run id; starts round one when the pack has none yet.

        Recraft seeding is a first-class way to open a pack — waiting for
        the agent should not be required to pick the first candidates.
        """
        runs_dir = self.pack_dir / ".runs"
        runs = sorted(p.name for p in runs_dir.glob("r*")) if runs_dir.is_dir() else []
        if runs:
            return runs[-1]
        out = self._start_round(None)
        return str(out.get("round") or "r001")

    def _start_round(self, only: list[str] | None = None) -> dict:
        """Create the next run dir; archive live feedback into it (history).

        `only` restricts the round to selected `icon#variant` keys (focus mode).
        """
        import json as _json

        runs_dir = self.pack_dir / ".runs"
        run = next_run_id(runs_dir)
        (runs_dir / run).mkdir(parents=True, exist_ok=True)
        carried = 0
        try:
            with pack_lock(self.pack_dir):
                pack, _ = load_pack(self.pack_dir / "pack.json")
                carried = len(advance_feedback(pack, runs_dir / run))
                write_pack_atomic(self.pack_dir, pack)
            open_ = [
                f"{iid}#{vid}"
                for iid, icon in pack["icons"].items()
                for vid, var in icon.get("variants", {}).items()
                if "style" in var
                and "link" not in var
                and var.get("status") != "approved"
                and not var.get("postponed")
            ]
            if only is not None:
                wanted = set(only)
                candidates = {
                    f"{iid}#{vid}"
                    for iid, icon in pack["icons"].items()
                    for vid, var in icon.get("variants", {}).items()
                    if "style" in var and "link" not in var and var.get("status") != "approved"
                }  # postponed included: explicit focus wins over postpone
                unknown = wanted - candidates
                if unknown:
                    raise ValueError(f"not open (or locked): {sorted(unknown)}")
                open_ = sorted(wanted)
        except ValueError:
            raise
        except Exception:
            open_ = []
        (runs_dir / run / "round.json").write_text(
            _json.dumps({"round": run, "open": open_, "feedback_carried": carried}) + "\n"
        )
        return {"round": run, "open": open_, "feedback_carried": carried}

    def _heal_bad_style(self, token: str, style_key: str, style, refs: list[str]) -> str | None:
        """A cached style with the wrong base (Recraft 'any') poisons every
        generation. Delete it remotely + locally, recreate with the correct
        vector base, return the fresh id (or None)."""
        import iconpilot.recraft as rc

        if not refs:
            return None
        # one lock across purge + recreate: concurrent drafts can't both
        # recreate (duplicate styles + double cost) and none can read the
        # purged cache mid-heal
        with pack_lock(self.pack_dir):
            pk, _ = load_pack(self.pack_dir / "pack.json")
            bad = (pk.get("recraft", {}).get("style_ids", {}) or {}).get(style_key)
            if bad:
                try:
                    rc._request(token, "DELETE", f"/styles/{bad}")
                except Exception:  # noqa: S110 — remote cleanup is best-effort
                    pass
            out = rc.create_style(
                token,
                refs,
                prompt=rc.style_prompt_text(style),
                palette=list(getattr(style, "palette", None) or []),
            )
            new_id = out["id"]
            snap = pk.setdefault("styles", {}).setdefault(style_key, {})
            snap["recraft_style_id"] = new_id
            snap["recraft_style_hash"] = rc.refs_hash(refs)
            pk.setdefault("recraft", {}).setdefault("style_ids", {})[style_key] = new_id
            write_pack_atomic(self.pack_dir, pk)
        rc.style_cache_put(rc.refs_hash(refs), new_id, style_key)
        return new_id

    def _ensure_style_id(self, token: str, style_key: str, style, refs: list[str]) -> str | None:
        """Cached Recraft style for `style_key`, creating it when missing/stale.

        The style bakes in the look (prompt) and the color world (palette),
        so generations with it need neither in the icon prompt. $0.005,
        cached until refs change (hash). Returns None when there are no
        refs to build a style from.
        """
        import iconpilot.recraft as rc

        with pack_lock(self.pack_dir):
            pack, _ = load_pack(self.pack_dir / "pack.json")
        cfg = pack.get("recraft", {})
        cached = (cfg.get("style_ids", {}) or {}).get(style_key) or cfg.get("style_id")
        h = rc.refs_hash(refs) if refs else None
        snap_h = (pack.get("styles", {}).get(style_key, {}) or {}).get("recraft_style_hash")
        if cached and (not refs or not h or h == snap_h):
            return cached
        if not refs:
            return cached  # manual/curated id without refs: trust as-is
        # account-level cache: same bundled refs in another pack already
        # created this style — reuse it and mirror into this pack
        if h:
            account_id = rc.style_cache_get(h)
            if account_id and account_id != cached:
                with pack_lock(self.pack_dir):
                    pk, _ = load_pack(self.pack_dir / "pack.json")
                    snap = pk.setdefault("styles", {}).setdefault(style_key, {})
                    snap["recraft_style_id"] = account_id
                    snap["recraft_style_hash"] = h
                    pk.setdefault("recraft", {}).setdefault("style_ids", {})[style_key] = account_id
                    write_pack_atomic(self.pack_dir, pk)
                return account_id
        out = rc.create_style(
            token,
            refs,
            prompt=rc.style_prompt_text(style),
            palette=list(getattr(style, "palette", None) or []),
        )
        new_id = out["id"]
        with pack_lock(self.pack_dir):
            pk, _ = load_pack(self.pack_dir / "pack.json")
            snap = pk.setdefault("styles", {}).setdefault(style_key, {})
            snap["recraft_style_id"] = new_id
            snap["recraft_style_hash"] = h
            pk.setdefault("recraft", {}).setdefault("style_ids", {})[style_key] = new_id
            write_pack_atomic(self.pack_dir, pk)
        if h:
            rc.style_cache_put(h, new_id, style_key)
        return new_id

    def _recraft_plan(self, icon_id: str, variant: str, n_in: int | None = None) -> dict:
        """Everything a Recraft call needs: prompt, style target, model, n, cost.

        Style targeting, in order: pack style_id (custom style) → reference
        SVGs attached as style_reference_urls (data URLs) → plain model.
        """
        import iconpilot.recraft as rc

        pack, styles = load_pack(self.pack_dir / "pack.json")
        icon = pack["icons"][icon_id]
        v = icon["variants"][variant]
        style = styles[v["style"]]
        cfg = pack.get("recraft", {})

        n = n_in or cfg.get("n") or 4
        n = max(1, min(int(n), 16))  # sheet mode allows up to grid² = 16

        prompt = rc.draft_prompt(icon, style, pack)
        style_id = cfg.get("style_ids", {}).get(v["style"]) or cfg.get("style_id")

        refs: list[str] = []
        if True:  # always collect — needed for staleness check + V4 fallback
            # ALL style refs (own uploads + bundled) as the look, then
            # pinned/approved pack icons on the same style
            from iconpilot.styles import style_refs as _sr

            for f in _sr(self.pack_dir, v["style"]):
                refs.append(f.read_text())
            # add pinned/approved pack icons (up to Recraft's 10-image limit total)
            for iid, ic in pack["icons"].items():
                for vid, vd in ic.get("variants", {}).items():
                    if len(refs) >= 10:
                        break
                    if (
                        vd.get("pinned")
                        and vd.get("status") == "approved"
                        and vd.get("style") == v["style"]
                    ):
                        f = self.pack_dir / "icons" / iid / f"{vid}.svg"
                        if f.is_file():
                            refs.append(f.read_text())
            if not refs:
                for vid, vd in icon.get("variants", {}).items():
                    if vid != variant and vd.get("status") == "approved":
                        f = self.pack_dir / "icons" / icon_id / f"{vid}.svg"
                        if f.is_file():
                            refs = [f.read_text()]
                            break

        style_snap = pack.get("styles", {}).get(v.get("style"), {})
        curated = style_snap.get("recraft_curated") or rc.CURATED_STYLE_MAP.get(v["style"])

        # stale style check: if refs changed since style creation, recreate
        snap_style_id = style_snap.get("recraft_style_id")
        snap_hash = style_snap.get("recraft_style_hash")
        needs_style_refresh = False
        if snap_style_id and snap_hash and refs and rc.refs_hash(refs) != snap_hash:
            style_id = None
            needs_style_refresh = True
        per_style_model = style_snap.get("recraft_model")
        model = (
            per_style_model
            or cfg.get("model")
            or (
                rc.FALLBACK_MODEL
                if (curated or style_id)
                else rc.DEFAULT_MODEL
                if refs
                else rc.FALLBACK_MODEL
            )
        )
        if model not in rc.VECTOR_MODELS:
            raise ValueError(f"model must be a vector model, got '{model}'")

        images_billed = 1 if n > 6 else n
        cost = rc.price_per_image(model) * images_billed
        if refs and "v4" in model and not style_id:
            cost += rc.STYLE_REF_PRICE
        if needs_style_refresh:
            cost += rc.STYLE_CREATE_PRICE
        return {
            "prompt": prompt,
            "style_id": style_id,
            "curated": curated,
            "needs_style_refresh": needs_style_refresh,
            "refs": refs,
            "model": model,
            "n": n,
            "cost": round(cost, 4),
            "pack": pack,
            "styles": styles,
            "style": style,
        }

    def _recraft_preview(self, data: dict) -> dict:
        """Generate and return SVG contents WITHOUT writing to disk.

        The page shows these in a review dialog; the user picks which to keep,
        then /api/recraft-commit writes the selection.
        """
        import base64 as _b64

        import iconpilot.recraft as rc

        token = rc.resolve_token()
        if not token:
            raise ValueError("no Recraft token on the server")

        pack, styles = load_pack(self.pack_dir / "pack.json")
        plan = self._recraft_plan(
            data.get("icon", ""), data.get("variant", ""), n_in=int(data.get("n") or 4)
        )
        if data.get("prompt"):
            plan["prompt"] = (plan["prompt"] + ", " + str(data["prompt"]))[:1000]

        style_id = plan["style_id"]
        if not style_id and plan["refs"]:
            # no cached style yet → create it now ($0.005, cached after)
            try:
                style_id = self._ensure_style_id(
                    token, plan["style"], styles[plan["style"]], plan["refs"]
                )
            except rc.RecraftError:
                style_id = None
        if style_id:
            # look + palette live in the style: prompt names only the subject
            icon = pack["icons"][data.get("icon", "")]
            plan["prompt"] = rc.draft_prompt(
                icon, styles[plan["style"]], pack, model=plan["model"], styled=False
            )
            if data.get("prompt"):
                plan["prompt"] = (plan["prompt"] + ", " + str(data["prompt"]))[:10000]
        ref_urls = None
        if plan["refs"] and "v4" in plan["model"] and not plan.get("curated") and not style_id:
            # PNG conversion for V4 refs

            png_urls = []
            for svg_text in plan["refs"]:
                try:
                    png_urls.append(rc.png_data_url(svg_text, 256))
                except (ValueError, OSError):
                    pass
            ref_urls = png_urls or None

        grid = int(data.get("grid") or 0)
        icon = pack["icons"][data.get("icon", "")]
        icon_colors = icon.get("colors") or None
        if grid >= 2:
            sheet = rc.generate(
                token,
                rc.sheet_prompt(plan["prompt"], grid, model=plan["model"]),
                n=1,
                style_id=style_id,
                model=plan["model"],
                reference_urls=ref_urls,
                curated_style=plan.get("curated"),
                colors=icon_colors,
            )
            cells = rc.split_sheet(sheet[0], grid)
        else:
            cells = rc.generate(
                token,
                plan["prompt"],
                n=plan["n"],
                colors=icon_colors,
                style_id=style_id,
                model=plan["model"],
                reference_urls=ref_urls,
                curated_style=plan.get("curated"),
            )

        # normalize + gate each, return as data URLs for preview
        viewbox = pack["spec"]["viewBox"]
        mono = styles[plan["style"]].color_mode == "mono"
        results = []
        for i, raw in enumerate(cells):
            svg = rc.normalize(rc.strip_metadata(raw), viewbox, mono=mono)
            b64 = _b64.b64encode(svg.encode()).decode()
            results.append(
                {
                    "id": i,
                    "svg_data": f"data:image/svg+xml;base64,{b64}",
                    "gate_pass": run_gate_svg(
                        svg,
                        pack,
                        styles,
                        str(data.get("icon") or ""),
                        str(data.get("variant") or ""),
                    ),
                }
            )
        return {
            "results": results,
            "model": plan["model"],
            "grid": grid,
            "cost_usd": round(rc.price_per_image(plan["model"]), 2),
        }

    def _recraft_commit(self, data: dict) -> dict:
        """Write user-picked SVG candidates to the run directory.

        Body: {icon, variant, svgs} for one icon, or {items: [{icon,
        variant, svgs}], cost_usd?} for pack drafts. Nothing lands on disk
        before this — generation endpoints only return previews.
        """
        import json as _json

        from iconpilot.gate.run import run_gate

        items = data.get("items") or [
            {
                "icon": data.get("icon", ""),
                "variant": data.get("variant", ""),
                "svgs": data.get("svgs", []),
            }
        ]
        if not items or any(
            not it.get("icon") or not it.get("variant") or not it.get("svgs") for it in items
        ):
            raise ValueError("need icon, variant, svgs (or items[])")

        with pack_lock(self.pack_dir):
            pack, styles = load_pack(self.pack_dir / "pack.json")
        runs_dir = self.pack_dir / ".runs"
        run = self._ensure_round()

        wrote_all, pass_all, n_all = [], 0, 0
        with pack_lock(self.pack_dir):
            for it in items:
                icon_id, variant, svgs = it["icon"], it["variant"], it["svgs"]
                icon = pack["icons"].get(icon_id)
                if icon is None or "style" not in icon.get("variants", {}).get(variant, {}):
                    raise ValueError(f"no authored variant {icon_id}#{variant}")
                style = styles[icon["variants"][variant]["style"]]
                cand_dir = runs_dir / run / variant / icon_id
                cand_dir.mkdir(parents=True, exist_ok=True)
                existing = len(list(cand_dir.glob("r*.svg")))
                for i, svg_text in enumerate(svgs, start=1):
                    f = cand_dir / f"r{existing + i}.svg"
                    f.write_text(svg_text)
                    wrote_all.append(f"{icon_id}#{variant}:{f.name}")
                    n_all += 1
                    if run_gate(
                        f,
                        pack,
                        style,
                        icon_colors=pack["icons"].get(icon_id, {}).get("colors") or None,
                    ).passed:
                        pass_all += 1
            # cost bookkeeping
            if data.get("cost_usd"):
                round_json = runs_dir / run / "round.json"
                try:
                    rj = _json.loads(round_json.read_text()) if round_json.is_file() else {}
                except ValueError:
                    rj = {}
                rj.setdefault("models_used", {})["seeder"] = "recraft"
                rj["estimated_cost_usd"] = round(
                    rj.get("estimated_cost_usd", 0) + float(data["cost_usd"]), 4
                )
                rj["candidates_generated"] = rj.get("candidates_generated", 0) + n_all
                round_json.write_text(_json.dumps(rj, indent=2) + "\n")
        return {"round": run, "wrote": wrote_all, "gate_passed": pass_all}

    def _recraft_draft(self, data: dict) -> dict:
        """Seed Recraft candidates for one icon (+optional variant) into the latest run."""
        import iconpilot.recraft as rc
        from iconpilot.gate.run import run_gate

        icon_id = data.get("icon") or ""
        variant = data.get("variant")
        try:
            n = int(data.get("n") or 0) or None
        except (TypeError, ValueError) as exc:
            raise ValueError("n must be an integer 1-6") from exc
        if n is not None and not 1 <= n <= 16:
            raise ValueError("n must be 1-16")
        with pack_lock(self.pack_dir):
            pack, _styles = load_pack(self.pack_dir / "pack.json")
        icon = pack["icons"].get(icon_id)
        if icon is None:
            raise ValueError(f"unknown icon '{icon_id}'")
        variants = [v for v in icon.get("variants", {}) if "style" in icon["variants"][v]]
        if variant:
            if variant not in variants:
                raise ValueError(f"no variant '{variant}' on {icon_id}")
        elif len(variants) == 1:
            variant = variants[0]
        else:
            raise ValueError(f"{icon_id} has variants {variants} — pass 'variant'")
        if icon["variants"][variant].get("status") == "approved":
            raise ValueError(f"{icon_id}#{variant} is approved/locked — unlock to redraft")
        token = rc.resolve_token()
        if not token:
            raise ValueError("no Recraft token on the server — set RECRAFT_API_TOKEN")

        plan = self._recraft_plan(icon_id, variant, n_in=n)
        if data.get("prompt"):
            plan["prompt"] = (plan["prompt"] + ", " + str(data["prompt"]))[:1000]
        style_id = plan["style_id"]
        style = plan["style"]

        # Recraft rejects SVG references — render to PNG first
        # auto-refresh stale Recraft styles ($0.005, cached until refs change)
        if plan.get("needs_style_refresh") and plan["refs"]:
            try:
                new_style = rc.create_style(token, plan["refs"])
                new_id = new_style["id"]
                pack_style = pack["icons"][icon_id]["variants"][variant]["style"]
                with pack_lock(self.pack_dir):
                    pk, _ = load_pack(self.pack_dir / "pack.json")
                    snap = pk.setdefault("styles", {}).setdefault(pack_style, {})
                    snap["recraft_style_id"] = new_id
                    snap["recraft_style_hash"] = rc.refs_hash(plan["refs"])
                    pk.setdefault("recraft", {}).setdefault("style_ids", {})[pack_style] = new_id
                    write_pack_atomic(self.pack_dir, pk)
                plan["style_id"] = new_id
                style_id = new_id
                plan["needs_style_refresh"] = False
            except rc.RecraftError:
                pass
        ref_urls = None
        # V2 + curated = use style param (no refs needed)
        # V2 without curated but with refs → upgrade to V4 (refs need V4)
        if plan["refs"] and "v4" not in plan["model"] and not plan.get("curated"):
            plan["model"] = rc.DEFAULT_MODEL
        if plan["refs"] and "v4" in plan["model"] and not plan.get("curated") and not style_id:
            png_urls = []
            for svg_text in plan["refs"]:
                try:
                    png_urls.append(rc.png_data_url(svg_text, 256))
                except (ValueError, OSError):
                    pass  # skip unrenderable refs
            ref_urls = png_urls or None
            # auto-upgrade: refs need V4 — don't send them to V2 models
            if ref_urls and "v4" not in plan["model"]:
                plan["model"] = rc.DEFAULT_MODEL  # v4_styles_vector
            import sys as _sys

            print(
                f"DEBUG recraft: model={plan['model']} style_id={plan.get('style_id')} "
                f"refs={len(plan['refs'])} png_refs={len(png_urls)} ref_urls={len(ref_urls) if ref_urls else 0} "
                f"refs_detail={[u[:40] for u in (ref_urls or [])[:1]]}",
                file=_sys.stderr,
            )
        grid = int(data.get("grid") or 0)
        if grid == 0:
            grid = int(data.get("sheet") or 0)  # backwards compat
            grid = max(2, min(grid, 4)) if grid else 0
        if grid >= 2:
            sheet_svgs = rc.generate(
                token,
                rc.sheet_prompt(plan["prompt"], grid, model=plan["model"]),
                n=1,
                style_id=style_id,
                model=plan["model"],
                reference_urls=ref_urls,
                curated_style=plan.get("curated"),
            )
            cells = rc.split_sheet(sheet_svgs[0], grid, target=24.0)
            svgs = cells  # keep ALL cells — same cost, more candidates
        else:
            svgs = rc.generate(
                token,
                plan["prompt"],
                n=plan["n"],
                style_id=style_id,
                model=plan["model"],
                reference_urls=ref_urls,
                curated_style=plan.get("curated"),
            )
        n = plan["n"]

        runs_dir = self.pack_dir / ".runs"
        run = self._ensure_round()
        # count + write + cost record under the pack lock: closes the concurrent
        # draft race (two tabs double-firing the same icon/variant).
        import json as _json

        viewbox = pack["spec"]["viewBox"]
        with pack_lock(self.pack_dir):
            _pk, _styles = load_pack(self.pack_dir / "pack.json")
        try:
            _mono = (
                _styles[_pk["icons"][icon_id]["variants"][variant]["style"]].color_mode == "mono"
            )
        except (KeyError, TypeError):
            _mono = False
        normalized = [rc.normalize(raw, viewbox, mono=_mono) for raw in svgs]
        with pack_lock(self.pack_dir):
            cand_dir = runs_dir / run / variant / icon_id
            cand_dir.mkdir(parents=True, exist_ok=True)
            existing = len(list(cand_dir.glob("r*.svg")))
            wrote = []
            n_pass = 0
            for i, svg in enumerate(normalized, start=1):
                f = cand_dir / f"r{existing + i}.svg"
                f.write_text(svg)
                wrote.append(f.name)
                if run_gate(
                    f, pack, style, icon_colors=pack["icons"].get(icon_id, {}).get("colors") or None
                ).passed:
                    n_pass += 1
            round_json = runs_dir / run / "round.json"
            try:
                rj = _json.loads(round_json.read_text()) if round_json.is_file() else {}
            except ValueError:
                rj = {}
            rj.setdefault("models_used", {})["seeder"] = plan["model"]
            rj["estimated_cost_usd"] = round(rj.get("estimated_cost_usd", 0) + plan["cost"], 4)
            round_json.write_text(_json.dumps(rj, indent=2) + "\n")
        return {
            "round": run,
            "icon": icon_id,
            "variant": variant,
            "wrote": wrote,
            "gate_passed": n_pass,
            "cost_usd": round(
                rc.price_per_image(plan["model"]) * (1 if grid >= 2 else plan["n"]), 2
            ),
            "model": plan["model"],
            "grid": grid,
        }

    def _recraft_style_create(self, data: dict) -> dict:
        """Create the Recraft custom style for a pack style ($0.005, cached)."""
        import iconpilot.recraft as rc

        token = rc.resolve_token()
        if not token:
            raise ValueError("no Recraft token on the server — set RECRAFT_API_TOKEN")
        sid = str(data.get("style") or "")
        with pack_lock(self.pack_dir):
            pack, styles = load_pack(self.pack_dir / "pack.json")
        if sid not in styles:
            raise ValueError(f"unknown style {sid}")
        style = styles[sid]
        from iconpilot.styles import style_refs as _sr

        refs = [f.read_text() for f in _sr(self.pack_dir, sid)][:10]
        if not refs:
            raise ValueError(f"style {sid} has no reference icons — add refs first")
        snap = pack.get("styles", {}).get(sid, {}) or {}
        match = snap.get("recraft_match") or "precise"
        out = rc.create_style(
            token,
            refs,
            match=match,
            prompt=rc.style_prompt_text(style),
            palette=list(style.palette or []),
        )
        new_id = out["id"]
        h = rc.refs_hash(refs)
        with pack_lock(self.pack_dir):
            pk, _ = load_pack(self.pack_dir / "pack.json")
            snap = pk.setdefault("styles", {}).setdefault(sid, {})
            snap["recraft_style_id"] = new_id
            snap["recraft_style_hash"] = h
            pk.setdefault("recraft", {}).setdefault("style_ids", {})[sid] = new_id
            write_pack_atomic(self.pack_dir, pk)
        rc.style_cache_put(h, new_id, sid)
        return {"style_id": new_id, "cost_usd": rc.STYLE_CREATE_PRICE}

    def _recraft_style_save(self, data: dict) -> dict:
        """Save a manually created Recraft style UUID onto a pack style."""
        import re as _re

        import iconpilot.recraft as rc

        sid = str(data.get("style") or "")
        rid = str(data.get("style_id") or "").strip()
        if not _re.fullmatch(r"[0-9a-fA-F-]{32,36}", rid):
            raise ValueError("style_id must be a Recraft UUID")
        with pack_lock(self.pack_dir):
            _, styles = load_pack(self.pack_dir / "pack.json")
        if sid not in styles:
            raise ValueError(f"unknown style {sid}")
        from iconpilot.styles import style_refs as _sr

        refs = [f.read_text() for f in _sr(self.pack_dir, sid)][:10]
        with pack_lock(self.pack_dir):
            pk, _ = load_pack(self.pack_dir / "pack.json")
            snap = pk.setdefault("styles", {}).setdefault(sid, {})
            snap["recraft_style_id"] = rid
            if refs:
                snap["recraft_style_hash"] = rc.refs_hash(refs)
            pk.setdefault("recraft", {}).setdefault("style_ids", {})[sid] = rid
            write_pack_atomic(self.pack_dir, pk)
        if refs:
            rc.style_cache_put(rc.refs_hash(refs), rid, sid)
        return {"style_id": rid}

    def _adopt_preview(self, data: dict) -> dict:
        """Process a seed deterministically; nothing is written. Soft gating:
        gate errors are returned for the user to judge, never blocking."""
        import base64 as _b64

        from iconpilot.adopt import adopt_svg

        icon_id = str(data.get("icon") or "")
        variant = str(data.get("variant") or "")
        with pack_lock(self.pack_dir):
            pack, styles = load_pack(self.pack_dir / "pack.json")
        icon = pack["icons"].get(icon_id)
        var = (icon or {}).get("variants", {}).get(variant)
        if var is None or "style" not in var:
            raise ValueError(f"no authored variant {icon_id}#{variant}")
        style = styles[var["style"]]

        runs_dir = self.pack_dir / ".runs"
        runs = sorted(p.name for p in runs_dir.glob("r*") if p.is_dir())
        run = runs[-1] if runs else None
        cand = str(data.get("cand") or "")
        src = None
        if data.get("approved") or not cand:
            f = self.pack_dir / "icons" / icon_id / f"{variant}.svg"
            if f.is_file():
                src = f
        if src is None and run and cand:
            f = runs_dir / run / variant / icon_id / f"{cand}.svg"
            if f.is_file():
                src = f
        if src is None:
            raise ValueError("need cand (current round) or an approved icon")

        out, fixes, gate_errors, kept = adopt_svg(src.read_text(), style, pack)
        b64 = _b64.b64encode(out.encode()).decode()
        return {
            "icon": icon_id,
            "variant": variant,
            "cand": cand,
            "source": str(src.relative_to(self.pack_dir)),
            "svg_data": f"data:image/svg+xml;base64,{b64}",
            "fixes": fixes,
            "gate_pass": not gate_errors,
            "gate_errors": gate_errors,
            "kept_colors": kept,
        }

    def _adopt_commit(self, data: dict) -> dict:
        """Write an adopted seed as the variant's icon. No hard gating —
        remaining gate issues are recorded as a comment for traceability."""
        import shutil

        from iconpilot.pack import file_sha256

        icon_id = str(data.get("icon") or "")
        variant = str(data.get("variant") or "")
        svg = str(data.get("svg") or "")
        cand = str(data.get("cand") or "")
        gate_errors = data.get("gate_errors") or []
        kept = data.get("kept_colors") or []
        if not svg.startswith("<svg"):
            raise ValueError("need the adopted svg text")
        with pack_lock(self.pack_dir):
            pack, _styles = load_pack(self.pack_dir / "pack.json")
        if kept:
            lst = pack["icons"].setdefault(icon_id, {}).setdefault("colors", [])
            have = set(lst)
            for c in kept:
                if c not in have:
                    lst.append(c)
        icon = pack["icons"].get(icon_id)
        var = (icon or {}).get("variants", {}).get(variant)
        if var is None or "style" not in var:
            raise ValueError(f"no authored variant {icon_id}#{variant}")
        runs_dir = self.pack_dir / ".runs"
        runs = sorted(p.name for p in runs_dir.glob("r*") if p.is_dir())
        run = runs[-1] if runs else "adopt"

        dest = self.pack_dir / "icons" / icon_id / f"{variant}.svg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        # adopt keeps a copy of the raw seed alongside for traceability
        if cand:
            raw = runs_dir / run / variant / icon_id / f"{cand}.svg"
            if raw.is_file():
                history = dest.parent / f"{variant}.seed-{cand}.svg"
                shutil.copyfile(raw, history)
        dest.write_text(svg)
        var["status"] = "approved"
        var["chosen"] = {"run": run, "variant": f"adopt:{cand}" if cand else "adopt"}
        var["content_hash"] = file_sha256(dest)
        notes = [f"[adopt] from {cand or 'approved'} (deterministic post-process)"]
        if gate_errors:
            notes.append(f"[adopt] open gate issues: {'; '.join(e[:120] for e in gate_errors[:4])}")
        for n in notes:
            var.setdefault("comments", []).append({"round": run, "text": n})
        pack["rev"] = pack.get("rev", 0) + 1
        write_pack_atomic(self.pack_dir, pack)
        return {
            "rev": pack["rev"],
            "dest": str(dest.relative_to(self.pack_dir)),
            "gate_issues": len(gate_errors),
        }

    def _recraft_refine(self, data: dict) -> dict:
        """Recraft refine: existing take + round feedback → i2i variants.

        Body: {targets: ["icon#variant"], feedback?: {target: text},
        strength: 0.3, takes: 2, model?, debug?}. Source per target:
        approved file → best-rated candidate of the current run → skip.
        Requires feedback text (from the current round or the request) —
        nothing to refine without it. Preview only; commit via
        /api/recraft-commit like all Recraft results.
        """
        import base64 as _b64
        import re as _re

        import iconpilot.recraft as rc

        token = rc.resolve_token()
        if not token and not data.get("debug"):
            raise ValueError("no Recraft token on the server — set RECRAFT_API_TOKEN")
        strength = max(0.0, min(float(data.get("strength") or 0.3), 1.0))
        takes = max(1, min(int(data.get("takes") or 2), 6))
        model = data.get("model") or "recraftv4_1_vector"
        if model not in rc.REFINE_MODELS:
            raise ValueError(f"refine needs a v4+ vector model, got '{model}'")
        overrides = data.get("feedback") or {}

        with pack_lock(self.pack_dir):
            pack, styles = load_pack(self.pack_dir / "pack.json")
        runs_dir = self.pack_dir / ".runs"
        run = self._ensure_round()

        items: list[dict] = []
        skipped: list[dict] = []
        calls: list[dict] = []
        cost = 0.0
        try:
            grid_sel = max(0, min(int(data.get("grid") or 0), 5))
        except (TypeError, ValueError):
            grid_sel = 0
        ready: list[dict] = []  # targets with source + feedback, in request order
        for target in data.get("targets", []):
            iid, _, vid = str(target).partition("#")
            icon = pack["icons"].get(iid)
            var = (icon or {}).get("variants", {}).get(vid)
            if var is None or "style" not in var:
                raise ValueError(f"no authored variant {iid}#{vid}")
            # feedback: request override → current-round variant feedback
            fb = str(overrides.get(target) or "").strip()
            if not fb:
                fbs = [
                    f.get("text", "")
                    for f in pack.get("feedback", [])
                    if f.get("scope") == "variant"
                    and f.get("icon") == iid
                    and f.get("variant") == vid
                    and f.get("round") == run
                ]
                fb = "; ".join(x for x in fbs if x).strip()
            # source: approved file → best-rated candidate in current run
            source_path = None
            approved = self.pack_dir / "icons" / iid / f"{vid}.svg"
            if approved.is_file():
                source_path = approved
            cand_dir = runs_dir / run / vid / iid
            cands = sorted(cand_dir.glob("r*.svg")) if cand_dir.is_dir() else []
            if source_path is None and cands:
                best_n, best_r = None, -1
                for c in var.get("comments", []):
                    m = _re.match(r"\[(r\d+)\] rated (\d+)/10", c.get("text", ""))
                    if (
                        m
                        and int(m.group(2)) >= best_r
                        and (cand_dir / f"{m.group(1)}.svg").is_file()
                    ):
                        best_n, best_r = m.group(1), int(m.group(2))
                source_path = cand_dir / f"{best_n}.svg" if best_n else cands[-1]
            if source_path is None:
                skipped.append({"target": target, "reason": "no take to refine — draft first"})
                continue
            if not fb:
                skipped.append(
                    {"target": target, "reason": "no feedback this round — add feedback first"}
                )
                continue
            ready.append(
                {
                    "target": target,
                    "iid": iid,
                    "vid": vid,
                    "style": var["style"],
                    "source": source_path,
                    "fb": fb,
                }
            )

        def _norm_gate(raw_svg: str, style_id: str, iid2: str, vid2: str) -> dict:
            style = styles[style_id]
            svg = rc.normalize(
                rc.strip_metadata(raw_svg), pack["spec"]["viewBox"], mono=style.color_mode == "mono"
            )
            b64 = _b64.b64encode(svg.encode()).decode()
            return {
                "id": 0,
                "svg_data": f"data:image/svg+xml;base64,{b64}",
                "gate_pass": run_gate_svg(svg, pack, styles, iid2, vid2),
            }

        if grid_sel >= 2:
            # grid refine: chunk ready targets (grouped by style) into
            # g×g sheets of source images — ONE i2i call per sheet, then
            # split the returned sheet back into per-icon candidates
            by_style: dict[str, list[dict]] = {}
            for r_ in ready:
                by_style.setdefault(r_["style"], []).append(r_)
            for style_id, group in by_style.items():
                label = styles[style_id].label
                for i0 in range(0, len(group), grid_sel * grid_sel):
                    chunk = group[i0 : i0 + grid_sel * grid_sel]
                    g = rc.pack_grid(len(chunk), max_grid=grid_sel)
                    changes = [f"{c_['iid']} icon ({label}) — change: {c_['fb']}" for c_ in chunk]
                    anchor = rc.style_anchor(styles[style_id])
                    prompt = rc.refine_sheet_prompt(changes, g, model=model, style_phrase=anchor)
                    grid_svg = rc.refine_grid_svg([c_["source"].read_text() for c_ in chunk], g)
                    c_cost = round(rc.price_per_image(model) * takes, 4)
                    calls.append(
                        {
                            "target": "+".join(c_["target"] for c_ in chunk),
                            "grid": g,
                            "cells": len(chunk),
                            "source": "grid sheet",
                            "prompt": prompt,
                            "strength": strength,
                            "takes": takes,
                            "model": model,
                            "cost": c_cost,
                        }
                    )
                    cost += c_cost
                    if data.get("debug"):
                        continue
                    sheets = rc.refine(
                        token, grid_svg, prompt, strength, model=model, n=takes, size=g * 512
                    )
                    self._save_sheets(
                        run, f"refine-{style_id}", g, sheets, prompt, input_svg=grid_svg
                    )
                    split_sheets = [rc.split_sheet(s, g) for s in sheets]
                    for k, c_ in enumerate(chunk):
                        results = []
                        for cells in split_sheets:
                            if k >= len(cells):
                                continue
                            r2 = _norm_gate(cells[k], c_["style"], c_["iid"], c_["vid"])
                            r2["id"] = len(results)
                            results.append(r2)
                        if results:
                            items.append(
                                {"icon": c_["iid"], "variant": c_["vid"], "results": results}
                            )
        else:
            for r_ in ready:
                c_cost = round(rc.price_per_image(model) * takes, 4)
                anchor = rc.style_anchor(styles[r_["style"]])
                calls.append(
                    {
                        "target": r_["target"],
                        "source": str(r_["source"].relative_to(self.pack_dir)),
                        "prompt": anchor + " Change: " + r_["fb"],
                        "strength": strength,
                        "takes": takes,
                        "model": model,
                        "cost": c_cost,
                    }
                )
                cost += c_cost
                if data.get("debug"):
                    continue
                svgs = rc.refine(
                    token,
                    r_["source"].read_text(),
                    anchor + " Change: " + r_["fb"],
                    strength,
                    model=model,
                    n=takes,
                )
                results = []
                for i, raw in enumerate(svgs):
                    res = _norm_gate(raw, r_["style"], r_["iid"], r_["vid"])
                    res["id"] = i
                    results.append(res)
                items.append({"icon": r_["iid"], "variant": r_["vid"], "results": results})

        out: dict = {
            "takes": takes,
            "grid": grid_sel,
            "strength": strength,
            "model": model,
            "cost_usd": round(cost, 4),
            "skipped": skipped,
            "calls": calls,
        }
        if not data.get("debug"):
            out["items"] = items
        return out

    def _recraft_batch(self, data: dict) -> dict:
        """Pack draft: same icons on every sheet, takes vary ACROSS sheets.

        Body: {targets: ["icon#variant", ...], takes: 4, model?: str,
        debug?: bool}. Icons are grouped by style and chunked ≤9 per 3×3
        sheet (different icons per cell — the proven grid pattern). ONE
        request per chunk generates `takes` sheets; cell k of every sheet
        is one take of icon k. Preview only — results are returned,
        nothing is written until /api/recraft-commit.
        """
        import base64 as _b64

        import iconpilot.recraft as rc

        token = rc.resolve_token()
        if not token and not data.get("debug"):
            raise ValueError("no Recraft token on the server — set RECRAFT_API_TOKEN")

        takes = max(1, min(int(data.get("takes") or 4), 6))
        try:
            max_grid = max(0, min(int(data.get("max_grid") or 0), 5))
        except (TypeError, ValueError):
            max_grid = 0
        chunk_size = (max_grid * max_grid) if max_grid >= 2 else 25
        with pack_lock(self.pack_dir):
            pack, styles = load_pack(self.pack_dir / "pack.json")

        by_style: dict[str, list[tuple[str, str]]] = {}
        for target in data.get("targets", []):
            iid, _, vid = str(target).partition("#")
            var = pack["icons"].get(iid, {}).get("variants", {}).get(vid)
            if var is None or "style" not in var:
                raise ValueError(f"no authored variant {iid}#{vid}")
            if var.get("status") == "approved":
                raise ValueError(f"{iid}#{vid} is approved/locked — unlock to redraft")
            by_style.setdefault(var["style"], []).append((iid, vid))

        cfg = pack.get("recraft", {})
        viewbox = pack["spec"]["viewBox"]
        model_override = data.get("model")
        items: list[dict] = []
        calls: list[dict] = []
        total_cost = 0.0
        for style_id, targets in by_style.items():
            style = styles[style_id]
            style_id_rc = cfg.get("style_ids", {}).get(style_id) or cfg.get("style_id")
            refs: list[str] = []
            if not style_id_rc:
                from iconpilot.styles import style_refs as _sr

                refs = [f.read_text() for f in _sr(self.pack_dir, style_id)[:3]]
            if not style_id_rc and refs and not data.get("debug"):
                # no cached style yet → create it now ($0.005, cached after)
                try:
                    style_id_rc = self._ensure_style_id(token or "", style_id, style, refs)
                except rc.RecraftError:
                    style_id_rc = None
            model = (
                model_override
                or cfg.get("model")
                or (rc.DEFAULT_MODEL if (style_id_rc or refs) else rc.FALLBACK_MODEL)
            )
            if model not in rc.VECTOR_MODELS:
                raise ValueError(f"model must be a vector model, got '{model}'")
            # Recraft generations endpoint only accepts raster refs
            ref_urls = None
            if refs and "v4" in model and not style_id_rc:
                pngs = []
                for svg_text in refs:
                    try:
                        pngs.append(rc.png_data_url(svg_text, 256))
                    except (ValueError, OSError):
                        pass
                ref_urls = pngs or None
            curated = (
                rc.CURATED_STYLE_MAP.get(style_id)
                if not style_id_rc and not ref_urls and "v4" not in model
                else None
            )
            for i0 in range(0, len(targets), chunk_size):
                chunk = targets[i0 : i0 + chunk_size]
                grid = rc.pack_grid(len(chunk), max_grid=max_grid or None)
                live_fb = pack.get("feedback") or []

                def _fb_for(feedback: list, iid: str, vid: str) -> list[str]:
                    out = []
                    for f in feedback:
                        s = f.get("scope")
                        hit = (
                            s == "pack"
                            or (s == "icon" and f.get("icon") == iid)
                            or (s == "variant" and f.get("icon") == iid and f.get("variant") == vid)
                        )
                        if hit:
                            out.append(str(f.get("text", "")))
                    return [x.strip() for x in out if x.strip()]

                briefs = []
                for iid, vid in chunk:
                    icon = pack["icons"][iid]
                    b = icon.get("brief") or icon.get("description") or ""
                    if icon.get("colors"):
                        b += ", colors " + " ".join(icon["colors"][:5])
                    elif icon.get("main_color") and not style_id_rc:
                        b += f", dominant color {icon['main_color']}"
                    fbs = _fb_for(live_fb, iid, vid)
                    if fbs:
                        b += ". Note: " + "; ".join(fbs)[:220]
                    briefs.append(b)
                prompt = rc.pack_sheet_prompt(briefs, style.label, grid, model=model)
                cost = round(
                    rc.price_per_image(model) * takes + (rc.STYLE_REF_PRICE if ref_urls else 0),
                    4,
                )
                request: dict = {
                    "model": model,
                    "prompt": prompt,
                    "size": "1:1",
                    "response_format": "b64_json",
                    "n": takes,
                }
                if style_id_rc:
                    request["style_id"] = style_id_rc
                elif curated:
                    request["style"] = curated
                elif ref_urls:
                    request["style_reference_urls"] = [f"<{len(ref_urls)} PNG refs>"]
                plimit = rc.prompt_limit(model)
                calls.append(
                    {
                        "style": style_id,
                        "grid": grid,
                        "takes": takes,
                        "max_grid": max_grid,
                        "model": model,
                        "cost": cost,
                        "prompt": prompt,
                        "prompt_chars": len(prompt),
                        "prompt_limit": plimit,
                        "prompt_fits": len(prompt) <= plimit,
                        "style_refs": len(refs),
                        "style_id": style_id_rc or "",
                        "curated": curated or "",
                        "endpoint": rc.API_BASE + "/images/generations/vector",
                        "request": request,
                    }
                )
                if data.get("debug"):
                    continue
                assert token is not None  # debug-only path skips generation
                try:
                    sheets = rc.generate(
                        token,
                        prompt,
                        n=takes,
                        style_id=style_id_rc,
                        model=model,
                        reference_urls=ref_urls,
                        curated_style=curated,
                    )
                except rc.RecraftError as exc:
                    msg = str(exc).lower()
                    bad_style = "not a vector style" in msg or (
                        "style" in msg
                        and any(s in msg for s in ("not found", "does not exist", "invalid"))
                    )
                    if style_id_rc and bad_style:
                        # poisoned cached style (wrong base, foreign account,
                        # remotely deleted) — heal + retry once
                        healed = self._heal_bad_style(token, style_id, style, refs)
                        if not healed or healed == style_id_rc:
                            raise  # nothing better to retry with
                        style_id_rc = healed
                        cost += rc.STYLE_CREATE_PRICE  # heal is a paid create
                        sheets = rc.generate(
                            token, prompt, n=takes, style_id=style_id_rc, model=model
                        )
                    else:
                        raise
                run_now = self._ensure_round()
                self._save_sheets(run_now, f"draft-{style_id}", grid, sheets, prompt)
                split_sheets = [rc.split_sheet(s, grid, target=24.0) for s in sheets]
                for k, (iid, vid) in enumerate(chunk):
                    results = []
                    for ti, cells in enumerate(split_sheets):
                        if k >= len(cells):
                            continue
                        svg = rc.normalize(
                            rc.strip_metadata(cells[k]), viewbox, mono=style.color_mode == "mono"
                        )
                        b64 = _b64.b64encode(svg.encode()).decode()
                        results.append(
                            {
                                "id": ti,
                                "svg_data": f"data:image/svg+xml;base64,{b64}",
                                "gate_pass": run_gate_svg(svg, pack, styles, iid, vid),
                            }
                        )
                    items.append({"icon": iid, "variant": vid, "results": results})
                total_cost += cost

        out: dict = {
            "takes": takes,
            "max_grid": max_grid,
            "cost_usd": round(sum(c["cost"] for c in calls) or total_cost, 4),
            "calls": [
                {
                    "style": c["style"],
                    "grid": c["grid"],
                    "takes": c["takes"],
                    "model": c["model"],
                    "cost": c["cost"],
                    "prompt": c["prompt"],
                    "prompt_chars": c["prompt_chars"],
                    "prompt_limit": c["prompt_limit"],
                    "prompt_fits": c["prompt_fits"],
                    "style_refs": c["style_refs"],
                    "style_id": c["style_id"],
                    "curated": c["curated"],
                    "endpoint": c["endpoint"],
                    "request": c["request"],
                }
                for c in calls
            ],
        }
        if not data.get("debug"):
            out["items"] = items
        return out

    def _feedback_write(self, op: str, data: dict) -> dict:
        """add / resolve / promote feedback items (lock + atomic)."""
        import uuid

        with pack_lock(self.pack_dir):
            pack, _ = load_pack(self.pack_dir / "pack.json")
            items = pack.setdefault("feedback", [])
            runs_dir = self.pack_dir / ".runs"
            runs = sorted(p.name for p in runs_dir.glob("r*")) if runs_dir.is_dir() else []
            cur_round = runs[-1] if runs else "pre"

            if op == "add":
                text = str(data.get("text") or "").strip()
                if not text:
                    raise ValueError("text required")
                scope = data.get("scope") or "pack"
                if scope not in ("pack", "icon", "variant"):
                    raise ValueError("scope must be pack|icon|variant")
                author = data.get("author") or "user"
                if author not in ("user", "agent"):
                    raise ValueError("author must be user|agent")
                item = {
                    "id": uuid.uuid4().hex[:8],
                    "scope": scope,
                    "text": text[:500],
                    "author": author,
                    "round": cur_round,
                    "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                if scope in ("icon", "variant"):
                    icon_id = data.get("icon")
                    if icon_id not in pack.get("icons", {}):
                        raise ValueError(f"unknown icon '{icon_id}'")
                    item["icon"] = icon_id
                if scope == "variant":
                    vid = data.get("variant")
                    if vid not in pack["icons"][icon_id].get("variants", {}):
                        raise ValueError(f"unknown variant '{vid}'")
                    item["variant"] = vid
                items.append(item)
                write_pack_atomic(self.pack_dir, pack)
                return {"item": item, "count": len(items)}

            if op == "revive":
                # bring an archived comment back to the live list: reads
                # .runs/<round>/feedback.json, appends a fresh live copy
                import json as _json

                src_round = str(data.get("round") or "")
                fid = str(data.get("id") or "")
                fb_file = runs_dir / src_round / "feedback.json"
                if not src_round or not fb_file.is_file():
                    raise ValueError(f"no archived feedback for round '{src_round}'")
                try:
                    archived = _json.loads(fb_file.read_text())
                except (ValueError, OSError) as exc:
                    raise ValueError(f"cannot read archived feedback: {exc}") from exc
                src = next((i for i in archived if i.get("id") == fid), None)
                if src is None:
                    raise ValueError(f"no archived feedback item '{fid}' in {src_round}")
                scope = src.get("scope") or "pack"
                icon_id = src.get("icon")
                if scope in ("icon", "variant"):
                    if icon_id not in pack.get("icons", {}):
                        raise ValueError(f"icon '{icon_id}' no longer in the pack")
                    item = {
                        "id": uuid.uuid4().hex[:8],
                        "scope": scope,
                        "icon": icon_id,
                        "text": str(src.get("text", ""))[:500],
                        "author": src.get("author") or "user",
                        "round": cur_round,
                        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "revived_from": f"{src_round}/{fid}",
                    }
                    if scope == "variant":
                        vid = src.get("variant")
                        if vid not in pack["icons"][icon_id].get("variants", {}):
                            raise ValueError(f"variant '{icon_id}#{vid}' no longer in the pack")
                        item["variant"] = vid
                else:
                    item = {
                        "id": uuid.uuid4().hex[:8],
                        "scope": "pack",
                        "text": str(src.get("text", ""))[:500],
                        "author": src.get("author") or "user",
                        "round": cur_round,
                        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "revived_from": f"{src_round}/{fid}",
                    }
                items.append(item)
                write_pack_atomic(self.pack_dir, pack)
                return {"item": item, "count": len(items)}

            fid = data.get("id") or ""
            item = next((i for i in items if i["id"] == fid), None)
            if item is None:
                raise ValueError(f"no feedback item '{fid}'")

            if op == "resolve":
                items.remove(item)
                write_pack_atomic(self.pack_dir, pack)
                return {"resolved": fid, "count": len(items)}

            # promote: fold into standing pack surfaces, drop from live list
            target = data.get("to") or "note"
            if item.get("scope") == "pack":
                label = ""
            elif item.get("scope") == "variant":
                label = f"{item.get('icon', '')}#{item.get('variant')}: "
            else:
                label = f"{item.get('icon', '')}: "
            if target == "rules":
                pack.setdefault("rules", []).append(f"{label}{item['text']}".strip())
            else:
                prefix = label.strip()
                standing = str(pack.get("note") or "")
                sep = " · " if standing else ""
                pack["note"] = f"{standing}{sep}{prefix}{item['text']}".strip()
            items.remove(item)
            write_pack_atomic(self.pack_dir, pack)
            return {"promoted": fid, "to": target, "count": len(items)}

    def do_POST(self) -> None:
        url = urlparse(self.path)
        if url.path == "/api/recraft-style-create":
            data = self._body()
            import iconpilot.recraft as _rcc

            try:
                self._json(200, self._recraft_style_create(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except _rcc.RecraftError as exc:
                self._json(502, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/recraft-style-save":
            data = self._body()
            try:
                self._json(200, self._recraft_style_save(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/adopt":
            data = self._body()
            try:
                self._json(200, self._adopt_preview(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/adopt-commit":
            data = self._body()
            try:
                self._json(200, self._adopt_commit(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/recraft-refine":
            data = self._body()
            try:
                self._json(200, self._recraft_refine(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                import iconpilot.recraft as _rcr

                self._json(502 if isinstance(exc, _rcr.RecraftError) else 500, {"error": str(exc)})
            return
        if url.path == "/api/recraft-batch":
            data = self._body()
            try:
                self._json(200, self._recraft_batch(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                import iconpilot.recraft as _rc0

                self._json(502 if isinstance(exc, _rc0.RecraftError) else 500, {"error": str(exc)})
            return
        if url.path == "/api/feedback":
            data = self._body()
            try:
                self._json(200, self._feedback_write("add", data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/feedback/resolve":
            data = self._body()
            try:
                self._json(200, self._feedback_write("resolve", data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/feedback/revive":
            data = self._body()
            try:
                self._json(200, self._feedback_write("revive", data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/feedback/promote":
            data = self._body()
            try:
                self._json(200, self._feedback_write("promote", data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/round/new":
            data = self._body()
            try:
                out = self._start_round(only=data.get("only"))
                # auto-prune old clutter once a new round opens
                try:
                    with pack_lock(self.pack_dir):
                        pack, _ = load_pack(self.pack_dir / "pack.json")
                    out["pruned"] = prune_runs(self.pack_dir, pack, keep_latest=2)
                except OSError:
                    out["pruned"] = []
                self._json(200, out)
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/style-ref-upload":
            data = self._body()
            try:
                sid = str(data.get("style") or "")
                name = str(data.get("name") or "").strip()
                svg = str(data.get("svg") or "")
                if not sid or not svg.startswith("<svg") or not name:
                    raise ValueError("need style, name and svg text")
                name = (
                    "".join(c for c in name.replace(".svg", "") if c.isalnum() or c in "-_")
                    or "ref"
                )
                d = self.pack_dir / ".style-refs" / sid
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{name}.svg").write_text(svg)
                self._json(200, {"added": f"{name}.svg", "style": sid})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/style-ref-remove":
            data = self._body()
            try:
                sid = str(data.get("style") or "")
                name = str(data.get("name") or "")
                f = self.pack_dir / ".style-refs" / sid / f"{name}.svg"
                if "/" in sid or "/" in name or ".." in name or not f.is_file():
                    raise ValueError("no such own reference")
                f.unlink()
                self._json(200, {"removed": name})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/pack-style-remove":
            data = self._body()
            try:
                sid = str(data.get("id") or "")
                with pack_lock(self.pack_dir):
                    pack, _ = load_pack(self.pack_dir / "pack.json")
                    removed = 0
                    for iid, icon in pack["icons"].items():
                        for vid in [
                            k
                            for k, vd in icon.get("variants", {}).items()
                            if k == sid or vd.get("style") == sid
                        ]:
                            if icon["variants"][vid].get("status") == "approved":
                                raise ValueError(f"{iid}#{vid} is approved — unlock first")
                            del icon["variants"][vid]
                            removed += 1
                    pack.get("styles", {}).pop(sid, None)
                    (pack.get("recraft", {}).get("style_ids", {}) or {}).pop(sid, None)
                    _, errors = revalidate(pack)
                    if errors:
                        raise ValueError("; ".join(errors[:3]))
                    write_pack_atomic(self.pack_dir, pack)
                self._json(200, {"removed_variants": removed, "style": sid})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/pack-style":
            data = self._body()
            try:
                sid = str(data.get("id") or "").strip()
                sdef = data.get("def") or {}
                if not sid or not sid.replace("-", "").replace("_", "").isalnum():
                    raise ValueError("style id required (letters/digits/-/_)")
                with pack_lock(self.pack_dir):
                    pack, styles = load_pack(self.pack_dir / "pack.json")
                    existing = pack.setdefault("styles", {}).get(sid)
                    if existing and "extends" in existing and "extends" not in sdef:
                        sdef = {**sdef, "extends": existing["extends"]}
                    elif not existing and sid in styles:
                        sdef = {**sdef, "extends": sid}  # lineage to the registry style
                    if existing:
                        # account-style extras are managed by the Recraft
                        # seeder, not the edit dialog — keep them across edits
                        keep = {
                            k: v
                            for k, v in existing.items()
                            if k in ("recraft_style_id", "recraft_style_hash") and k not in sdef
                        }
                        if keep:
                            sdef = {**keep, **sdef}
                    pack["styles"][sid] = sdef
                    _, errors = revalidate(pack)
                    if errors:
                        raise ValueError("; ".join(errors[:3]))
                    write_pack_atomic(self.pack_dir, pack)
                self._json(200, {"rev": pack.get("rev", 0), "style": sid})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/pack-variant-bulk":
            data = self._body()
            try:
                style_id = str(data.get("style") or "").strip()
                with pack_lock(self.pack_dir):
                    pack, styles = load_pack(self.pack_dir / "pack.json")
                    if style_id not in styles:
                        raise ValueError(f"unknown style '{style_id}'")
                    added = 0
                    for icon in pack["icons"].values():
                        has = any(
                            v.get("style") == style_id for v in icon.get("variants", {}).values()
                        )
                        if has or style_id in icon.get("variants", {}):
                            continue
                        icon["variants"][style_id] = {"style": style_id, "status": "todo"}
                        added += 1
                    _, errors = revalidate(pack)
                    if errors:
                        raise ValueError("; ".join(errors[:3]))
                    write_pack_atomic(self.pack_dir, pack)
                self._json(200, {"rev": pack.get("rev", 0), "added": added})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/recraft-preview":
            data = self._body()
            try:
                self._json(200, self._recraft_preview(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                import iconpilot.recraft as _rc0

                self._json(502 if isinstance(exc, _rc0.RecraftError) else 500, {"error": str(exc)})
            return
        if url.path == "/api/recraft-commit":
            data = self._body()
            try:
                self._json(200, self._recraft_commit(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if url.path == "/api/recraft":
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host", ""):
                self._json(403, {"error": "cross-origin POST rejected"})
                return
            data = self._body()
            try:
                self._json(200, self._recraft_draft(data))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                import iconpilot.recraft as _rc

                self._json(502 if isinstance(exc, _rc.RecraftError) else 500, {"error": str(exc)})
            return
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
                runs = sorted(p.name for p in (self.pack_dir / ".runs").glob("r*") if p.is_dir())
                if round_id is None:
                    if not runs:
                        raise ValueError("no rounds under .runs/")
                    round_id = runs[-1]
                elif round_id != runs[-1]:
                    raise ValueError(
                        f"round {round_id} is history — only the latest ({runs[-1]}) is live"
                    )
                # backup before apply (for undo) — atomic via tmp+rename
                import shutil

                tmp_bk = self.pack_dir / ".pack-backup.tmp"
                shutil.copyfile(self.pack_dir / "pack.json", tmp_bk)
                tmp_bk.rename(self.pack_dir / ".pack-backup.json")
                log = apply_decisions(
                    self.pack_dir,
                    pack,
                    styles,
                    decisions,
                    round_id,
                    source="server",
                    instructions=(data.get("instructions") or None),
                )
            # auto-prune: empty rounds + orphan candidate dirs
            try:
                log += prune_runs(self.pack_dir, pack)
            except OSError:
                pass
            self._json(200, {"rev": pack.get("rev", 0), "log": log})
        except (ValueError, KeyError) as exc:
            self._json(400, {"error": str(exc)})
        except TimeoutError as exc:
            self._json(423, {"error": str(exc)})
        except Exception as exc:  # invalid pack after load etc.
            self._json(500, {"error": str(exc)})

    def do_PUT(self) -> None:
        url = urlparse(self.path)
        if url.path == "/api/pack":
            data = self._body()
            try:
                with pack_lock(self.pack_dir):
                    pack, _styles = load_pack(self.pack_dir / "pack.json")
                    if "version" in data:
                        pack["version"] = data["version"]
                    if isinstance(data.get("note"), str):
                        pack["note"] = data["note"]
                    if isinstance(data.get("description"), str):
                        pack["description"] = data["description"]
                    rc_in = data.get("recraft") or {}
                    if isinstance(rc_in, dict) and ("model" in rc_in or "n" in rc_in):
                        import iconpilot.recraft as _rc4

                        cfg = pack.setdefault("recraft", {})
                        if "model" in rc_in:
                            if rc_in["model"] not in _rc4.VECTOR_MODELS:
                                raise ValueError("recraft model must be a vector model")
                            cfg["model"] = rc_in["model"]
                        if "n" in rc_in:
                            n_val = int(rc_in["n"])
                            if not 1 <= n_val <= 6:
                                raise ValueError("recraft n must be 1-6")
                            cfg["n"] = n_val
                    if "rules" in data and isinstance(data["rules"], list):
                        pack["rules"] = [str(r) for r in data["rules"] if str(r).strip()]
                    spec_in = data.get("spec") or {}
                    spec = pack.setdefault("spec", {})
                    for k in ("stroke", "live_area"):
                        if isinstance(spec_in.get(k), dict):
                            spec.setdefault(k, {}).update(
                                {kk: vv for kk, vv in spec_in[k].items() if vv is not None}
                            )
                    for k in ("precision",):
                        if spec_in.get(k) is not None:
                            spec[k] = spec_in[k]
                    if isinstance(data.get("styles"), dict):
                        pack["styles"] = data["styles"]
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
            return

        if url.path == "/api/variant":
            data = self._body()
            icon_id = data.get("icon")
            variant_id = data.get("variant")
            style_id = data.get("style")
            note = data.get("note")
            pinned = data.get("pinned")
            postponed = data.get("postponed")
            reopen = bool(data.get("reopen"))
            if not (
                icon_id
                and variant_id
                and (
                    style_id
                    or note is not None
                    or pinned is not None
                    or postponed is not None
                    or reopen
                )
            ):
                self._json(400, {"error": "need icon, variant, style"})
                return
            try:
                with pack_lock(self.pack_dir):
                    pack, styles = load_pack(self.pack_dir / "pack.json")
                    v = pack["icons"].get(icon_id, {}).get("variants", {}).get(variant_id)
                    if v is None or "link" in v:
                        self._json(404, {"error": f"no authored variant {icon_id}#{variant_id}"})
                        return
                    if reopen and v.get("status") == "approved":
                        v["status"] = "todo"  # chosen stays as historical record
                    if style_id and style_id not in styles:
                        self._json(400, {"errors": [f"unknown style '{style_id}'"]})
                        return
                    if style_id:
                        v["style"] = style_id
                    if note is not None:
                        v["note"] = note
                    if pinned is not None:
                        v["pinned"] = pinned
                    if postponed is not None:
                        if postponed:
                            v["postponed"] = True
                        else:
                            v.pop("postponed", None)
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
            return

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
