"""iconpilot CLI."""

from __future__ import annotations

import json
import re
from pathlib import Path

import typer

from iconpilot import __version__
from iconpilot.context import build_context, render_markdown
from iconpilot.decide import apply_decisions, parse_decision_text
from iconpilot.export.export import (
    TARGETS,
    collect_exportables,
    export_iconify,
    export_maplibre,
    export_sprite_svg,
    export_svg,
)
from iconpilot.gate.run import run_gate
from iconpilot.pack import (
    PackError,
    advance_feedback,
    load_pack,
    next_run_id,
    revalidate,
    write_pack_atomic,
)
from iconpilot.packs import summarize
from iconpilot.render.contact import contact_sheet
from iconpilot.render.render import hamming, hash_file
from iconpilot.server.server import pack_lock
from iconpilot.server.server import serve as serve_review
from iconpilot.styles import resolve_styles, snapshot_style, user_styles_path

app = typer.Typer(
    name="iconpilot",
    help="Design consistent SVG icon packs with deterministic gates and human rounds.",
    no_args_is_help=True,
)


def _not_implemented(command: str) -> None:
    typer.secho(
        f"`iconpilot {command}` is not implemented yet.",
        fg=typer.colors.YELLOW,
        err=True,
    )
    raise typer.Exit(code=1)


def _version_cb(value: bool | None) -> None:
    if value:
        typer.echo(f"iconpilot {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool | None = typer.Option(
        None, "--version", help="Show version.", callback=_version_cb, is_eager=True
    ),
) -> None:
    """Design consistent SVG icon packs with deterministic gates and human rounds."""


DEFAULT_SPEC = {
    "viewBox": "0 0 24 24",
    "live_area": {"padding": 2},
    "stroke": {"width": 2, "linecap": "round", "linejoin": "round"},
    "fill": "none",
    "allowed_elements": [
        "path",
        "circle",
        "rect",
        "line",
        "polyline",
        "polygon",
        "ellipse",
    ],
    "precision": 0.5,
}


