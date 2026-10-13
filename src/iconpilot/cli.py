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
from iconpilot.pack import PackError, load_pack, revalidate, write_pack_atomic
from iconpilot.render.contact import contact_sheet
from iconpilot.render.render import hamming, hash_file
from iconpilot.server.server import pack_lock
from iconpilot.server.server import serve as serve_review
from iconpilot.styles import resolve_styles, user_styles_path

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
) -> None:
    """Run the deterministic gate on an SVG — or every SVG under a run dir.

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
        pack_data, _styles = _load_pack_arg(pack)
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
