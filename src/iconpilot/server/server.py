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
    revalidate,
    write_pack_atomic,
)
from iconpilot.render.contact import contact_sheet
from iconpilot.render.render import render_png_text

EDITABLE_FIELDS = ("brief", "prompt", "main_color", "note", "description")


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
            if active:
                for svg in sorted((self.pack_dir / ".runs" / active).rglob("*.svg")):
                    rel = svg.relative_to(self.pack_dir / ".runs" / active).parts
                    if len(rel) == 3:
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
            out = {}
            for sid in sorted(set(all_styles) | used):
                files = style_refs(self.pack_dir, sid)
                if not files:
                    continue
                own = any(str(f).startswith(str(self.pack_dir)) for f in files)
                out[sid] = {
                    "source": "own" if own else "bundled",
                    "icons": [{"name": f.stem} for f in files],
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
        if url.path == "/api/recraft-models":
            import iconpilot.recraft as _rc

            self._json(200, dict(_rc.MODEL_PRICES))
            return
        if url.path == "/api/recraft-request":
            icon_id = (q.get("icon") or [""])[0]
            variant = (q.get("variant") or [""])[0]
            try:
                n = max(1, min(int((q.get("n") or ["4"])[0]), 6))
            except ValueError:
                n = 4
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
            req = {
                "model": plan["model"],
                "prompt": plan["prompt"],
                "n": plan["n"],
                "size": "1:1",
                "response_format": "b64_json",
            }
            if plan["style_id"]:
                req["style_id"] = plan["style_id"]
                req["style_match"] = "precise"
            elif plan["refs"]:
                req["style_reference_urls"] = [rc._svg_data_url(s)[:60] + "…" for s in plan["refs"]]
            self._json(
                200,
                {
                    "endpoint": rc.API_BASE + "/images/generations",
                    "request": req,
                    "style_refs_attached": len(plan["refs"]),
                    "full_prompt": build_prompt(
                        self.pack_dir, plan["pack"], plan["styles"], icon_id, variant, n=plan["n"]
                    ),
                    "est_cost_usd": plan["cost"],
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
        n = max(1, min(int(n), 6))

        prompt = rc.draft_prompt(icon, style, pack)
        style_id = cfg.get("style_ids", {}).get(v["style"]) or cfg.get("style_id")

        refs: list[str] = []
        if not style_id:
            # attach the look: pinned/approved SVGs on the same style first,
            # then the approved sibling of this icon (max 3)
            for iid, ic in pack["icons"].items():
                for vid, vd in ic.get("variants", {}).items():
                    if len(refs) >= 3:
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

        model = cfg.get("model") or (rc.DEFAULT_MODEL if (style_id or refs) else rc.FALLBACK_MODEL)
        if model not in rc.VECTOR_MODELS:
            raise ValueError(f"model must be a vector model, got '{model}'")

        cost = rc.price_per_image(model) * n + (rc.STYLE_REF_PRICE if refs else 0)
        return {
            "prompt": prompt,
            "style_id": style_id,
            "refs": refs,
            "model": model,
            "n": n,
            "cost": round(cost, 4),
            "pack": pack,
            "styles": styles,
            "style": style,
        }

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
        if n is not None and not 1 <= n <= 6:
            raise ValueError("n must be 1-6")
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
        style = plan["style"]
        style_id = plan["style_id"]

        ref_urls = [rc._svg_data_url(s) for s in plan["refs"]] or None
        sheet = int(data.get("sheet") or 0)
        if sheet:
            grid = max(2, min(sheet, 4))
            sheet_svgs = rc.generate(
                token,
                rc.sheet_prompt(plan["prompt"], grid),
                n=1,
                style_id=style_id,
                model=plan["model"],
                reference_urls=ref_urls,
            )
            svgs = rc.split_sheet(sheet_svgs[0], grid, target=24.0)
        else:
            svgs = rc.generate(
                token,
                plan["prompt"],
                n=plan["n"],
                style_id=style_id,
                model=plan["model"],
                reference_urls=ref_urls,
            )
        n = plan["n"]

        runs_dir = self.pack_dir / ".runs"
        runs = sorted(p.name for p in runs_dir.glob("r*")) if runs_dir.is_dir() else []
        run = runs[-1] if runs else None
        if not run:
            raise ValueError("no round yet — POST /api/round/new first")
        # count + write + cost record under the pack lock: closes the concurrent
        # draft race (two tabs double-firing the same icon/variant).
        import json as _json

        viewbox = pack["spec"]["viewBox"]
        normalized = [rc.normalize(raw, viewbox) for raw in svgs]
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
                if run_gate(f, pack, style).passed:
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
                rc.price_per_image(style_id and rc.DEFAULT_MODEL or rc.FALLBACK_MODEL) * len(wrote),
                2,
            ),
            "model": style_id and rc.DEFAULT_MODEL or rc.FALLBACK_MODEL,
        }

    def _recraft_batch(self, data: dict) -> dict:
        """Smart Recraft seeding: fewest calls, one per style, icons packed.

        Body: {targets: ["icon#variant", ...], vpi: 2, model?: "..."}
        Cells map row-major: icon k of a call gets cells k*vpi+1..(k+1)*vpi.
        """
        import iconpilot.recraft as rc
        from iconpilot.gate.run import run_gate

        token = rc.resolve_token()
        if not token:
            raise ValueError("no Recraft token on the server — set RECRAFT_API_TOKEN")

        vpi = max(1, min(int(data.get("vpi") or 2), 6))
        with pack_lock(self.pack_dir):
            pack, styles = load_pack(self.pack_dir / "pack.json")

        # group targets by style, preserving order; per-icon prompts
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
        model_override = data.get("model")
        calls = []
        for style_id, targets in by_style.items():
            style = styles[style_id]
            style_id_rc = cfg.get("style_ids", {}).get(style_id) or cfg.get("style_id")
            refs: list[str] = []
            if not style_id_rc:
                from iconpilot.styles import style_refs as _sr

                refs = [f.read_text() for f in _sr(self.pack_dir, style_id)[:3]]
            model = (
                model_override
                or cfg.get("model")
                or (rc.DEFAULT_MODEL if (style_id_rc or refs) else rc.FALLBACK_MODEL)
            )
            if model not in rc.VECTOR_MODELS:
                raise ValueError(f"model must be a vector model, got '{model}'")
            icon_prompts = []
            for iid, vid in targets:
                icon = pack["icons"][iid]
                icon_prompts.append(
                    rc.draft_prompt(icon, styles[icon["variants"][vid]["style"]], pack)
                )
            for plan in rc.plan_batch({style_id: icon_prompts}, vpi):
                plan.update(
                    model=model,
                    style_id=style_id_rc,
                    refs=refs,
                    targets=targets,
                    prompt=rc.batch_prompt(plan["icons"], plan["vpi"], style.label, plan["grid"]),
                    cost=round(
                        rc.price_per_image(model)
                        + (rc.STYLE_REF_PRICE if refs and not style_id_rc else 0),
                        4,
                    ),
                )
                calls.append(plan)

        # debug mode: return the planned requests without calling
        if data.get("debug"):
            return {
                "calls": [
                    {
                        "style": c["style"],
                        "grid": c["grid"],
                        "vpi": c["vpi"],
                        "model": c["model"],
                        "cost": c["cost"],
                        "prompt": c["prompt"][:300] + "…",
                        "style_refs": len(c["refs"]),
                    }
                    for c in calls
                ],
                "est_total_usd": round(sum(c["cost"] for c in calls), 4),
            }

        runs_dir = self.pack_dir / ".runs"
        runs = sorted(p.name for p in runs_dir.glob("r*")) if runs_dir.is_dir() else []
        run = runs[-1] if runs else None
        if not run:
            raise ValueError("no round yet — start a pass first")

        results = []
        total_cost = 0.0
        with pack_lock(self.pack_dir):
            for c in calls:
                sheet = rc.generate(
                    token,
                    c["prompt"],
                    n=1,
                    style_id=c["style_id"],
                    model=c["model"],
                    reference_urls=[rc._svg_data_url(s) for s in c["refs"]] or None,
                )
                cells = rc.split_sheet(sheet[0], c["grid"], target=24.0)
                # row-major assignment: icon k -> cells k*vpi .. k*vpi+vpi-1
                viewbox = pack["spec"]["viewBox"]
                for k, (iid, vid) in enumerate(c["targets"]):
                    got, passed = [], 0
                    cell_svgs = cells[k * c["vpi"] : (k + 1) * c["vpi"]]
                    # len may fall short if the model dropped cells
                    cand_dir = runs_dir / run / vid / iid
                    cand_dir.mkdir(parents=True, exist_ok=True)
                    existing = len(list(cand_dir.glob("r*.svg")))
                    for j, cell in enumerate(cell_svgs):
                        f = cand_dir / f"r{existing + j + 1}.svg"
                        f.write_text(rc.normalize(cell, viewbox))
                        got.append(f.name)
                        if run_gate(
                            f, pack, styles[pack["icons"][iid]["variants"][vid]["style"]]
                        ).passed:
                            passed += 1
                    results.append(
                        {"icon": iid, "variant": vid, "seeds": got, "gate_passed": passed}
                    )
                total_cost += c["cost"]
            # cost bookkeeping
            import json as _json

            round_json = runs_dir / run / "round.json"
            try:
                rj = _json.loads(round_json.read_text()) if round_json.is_file() else {}
            except ValueError:
                rj = {}
            rj.setdefault("models_used", {})["seeder"] = calls[0]["model"] if calls else "-"
            rj["estimated_cost_usd"] = round(rj.get("estimated_cost_usd", 0) + total_cost, 4)
            seeds_total = 0
            for x in results:
                sv = x.get("seeds")
                if isinstance(sv, list):
                    seeds_total += len(sv)
            rj["candidates_generated"] = rj.get("candidates_generated", 0) + seeds_total
            round_json.write_text(_json.dumps(rj, indent=2) + "\n")

        return {
            "round": run,
            "calls": len(calls),
            "results": results,
            "cost_usd": round(total_cost, 4),
        }

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
                self._json(200, self._start_round(only=data.get("only")))
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
                    pack, _ = load_pack(self.pack_dir / "pack.json")
                    pack.setdefault("styles", {})[sid] = sdef
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