@app.command()
def new(
    pack_dir: str,
    name: str = typer.Option(None, "--name", help="Pack name (default: directory name)."),
    author: str = typer.Option(
        "user", "--author", help="user | designer (designer packs are todo-only)."
    ),
) -> None:
    """Scaffold a pack: spec + empty registry. Fill briefs, then `check`."""
    d = Path(pack_dir)
    pack_name = name or d.name
    if author not in ("user", "designer"):
        typer.secho("--author must be 'user' or 'designer'", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    if not re.match(r"^[a-z][a-z0-9-]*$", pack_name):
        typer.secho(
            f"invalid pack name '{pack_name}' (lowercase kebab-case)", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=2)
    if (d / "pack.json").exists():
        typer.secho(
            f"{d / 'pack.json'} already exists — refusing to overwrite",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)
    d.mkdir(parents=True, exist_ok=True)
    (d / "icons").mkdir(exist_ok=True)
    pack = {
        "schema": 2,
        "name": pack_name,
        "version": "0.1.0",
        "provenance": {"created_by": author},
        "spec": DEFAULT_SPEC,
        "styles": {},
        "icons": {},
    }
    (d / "pack.json").write_text(json.dumps(pack, indent=2) + "\n")
    typer.secho(
        f"created {d / 'pack.json'}\n"
        f"next: iconpilot add {d} <icon> --brief … [--variant mono:mono-line]\n"
        f"then: iconpilot check {d}",
        fg=typer.colors.GREEN,
    )


@app.command()
def add(
    pack: str,
    icon: str,
    brief: str = typer.Option(..., "--brief"),
    variant: list[str] = typer.Option(
        None, "--variant", help="<name>:<style-id>, repeatable. Default: mono:mono-line."
    ),
) -> None:
    """Add an icon with authored variants (status todo)."""
    import re as _re

    pack_dir = resolve_pack_dir(pack)
    try:
        with pack_lock(pack_dir):
            pack_data, styles = _load_pack_arg(pack)
            for spec_v in variant or ["mono:mono-line"]:
                try:
                    snapshot_style(pack_data, spec_v.split(":", 1)[1])
                except ValueError as exc:
                    typer.secho(str(exc), fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=2) from exc
            if icon in pack_data["icons"]:
                typer.secho(f"icon '{icon}' already exists", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=2)
            if not _re.match(r"^[a-z][a-z0-9-]*$", icon):
                typer.secho(
                    f"invalid icon name '{icon}' (lowercase kebab-case)",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=2)
            specs = variant or ["mono:mono-line"]
            variants: dict = {}
            for spec in specs:
                vname, _, style_id = spec.partition(":")
                if not style_id or style_id not in styles:
                    typer.secho(
                        f"unknown style '{style_id}' in '{spec}' — see iconpilot styles",
                        fg=typer.colors.RED,
                        err=True,
                    )
                    raise typer.Exit(code=2)
                variants[vname] = {"style": style_id, "status": "todo"}
            pack_data["icons"][icon] = {"brief": brief, "variants": variants}
            _, errors = revalidate(pack_data)
            if errors:
                typer.secho(
                    "rejected:\n  - " + "\n  - ".join(errors), fg=typer.colors.RED, err=True
                )
                raise typer.Exit(code=2)
            write_pack_atomic(pack_dir, pack_data)
    except TimeoutError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.secho(f"added {icon} ({', '.join(variants)})", fg=typer.colors.GREEN)


@app.command()
def wait(
    pack: str,
    timeout: float = typer.Option(3600, "--timeout", help="Seconds to wait before giving up."),
    interval: float = typer.Option(2, "--interval", help="Poll interval in seconds."),
) -> None:
    """Block until the user applies decisions (pack rev changes), then exit.

    The agent loop's handoff point: serve the review page, run this, continue
    automatically when it returns (exit 0 = decisions applied, exit 124 = timeout).
    """
    from iconpilot.watch import wait_for_change

    pack_dir = resolve_pack_dir(pack)
    result = wait_for_change(pack_dir, timeout=timeout, interval=interval)
    if not result["changed"]:
        typer.secho(
            f"timeout after {timeout:.0f}s (rev {result['rev']} unchanged)",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=124)
    typer.secho(f"pack changed → rev {result['rev']}", fg=typer.colors.GREEN)
    if result["summary"]:
        typer.echo(f"  {result['summary']}")


def open_variants(pack_data: dict) -> list[tuple[str, str, str]]:
    """Open work: (icon, variant, style) for variants not yet approved (links skipped)."""
    out = []
    for iid, icon in pack_data["icons"].items():
        for vid, v in icon.get("variants", {}).items():
            if "link" in v or "style" not in v:
                continue
            if v.get("postponed"):
                continue  # excluded until explicitly focused or un-postponed
            if v.get("status") != "approved":
                out.append((iid, vid, v["style"]))
    return out


@app.command(name="next")
def next_round(
    pack: str,
    only: str = typer.Option(
        None, "--only", help="Focus mode: comma list of icon#variant keys to draft."
    ),
) -> None:
    """Start the next round: fresh run dir, printed open work, history untouched.

    Tooling defines what is open: approved/locked variants are excluded, and
    previous comments/decisions stay in their .runs/<round>/ dirs (history).
    The LLM drafts only what this command lists.
    """
    try:
        pack_data, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    pack_dir = resolve_pack_dir(pack)
    runs_dir = pack_dir / ".runs"
    runs = sorted(p.name for p in runs_dir.glob("r*")) if runs_dir.is_dir() else []

    # warn on unapplied decisions in the previous round
    if runs and not (runs_dir / runs[-1] / "decisions.json").is_file():
        typer.secho(
            f"warning: {runs[-1]} has no decisions.json — previous round was never applied",
            fg=typer.colors.YELLOW,
            err=True,
        )

    run = next_run_id(runs_dir)
    (runs_dir / run).mkdir(parents=True, exist_ok=True)
    with pack_lock(pack_dir):
        pack_data, _styles = _load_pack_arg(pack)  # re-load under the lock (no TOCTOU)
        carried = advance_feedback(pack_data, runs_dir / run)
        write_pack_atomic(pack_dir, pack_data)
    open_ = open_variants(pack_data)
    open_keys = [f"{i}#{v}" for i, v, _ in open_]
    if only is not None:
        wanted = {k.strip() for k in only.split(",") if k.strip()}
        all_variants = {
            f"{iid}#{vid}"
            for iid, icon in pack_data["icons"].items()
            for vid, var in icon.get("variants", {}).items()
            if "style" in var and "link" not in var and var.get("status") != "approved"
        }
        unknown = wanted - all_variants
        if unknown:
            typer.secho(f"not open (or locked): {sorted(unknown)}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
        open_ = [
            (iid, vid, var["style"])
            for iid, icon in pack_data["icons"].items()
            for vid, var in icon.get("variants", {}).items()
            if f"{iid}#{vid}" in wanted
            and "style" in var
            and "link" not in var
            and var.get("status") != "approved"
        ]
        open_keys = [f"{i}#{v}" for i, v, _ in open_]
    (runs_dir / run / "round.json").write_text(
        json.dumps(
            {
                "round": run,
                "open": open_keys,
                "locked_count": sum(
                    1
                    for icon in pack_data["icons"].values()
                    for v in icon.get("variants", {}).values()
                    if "style" in v and v.get("status") == "approved"
                ),
            },
            indent=2,
        )
        + "\n"
    )

    typer.secho(
        f"── round {run} started (history: {len(runs)} round(s) kept)", fg=typer.colors.GREEN
    )
    if carried:
        typer.secho(f"  feedback carried into {run}: {len(carried)} item(s)", fg=typer.colors.CYAN)
        for i in carried:
            where = (
                f"{i.get('icon', '')}#{i.get('variant', '')}"
                if i.get("scope") != "pack"
                else "pack"
            )
            typer.echo(f"    [{i['author']}] {where}: {i['text'][:70]}")
    typer.secho(f"OPEN WORK ({len(open_)}):", fg=typer.colors.GREEN)
    for iid, vid, style in open_:
        typer.echo(f"  {iid}#{vid} ({style})")
    if not open_:
        typer.secho("  nothing open — all variants approved 🎉", fg=typer.colors.GREEN)
    typer.secho(
        "locked variants are excluded; draft exactly what is listed above",
        fg=typer.colors.CYAN,
    )


@app.command()
def feedback(
    pack: str,
    add: str = typer.Option(None, "--add", help="Feedback text to add."),
    icon: str = typer.Option(None, "--icon", help="Scope: icon id."),
    variant: str = typer.Option(None, "--variant", help="Scope: variant id (needs --icon)."),
    author: str = typer.Option("agent", help="user or agent."),
    resolve: str = typer.Option(None, "--resolve", help="Resolve (remove) item by id."),
    promote: str = typer.Option(None, "--promote", help="Promote item by id into the pack."),
    to: str = typer.Option("note", "--to", help="promote target: note (standing) or rules."),
) -> None:
    """Per-round feedback: add / resolve / promote / list (default: list).

    Feedback guides exactly the next draft, then dies with its round (history
    keeps it). If an item is generally relevant, PROMOTE it — the text moves
    into the pack's standing note (or rules) and survives rounds.
    """
    import uuid

    try:
        pack_data, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    pack_dir = resolve_pack_dir(pack)

    with pack_lock(pack_dir):
        pack_data, _styles = _load_pack_arg(pack)
        items = pack_data.setdefault("feedback", [])

        if add:
            scope = "variant" if variant else "icon" if icon else "pack"
            import time as _time

            item = {
                "id": uuid.uuid4().hex[:8],
                "scope": scope,
                "text": add.strip()[:500],
                "author": author if author in ("user", "agent") else "agent",
                "round": "cli",
                "created": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
            }
            if icon:
                if icon not in pack_data["icons"]:
                    typer.secho(f"unknown icon '{icon}'", fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=2)
                item["icon"] = icon
            if variant:
                if not icon or variant not in pack_data["icons"][icon].get("variants", {}):
                    typer.secho(f"unknown variant '{variant}'", fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=2)
                item["variant"] = variant
            items.append(item)
            write_pack_atomic(pack_dir, pack_data)
            typer.secho(f"added [{item['id']}] {scope}: {item['text'][:70]}", fg=typer.colors.GREEN)
        elif resolve or promote:
            fid = resolve or promote
            item = next((i for i in items if i["id"] == fid), None)
            if item is None:
                typer.secho(f"no feedback item '{fid}'", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=2)
            if resolve:
                items.remove(item)
                typer.secho(f"resolved {fid}", fg=typer.colors.GREEN)
            else:
                if item.get("scope") == "pack":
                    label = ""
                elif item.get("scope") == "variant":
                    label = f"{item.get('icon', '')}#{item.get('variant')}: "
                else:
                    label = f"{item.get('icon', '')}: "
                if to == "rules":
                    pack_data.setdefault("rules", []).append(f"{label}{item['text']}".strip())
                else:
                    standing = str(pack_data.get("note") or "")
                    sep = " · " if standing else ""
                    pack_data["note"] = f"{standing}{sep}{label}{item['text']}".strip()
                items.remove(item)
                typer.secho(
                    f"promoted {fid} → {'rules' if to == 'rules' else 'standing note'}",
                    fg=typer.colors.GREEN,
                )
            write_pack_atomic(pack_dir, pack_data)

    if not add and not resolve and not promote:
        if not items:
            typer.echo("no live feedback — the next draft starts clean")
        for i in items:
            where = (
                f"{i.get('icon', '')}#{i.get('variant', '')}"
                if i.get("scope") != "pack"
                else "pack"
            )
            typer.echo(f"  [{i['id']}] ({i['author']}, {where}) {i['text'][:80]}")


@app.command()
def waive(
    pack: str,
    target: str = typer.Argument(help="icon#variant or style:<style-id>."),
    check: str = typer.Argument(help="min_gap | grid | live_area | max_nodes | palette"),
    reason: str = typer.Option(..., "--reason", help="why this exception is fine (written down)."),
    by: str = typer.Option("user", help="user or agent."),
) -> None:
    """Record a documented gate exception. The gate passes with a note."""
    pack_dir = resolve_pack_dir(pack)
    with pack_lock(pack_dir):
        pack_data, _ = _load_pack_arg(pack)
        pack_data.setdefault("waivers", []).append(
            {"check": check, "target": target, "reason": reason[:200], "by": by}
        )
        write_pack_atomic(pack_dir, pack_data)
    typer.secho(f"waived {check} for {target} — {reason[:60]}", fg=typer.colors.GREEN)


@app.command(name="style-ref")
def style_ref_cmd(
    pack: str,
    add: str = typer.Option(None, "--add", help="Copy an SVG file in as an own reference."),
    style: str = typer.Option(..., "--style", help="Style id the reference belongs to."),
) -> None:
    """Own style references (override the bundled ones); no args = list."""
    import shutil

    pack_dir = resolve_pack_dir(pack)
    if add:
        src = Path(add)
        if not src.is_file():
            typer.secho(f"not a file: {src}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
        d = pack_dir / ".style-refs" / style
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, d / src.name)
        typer.secho(f"own reference added: {style}/{src.name}", fg=typer.colors.GREEN)
        return
    from iconpilot.styles import style_refs

    for f in style_refs(pack_dir, style):
        origin = "own" if str(f).startswith(str(pack_dir)) else "bundled"
        typer.echo(f"  {origin}: {f.name}")


@app.command(name="recraft-style")
def recraft_style(
    pack: str,
    match: str = typer.Option("precise", help="Style match: precise or flexible."),
) -> None:
    """Create a Recraft custom style from approved/pinned icons; store its id in pack.json."""
    import iconpilot.recraft as rc

    try:
        pack_data, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    token = rc.resolve_token()
    if not token:
        typer.secho(
            "no Recraft token — set RECRAFT_API_TOKEN or [recraft] token in "
            + str(rc.models_path()),
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)

    pack_dir = resolve_pack_dir(pack)

    # collect references grouped by PACK STYLE — each gets its own Recraft
    # style, so mono and color variants stay independently consistent.
    refs_by_style: dict[str, list[str]] = {}
    seen: set[tuple[str, str, str]] = set()

    def add_ref(iid: str, vid: str, pack_style: str) -> None:
        key = (iid, vid, pack_style)
        if key in seen:
            return
        bucket = refs_by_style.setdefault(pack_style, [])
        if len(bucket) >= 10:  # Recraft limit per style
            return
        f = pack_dir / "icons" / iid / f"{vid}.svg"
        if f.is_file():
            bucket.append(f.read_text())
            seen.add(key)

    for pri in (True, False):  # pinned pass, then approved pass
        for iid, icon in pack_data["icons"].items():
            for vid, v in icon.get("variants", {}).items():
                if not (
                    (pri and v.get("pinned"))
                    or (not pri and v.get("status") == "approved" and v.get("chosen"))
                ):
                    continue
                add_ref(iid, vid, v["style"])
    if not refs_by_style:
        typer.secho(
            "no reference SVGs — approve (or pin) at least one variant first",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)

    style_ids: dict[str, str] = {}
    try:
        for pack_style, refs in refs_by_style.items():
            style = rc.create_style(token, refs, match=match)
            style_ids[pack_style] = style["id"]
            typer.echo(f"  {pack_style}: {style['id']} ({len(refs)} refs)")
    except rc.RecraftError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    recraft = pack_data.setdefault("recraft", {})
    recraft["style_id"] = next(iter(style_ids.values()))
    recraft["style_ids"] = {**recraft.get("style_ids", {}), **style_ids}
    recraft["model"] = rc.DEFAULT_MODEL
    recraft.setdefault("name", f"{pack_data['name']} style")
    with pack_lock(pack_dir):
        write_pack_atomic(pack_dir, pack_data)
    typer.secho(
        f"recraft styles created for {list(style_ids)} "
        f"(~${rc.STYLE_CREATE_PRICE * len(style_ids):.3f}) "
        "— stored in pack.json",
        fg=typer.colors.GREEN,
    )


@app.command()
def draft(
    pack: str,
    icon_id: str = typer.Argument(help="Icon id to draft."),
    variant: str = typer.Option(None, help="Variant/style id (default: the icon's only variant)."),
    n: int = typer.Option(4, min=1, max=6, help="Candidates to generate."),
    prompt: str = typer.Option("", help="Extra prompt text appended to the brief."),
    new_round: bool = typer.Option(False, "--new-round", help="Start a fresh run directory."),
) -> None:
    """Seed candidates for one icon via the Recraft API, then gate them."""
    import iconpilot.recraft as rc

    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    token = rc.resolve_token()
    if not token:
        typer.secho("no Recraft token — set RECRAFT_API_TOKEN", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    icon = pack_data["icons"].get(icon_id)
    if icon is None:
        typer.secho(f"unknown icon '{icon_id}'", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    variants = [v for v in icon.get("variants", {}) if "style" in icon["variants"][v]]
    if variant:
        if variant not in variants:
            typer.secho(f"no variant '{variant}' on {icon_id}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
    elif len(variants) == 1:
        variant = variants[0]
    else:
        typer.secho(
            f"{icon_id} has variants {variants} — pass --variant", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=2)

    style = styles[icon["variants"][variant]["style"]]
    recraft_cfg = pack_data.get("recraft", {})
    style_id = recraft_cfg.get("style_ids", {}).get(
        icon["variants"][variant]["style"]
    ) or recraft_cfg.get("style_id")
    if not style_id:
        typer.secho(
            "note: no recraft style_id — attaching approved/pinned SVGs as style "
            "references (+$0.005); run `iconpilot recraft-style` for a reusable style",
            fg=typer.colors.YELLOW,
            err=True,
        )

    pack_dir = resolve_pack_dir(pack)

    # prompt: description (docs) over brief, + color world + style words + rules
    full_prompt = rc.draft_prompt(icon, style, pack_data)
    if prompt:
        full_prompt = (full_prompt + ", " + prompt)[:1000]

    # style references: pinned/approved SVGs on the same style, else the
    # approved sibling of this icon (max 3)
    refs: list[str] = []
    if not style_id:
        for iid, ic in pack_data["icons"].items():
            for vid, vd in ic.get("variants", {}).items():
                if len(refs) >= 3:
                    break
                if (
                    vd.get("pinned")
                    and vd.get("status") == "approved"
                    and vd.get("style") == icon["variants"][variant]["style"]
                ):
                    f = pack_dir / "icons" / iid / f"{vid}.svg"
                    if f.is_file():
                        refs.append(f.read_text())
        if not refs:
            for vid, vd in icon.get("variants", {}).items():
                if vid != variant and vd.get("status") == "approved":
                    f = pack_dir / "icons" / icon_id / f"{vid}.svg"
                    if f.is_file():
                        refs = [f.read_text()]
                        break
    model = recraft_cfg.get("model") or (
        rc.DEFAULT_MODEL if (style_id or refs) else rc.FALLBACK_MODEL
    )
    n_cfg = int(recraft_cfg.get("n", n))

    try:
        raw_svgs = rc.generate(
            token,
            full_prompt,
            n=n_cfg,
            style_id=style_id,
            model=model,
            reference_urls=[rc._svg_data_url(s) for s in refs] or None,
        )
    except rc.RecraftError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    # run directory: latest, or a new one
    pack_dir = resolve_pack_dir(pack)
    runs_dir = pack_dir / ".runs"
    runs = sorted(p.name for p in runs_dir.glob("r*")) if runs_dir.is_dir() else []
    if new_round or not runs:
        run = next_run_id(runs_dir)
    else:
        run = runs[-1]
    viewbox = pack_data["spec"]["viewBox"]
    normalized = [rc.normalize(raw, viewbox) for raw in raw_svgs]
    wrote: list[Path] = []
    with pack_lock(pack_dir):  # count + write + cost under the lock (race-safe)
        cand_dir = runs_dir / run / variant / icon_id
        cand_dir.mkdir(parents=True, exist_ok=True)
        existing = len(list(cand_dir.glob("r*.svg")))
        for i, svg in enumerate(normalized, start=1):
            f = cand_dir / f"r{existing + i}.svg"
            f.write_text(svg)
            wrote.append(f)

        # record cost (round.json convention from the skill)
        round_json = runs_dir / run / "round.json"
        try:
            rj = json.loads(round_json.read_text()) if round_json.is_file() else {}
        except ValueError:
            rj = {}
        rj.setdefault("models_used", {})["seeder"] = (
            pack_data.get("recraft", {}).get("model") or rc.FALLBACK_MODEL
        )
        rj["candidates_generated"] = rj.get("candidates_generated", 0) + len(wrote)
        rj["estimated_cost_usd"] = round(
            rj.get("estimated_cost_usd", 0)
            + rc.price_per_image(model) * len(wrote)
            + (rc.STYLE_REF_PRICE if refs else 0),
            4,
        )
        round_json.write_text(json.dumps(rj, indent=2) + "\n")

    # gate each seed (informational — seeds are redrawn by the agent, not shipped)
    n_pass = 0
    for f in wrote:
        report = run_gate(f, pack_data, style)
        if report.passed:
            n_pass += 1
    typer.secho(
        f"{run}/{variant}/{icon_id}: {len(wrote)} seeds written (r{existing + 1}"
        f"..r{existing + len(wrote)}), gate {n_pass}/{len(wrote)} pass "
        f"~${rc.price_per_image(style_id and rc.DEFAULT_MODEL or rc.FALLBACK_MODEL) * len(wrote):.2f}"
        f" ({style_id and rc.DEFAULT_MODEL or rc.FALLBACK_MODEL})",
        fg=typer.colors.GREEN,
    )
    if n_pass < len(wrote):
        typer.secho(
            "seeds failing the gate are expected — agent redraws on-grid; "
            "run `iconpilot step` for details",
            fg=typer.colors.YELLOW,
        )


@app.command(name="style-export")
def style_export(
    pack: str, out: str = typer.Option(..., "--out", help="Output JSON path.")
) -> None:
    """Export the pack's style profile (spec + styles + rules + notes + anchors) as JSON."""
    try:
        pack_data, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    # collect anchor SVGs
    anchors = {}
    pack_dir = resolve_pack_dir(pack)
    for iid, icon in pack_data["icons"].items():
        for vid, v in icon.get("variants", {}).items():
            if v.get("anchor") or v.get("pinned"):
                f = pack_dir / "icons" / iid / f"{vid}.svg"
                if f.is_file():
                    anchors[f"{iid}#{vid}"] = {
                        "brief": icon.get("brief", ""),
                        "svg": f.read_text(),
                        "pinned": bool(v.get("pinned")),
                    }

    profile = {
        "format": "iconpilot-style-profile",
        "version": 1,
        "pack_name": pack_data["name"],
        "spec": pack_data.get("spec", {}),
        "styles": pack_data.get("styles", {}),
        "rules": pack_data.get("rules", []),
        "note": pack_data.get("note"),
        "anchors": anchors,
    }
    Path(out).write_text(json.dumps(profile, indent=2))
    typer.secho(f"exported style profile → {out} ({len(anchors)} anchors)", fg=typer.colors.GREEN)


@app.command(name="style-import")
def style_import(
    pack: str,
    profile_path: str = typer.Option(..., "--from", help="Style profile JSON path."),
) -> None:
    """Import a style profile into a pack (merges spec/styles/rules/notes)."""
    try:
        pack_data, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    profile = json.loads(Path(profile_path).read_text())
    if profile.get("format") != "iconpilot-style-profile":
        typer.secho("not a valid iconpilot style profile", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    pack_dir = resolve_pack_dir(pack)
    from iconpilot.pack import revalidate, write_pack_atomic

    if profile.get("spec"):
        pack_data.setdefault("spec", {}).update(profile["spec"])
    if profile.get("styles"):
        pack_data.setdefault("styles", {}).update(profile["styles"])
    if profile.get("rules"):
        existing = pack_data.get("rules", [])
        new_rules = [r for r in profile["rules"] if r not in existing]
        pack_data["rules"] = existing + new_rules
    if profile.get("note") and not pack_data.get("note"):
        pack_data["note"] = profile["note"]

    # import anchor SVGs: copy to icons/ AND register as pinned variants
    for ref_id, data in profile.get("anchors", {}).items():
        iid, _, vid = ref_id.partition("#")
        # copy the SVG to icons/ so context.py can read it
        icon_dir = pack_dir / "icons" / iid
        icon_dir.mkdir(parents=True, exist_ok=True)
        svg_file = icon_dir / f"{vid}.svg"
        if not svg_file.exists():
            svg_file.write_text(data["svg"])
        # register as a pinned reference variant in pack.json
        icon = pack_data["icons"].setdefault(iid, {"brief": data.get("brief", ""), "variants": {}})
        if vid not in icon["variants"]:
            icon["variants"][vid] = {
                "style": "mono-line",
                "status": "approved",
                "pinned": True,
                "chosen": {"run": "style-import", "variant": "ref"},
            }
        else:
            icon["variants"][vid].setdefault("pinned", True)

    _, errors = revalidate(pack_data)
    if errors:
        typer.secho("rejected:\n  - " + "\n  - ".join(errors), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    write_pack_atomic(pack_dir, pack_data)
    typer.secho(
        f"imported style profile from {profile_path} "
        f"({len(profile.get('anchors', {}))} anchor refs)",
        fg=typer.colors.GREEN,
    )


@app.command()
def diff(pack: str) -> None:
    """Show what changed since the last round: statuses, briefs, notes, SVG edits."""
    from iconpilot.edits import detect_edits

    try:
        pack_data, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    pack_dir = resolve_pack_dir(pack)

    # find the last two rounds with decisions
    runs = sorted(p.name for p in (pack_dir / ".runs").glob("r*") if p.is_dir())
    decided_runs = []
    for run in reversed(runs):
        if (pack_dir / ".runs" / run / "decisions.json").is_file():
            decided_runs.append(run)
        if len(decided_runs) >= 2:
            break

    typer.echo(f"── {pack_data['name']} — changes in {decided_runs[0] if decided_runs else '—'}")

    # 1) hand-edited SVGs (content_hash mismatches)
    edited = detect_edits(pack_dir, pack_data)
    if edited:
        typer.secho("  ✎ hand-edited SVGs:", fg=typer.colors.YELLOW)
        for e in edited:
            typer.echo(f"    {e['icon']}#{e['variant']}")

    # 2) decisions from last round
    if decided_runs:
        dec_path = pack_dir / ".runs" / decided_runs[0] / "decisions.json"
        try:
            dec = json.loads(dec_path.read_text())
            typer.secho(f"  decisions in {decided_runs[0]}:", fg=typer.colors.GREEN)
            for key, payload in dec.get("icons", {}).items():
                parts = []
                for i in payload.get("items", []):
                    if "action" in i:  # {cand, action} from decide
                        parts.append(f"{i.get('cand', '?')} {i['action']}")
                    elif "rate_cand" in i:  # {rate_cand, rate_n}
                        parts.append(f"{i.get('rate_cand', '?')} rated {i.get('rate_n', '?')}/10")
                    else:
                        parts.append(str(i.get("t", "?")))
                typer.echo(f"    {key}: {' · '.join(parts)}")
            if dec.get("instructions"):
                typer.secho(f"  instructions: {dec['instructions']}", fg=typer.colors.CYAN)
        except (ValueError, OSError):
            pass

    # 3) variant status summary
    counts: dict[str, int] = {}
    for icon in pack_data["icons"].values():
        for v in icon["variants"].values():
            if "style" in v:
                st = v.get("status", "todo")
                counts[st] = counts.get(st, 0) + 1
    summary = " · ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    typer.secho(f"  pack: {summary}", fg=typer.colors.GREEN)

    # 4) notes (pack, icon, variant)
    if pack_data.get("note"):
        typer.secho(f"  pack note: {pack_data['note'][:80]}", fg=typer.colors.CYAN)
    for iid, icon in pack_data["icons"].items():
        for vid, v in icon["variants"].items():
            if v.get("note"):
                typer.secho(f"  note {iid}#{vid}: {v['note'][:60]}", fg=typer.colors.CYAN)


@app.command()
def step(pack: str) -> None:
    """One round step: gate all candidates + contact sheet + status signal."""
    import subprocess
    import sys

    pack_dir = resolve_pack_dir(pack)
    runs = (
        sorted(p.name for p in (pack_dir / ".runs").glob("r*"))
        if (pack_dir / ".runs").is_dir()
        else []
    )
    if not runs:
        typer.secho("no rounds under .runs/", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    latest = pack_dir / ".runs" / runs[-1]

    # 1) gate
    typer.echo(f"── gating {runs[-1]} …")
    rc = subprocess.call(
        [sys.executable, "-m", "iconpilot.cli", "gate", str(latest), "--pack", pack]
    )
    if rc != 0:
        typer.secho("gate failures — fix before screening", fg=typer.colors.RED)
        # still generate the sheet so the user can see failures

    # 2) contact sheet
    typer.echo("── contact sheet …")
    from iconpilot.render.contact import contact_sheet as make_sheet

    svgs = sorted(latest.rglob("*.svg"))
    svgs = [s for s in svgs if not s.name.startswith(".")]
    if svgs:
        sheet = latest / "contact-sheet.png"
        make_sheet(svgs, sheet, title=runs[-1])
        typer.secho(f"  {len(svgs)} icons → {sheet}", fg=typer.colors.GREEN)

    # 3) status signal
    n_pass = sum(1 for f in latest.rglob("*.gate.json") if json.loads(f.read_text()).get("passed"))
    n_total = sum(1 for _ in latest.rglob("*.gate.json"))
    msg = f"round {runs[-1]}: {n_pass}/{n_total} passed gate — ready for screening"
    (pack_dir / ".runs" / ".ai-status").write_text(msg + "\n")
    typer.secho(f"── {msg}", fg=typer.colors.GREEN)


@app.command(name="packs")
def packs() -> None:
    """List discovered packs across configured roots (config.toml [packs].dirs)."""
    from iconpilot.packs import config_path, discover_packs, pack_roots

    found = discover_packs()
    roots = ", ".join(str(r) for r in pack_roots()) or "none"
    typer.echo(f"roots: {roots}  (configure in {config_path()})")
    if not found:
        typer.secho(
            "no packs found — pass a pack path to any command, or add roots to config.toml",
            fg=typer.colors.YELLOW,
        )
        return
    for p in found:
        typer.echo(f"  {p['path']}  —  {summarize(p['path'])}")


@app.command()
def status(pack: str) -> None:
    """Per-variant states, open work, and rounds."""
    try:
        pack_data, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    pack_dir = resolve_pack_dir(pack)
    runs = (
        sorted(p.name for p in (pack_dir / ".runs").glob("r*"))
        if (pack_dir / ".runs").is_dir()
        else []
    )

    from iconpilot.edits import detect_edits

    edited = {(e["icon"], e["variant"]) for e in detect_edits(pack_dir, pack_data)}

    counts: dict[str, int] = {}
    for icon_id, icon in pack_data["icons"].items():
        parts = []
        color = f" {icon['main_color']}" if icon.get("main_color") else ""
        for vid, v in icon["variants"].items():
            if "link" in v:
                parts.append(f"{vid}→{v['link']}")
                continue
            st = v.get("status", "todo")
            counts[st] = counts.get(st, 0) + 1
            extra = ""
            if v.get("chosen"):
                extra = f" ({v['chosen']['run']}/{v['chosen']['variant']})"
            if v.get("request"):
                r = v["request"]
                extra += f" [{r.get('type')}{' ' + str(r['n']) if r.get('n') else ''}]"
            if (icon_id, vid) in edited:
                extra += " ✎edited"
            parts.append(f"{vid}:{st}{extra}")
        typer.echo(f"  {icon_id}{color}  {' · '.join(parts)}")
    summary = " · ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "empty"
    typer.secho(
        f"{pack_data['name']} — {summary} · rev {pack_data.get('rev', 0)}"
        + (f" · rounds {runs[0]}…{runs[-1]}" if runs else " · no rounds"),
        fg=typer.colors.GREEN,
    )


@app.command(name="install-skill")
def install_skill(force: bool = typer.Option(False, "--force")) -> None:
    """Symlink the skill into ~/.agents/skills/iconpilot (+ ~/.claude/skills)."""
    from importlib import resources as _res

    src = Path(str(_res.files("iconpilot"))) / "skill"
    if not (src / "SKILL.md").is_file():
        typer.secho(f"skill not found in package: {src}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    agents = Path.home() / ".agents" / "skills" / "iconpilot"
    agents.parent.mkdir(parents=True, exist_ok=True)
    if agents.is_symlink():
        agents.unlink()
    elif agents.exists():
        if not force:
            typer.secho(
                f"{agents} exists and is not a symlink — pass --force to replace",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=2)
        import shutil as _shutil

        _shutil.rmtree(agents)
    agents.symlink_to(src, target_is_directory=True)
    typer.secho(f"  → {agents} -> {src}", fg=typer.colors.GREEN)
    claude = Path.home() / ".claude" / "skills" / "iconpilot"
    if claude.parent.is_dir():
        if claude.is_symlink():
            claude.unlink()
        if not claude.exists():
            claude.symlink_to(agents, target_is_directory=True)
            typer.secho(f"  → {claude} -> {agents}", fg=typer.colors.GREEN)


@app.command()
def review(
    pack: str,
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
) -> None:
    """Serve the live review page (decisions + per-icon editing)."""
    try:
        _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    pack_dir = resolve_pack_dir(pack)
    serve_review(pack_dir, host, port)


@app.command()
def check(pack: str) -> None:
    """Validate a pack: schema, semantics, style resolution, links, DAG."""
    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    n_icons = len(pack_data["icons"])
    n_variants = sum(len(i["variants"]) for i in pack_data["icons"].values())
    typer.secho(
        f"valid — {n_icons} icons, {n_variants} variants, {len(styles)} styles resolvable",
        fg=typer.colors.GREEN,
    )


@app.command()
def context(
    pack: str,
    icon: str = typer.Option(..., "--icon"),
    variant: str = typer.Option(None, "--variant"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Emit the deterministic context for one icon variant."""
    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    if icon not in pack_data["icons"]:
        typer.secho(f"unknown icon '{icon}'", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    if variant is None:
        from iconpilot.pack import resolve_default_variant

        variant = resolve_default_variant(pack_data["icons"][icon]) or "mono"
    try:
        ctx = build_context(Path(pack), pack_data, styles, icon, variant)
    except (KeyError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(ctx, indent=2) if as_json else render_markdown(ctx))


@app.command(name="contact-sheet")
def contact_sheet_cmd(
    target: str = typer.Argument(..., help="Run dir (.runs/r001) or pack icons/ dir."),
    pack: str = typer.Option(..., "--pack"),
    out: str = typer.Option(
        None, "--out", help="Output PNG path (default: <target>/contact-sheet.png)"
    ),
) -> None:
    """Compose a PNG contact sheet of candidates or approved icons."""
    from pathlib import Path as _P

    try:
        _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    d = _P(target)
    svgs = sorted(d.rglob("*.svg")) if d.is_dir() else [_P(target)]
    if not svgs:
        typer.secho(f"no SVGs under {d}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    out_path = contact_sheet(svgs, _P(out) if out else d / "contact-sheet.png", title=str(d))
    typer.secho(f"{len(svgs)} icons → {out_path}", fg=typer.colors.GREEN)


@app.command()
def decide(
    pack: str,
    text: str | None = typer.Option(None, "--text", help="Compact decision text."),
    file: str | None = typer.Option(None, "--file", help="decisions.json path."),
    round_id: str = typer.Option(None, "--round", help="Round id (default: latest run)."),
) -> None:
    """Apply user decisions (compact text or decisions.json) to pack state."""
    import json as _json
    from pathlib import Path as _P

    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    pack_dir = _P(pack)
    if pack_dir.is_file():
        pack_dir = pack_dir.parent
    runs = pack_dir / ".runs"
    if round_id is None:
        rounds = sorted(p.name for p in runs.glob("r*") if p.is_dir()) if runs.is_dir() else []
        if not rounds:
            typer.secho("no rounds under .runs/ — pass --round", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
        round_id = rounds[-1]

    try:
        if text is not None:
            decisions = parse_decision_text(text)
        elif file is not None:
            decisions = _json.loads(_P(file).read_text())["icons"]
        else:
            typer.secho("pass --text or --file", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
    except (ValueError, KeyError, OSError) as exc:
        typer.secho(f"cannot parse decisions: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    try:
        log = apply_decisions(
            pack_dir,
            pack_data,
            styles,
            decisions,
            round_id,
            source="text" if text is not None else "file",
        )
    except ValueError as exc:
        typer.secho(f"rejected: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    for line in log:
        typer.echo(f"  {line}")
    typer.secho(
        f"applied {len(decisions)} icon decisions (round {round_id})", fg=typer.colors.GREEN
    )


def resolve_pack_dir(pack: str) -> Path:
    """Accept a pack.json path or a pack directory; return the directory."""
    p = Path(pack)
    return p.parent if p.is_file() else p


def _load_pack_arg(pack: str) -> tuple[dict, dict]:
    """Accept a pack.json path or a pack directory."""
    p = Path(pack)
    if p.is_dir():
        p = p / "pack.json"
    return load_pack(p)


def _gate_one(file: Path, pack_data: dict, style, as_json: bool, write_report: bool) -> bool:
    report = run_gate(file, pack_data, style)
    if write_report:
        file.with_suffix(".gate.json").write_text(json.dumps(report.as_dict(), indent=2))
    if as_json:
        typer.echo(json.dumps(report.as_dict(), indent=2))
    else:
        for c in report.checks:
            typer.secho(f"  ✓ {c}", fg=typer.colors.GREEN)
        for e in report.errors:
            typer.secho(f"  ✗ {e}", fg=typer.colors.RED)
        typer.secho(
            f"{'PASS' if report.passed else 'FAIL'} — {file.name} against '{style.id}'",
            fg=typer.colors.GREEN if report.passed else typer.colors.RED,
        )
    return report.passed


@app.command()
def gate(
    file: str,
    pack: str = typer.Option(..., help="Pack directory or pack.json path."),
    variant: str = typer.Option(
        None, help="Variant name; single SVG only. Batch mode resolves per path."
    ),
    as_json: bool = typer.Option(False, "--json"),
    fix: bool = typer.Option(
        False, "--fix", help="Auto-fix coordinates to the grid, then re-gate."
    ),
) -> None:
    """Run the deterministic gate on an SVG — or every SVG under a run dir.

    Use --fix to snap coordinates to the precision grid before gating.

    Batch layout: <run-dir>/<variant>/<icon>/<candidate>.svg — the style is
    resolved per file from the pack; a <candidate>.gate.json is written beside
    each SVG for the drafting agent to read.
    """
    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    target = Path(file)
    icons = pack_data["icons"]

    if target.is_dir():
        passed = failed = 0
        for svg in sorted(target.rglob("*.svg")):
            rel = svg.relative_to(target).parts
            if len(rel) < 3:
                typer.secho(
                    f"  ? {svg} — not in <variant>/<icon>/<cand>.svg layout, skipped",
                    fg=typer.colors.YELLOW,
                )
                continue
            v_id, i_id = rel[0], rel[1]
            icon = icons.get(i_id)
            v = icon and icon["variants"].get(v_id)
            if not v or "style" not in v:
                typer.secho(
                    f"  ? {svg} — no authored variant {i_id}#{v_id}, skipped",
                    fg=typer.colors.YELLOW,
                )
                continue
            if _gate_one(svg, pack_data, styles[v["style"]], as_json, write_report=True):
                passed += 1
            else:
                failed += 1
        typer.secho(
            f"batch: {passed} passed, {failed} failed",
            fg=typer.colors.GREEN if not failed else typer.colors.RED,
        )
        raise typer.Exit(code=0 if not failed else 1)

    # single file
    target_v = None
    if variant:
        for icon in icons.values():
            if variant in icon.get("variants", {}):
                target_v = icon["variants"][variant]
                break
        if target_v is None or "style" not in target_v:
            typer.secho(
                f"variant '{variant}' not found as an authored variant",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=2)
    else:
        for icon in icons.values():
            vs = icon.get("variants", {})
            if "mono" in vs and "style" in vs["mono"]:
                target_v, variant = vs["mono"], "mono"
                break
        if target_v is None:
            for icon in icons.values():
                for vid, v in icon.get("variants", {}).items():
                    if "style" in v:
                        target_v, variant = v, vid
                        break
                if target_v:
                    break
    if target_v is None:
        typer.secho("pack has no authored variants to gate against", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    if fix:
        from iconpilot.gate.run import fix_svg

        spec_precision = pack_data.get("spec", {}).get("precision", 0.5)
        fixed_svg, n = fix_svg(target, spec_precision)
        if n > 0:
            backup = target.with_suffix(".orig")
            if not backup.exists():
                import shutil

                shutil.copyfile(target, backup)
            target.write_text(fixed_svg)
            typer.secho(
                f"  fixed {n} coordinate(s) snapped to {spec_precision} grid (backup: {backup.name})",
                fg=typer.colors.CYAN,
            )
        else:
            typer.secho("  already on grid — no changes needed", fg=typer.colors.GREEN)
    ok = _gate_one(target, pack_data, styles[target_v["style"]], as_json, write_report=False)
    raise typer.Exit(code=0 if ok else 1)


@app.command()
def similar(
    file: str,
    pack: str = typer.Option(..., "--pack", help="Pack directory or pack.json path."),
    threshold: int = typer.Option(
        8, "--threshold", help="Hamming distance (of 64-bit phash) flagged as near-duplicate."
    ),
) -> None:
    """Find near-duplicate icons in a pack — the link-suggestion primitive."""
    try:
        _, _styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    pack_dir = resolve_pack_dir(pack)
    icons_dir = pack_dir / "icons"

    target = hash_file(file)
    rows: list[tuple[int, Path]] = []
    for svg in sorted(icons_dir.glob("**/*.svg")) if icons_dir.is_dir() else []:
        if svg.resolve() == Path(file).resolve():
            continue
        rows.append((hamming(target, hash_file(svg)), svg))
    rows.sort(key=lambda r: r[0])

    if not rows:
        typer.echo(f"no other SVGs under {icons_dir} — nothing to compare")
        return
    for dist, svg in rows:
        flag = typer.colors.YELLOW if dist <= threshold else None
        text = f"  {dist:>3}  {svg.relative_to(pack_dir)}"
        if dist <= threshold:
            text += "  ≈ near-duplicate — consider a link"
        typer.secho(text, fg=flag)
    typer.echo(f"threshold: ≤ {threshold} (64-bit phash hamming distance)")


@app.command(name="styles")
def styles(
    pack: str = typer.Option(None, "--pack", help="Include pack-local styles for this pack."),
) -> None:
    """List the style registry: built-ins, user config, and pack-local."""
    from iconpilot.styles import BUILTIN_STYLES

    pack_local_ids: set[str] = set()
    if pack:
        try:
            data, _ = _load_pack_arg(pack)
            pack_local_ids = set(data.get("styles", {}))
        except PackError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc

    merged = resolve_styles(data.get("styles") if pack else None)
    typer.echo(f"registry: {len(merged)} styles")
    if user_styles_path().is_file():
        typer.echo(f"user config: {user_styles_path()}")
    for style_id in sorted(merged):
        s = merged[style_id]
        if pack and style_id in pack_local_ids:
            src = "pack"
        elif style_id in BUILTIN_STYLES and BUILTIN_STYLES[style_id] == s:
            src = "built-in"
        else:
            src = "user"
        desc = f"{s.construction}/{s.color_mode}"
        if s.stroke:
            desc += f" stroke {s.stroke.get('width')}"
        if s.fill:
            desc += f" fill {s.fill}"
        desc += f" · detail {s.detail} · max {s.max_nodes} nodes"
        typer.echo(f"  {style_id:<16} [{src:<8}] {s.label}: {desc}")


@app.command()
def export(
    pack: str,
    target: str = typer.Option(..., "--target", help="svg | sprite-svg | maplibre | iconify"),
    out: str = typer.Option(..., "--out"),
) -> None:
    """Export approved variants (+ approved-master links) to a target."""
    if target not in TARGETS:
        typer.secho(
            f"unknown target '{target}' (have: {', '.join(TARGETS)})", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=2)
    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    pack_dir = resolve_pack_dir(pack)
    entries, skipped = collect_exportables(pack_dir, pack_data, styles)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if target == "svg":
        written = export_svg(entries, out_dir)
    elif target == "sprite-svg":
        written = [export_sprite_svg(entries, out_dir)]
    elif target == "maplibre":
        written = export_maplibre(entries, out_dir)
    else:
        written = [export_iconify(entries, out_dir, pack_data)]

    for w in written:
        typer.secho(f"  → {w}", fg=typer.colors.GREEN)
    for s in skipped:
        typer.secho(f"  – skipped {s}", fg=typer.colors.YELLOW)
    typer.secho(f"{target}: {len(entries)} exported, {len(skipped)} skipped", fg=typer.colors.GREEN)


@app.command()
def link(write_design_md: bool = typer.Option(False, "--write-design-md")) -> None:
    """In a consuming project: create iconpilot.toml."""
    _not_implemented("link")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
