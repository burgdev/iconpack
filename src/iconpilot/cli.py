"""iconpilot CLI."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from iconpilot import __version__
from iconpilot.context import build_context, render_markdown
from iconpilot.decide import apply_decisions, parse_decision_text
from iconpilot.gate.run import run_gate
from iconpilot.pack import PackError, load_pack
from iconpilot.render.contact import contact_sheet
from iconpilot.render.render import hamming, hash_file
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


@app.command()
def new(pack: str, from_design_md: str | None = typer.Option(None, "--from-design-md")) -> None:
    """Create a pack (designer drafts spec + briefs)."""
    _not_implemented("new")


@app.command()
def add(pack: str, icon: str, brief: str | None = typer.Option(None, "--brief")) -> None:
    """Add an icon to the pack registry."""
    _not_implemented("add")


@app.command()
def review(
    pack: str,
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
    static: bool = typer.Option(False, "--static", help="Write a self-contained HTML file."),
) -> None:
    """Serve (or write) the review page."""
    _not_implemented("review")


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
        f"valid — {n_icons} icons, {n_variants} variants, "
        f"{len(styles)} styles resolvable",
        fg=typer.colors.GREEN,
    )


@app.command()
def context(
    pack: str,
    icon: str = typer.Option(..., "--icon"),
    variant: str = typer.Option(None, "--variant"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Emit the deterministic drafting context for one icon variant."""
    import json as _json

    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    if icon not in pack_data["icons"]:
        typer.secho(f"unknown icon '{icon}'", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    if variant is None:
        authored = [v for v, d in pack_data["icons"][icon]["variants"].items() if "style" in d]
        variant = authored[0] if len(authored) == 1 else "mono"
    try:
        ctx = build_context(Path(pack), pack_data, styles, icon, variant)
    except (KeyError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(_json.dumps(ctx, indent=2) if as_json else render_markdown(ctx))


@app.command(name="contact-sheet")
def contact_sheet_cmd(
    target: str = typer.Argument(..., help="Run dir (.runs/r001) or pack icons/ dir."),
    pack: str = typer.Option(..., "--pack"),
    out: str = typer.Option(None, "--out", help="Output PNG path (default: <target>/contact-sheet.png)"),
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
        log = apply_decisions(pack_dir, pack_data, styles, decisions, round_id,
                              source="text" if text is not None else "file")
    except ValueError as exc:
        typer.secho(f"rejected: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    for line in log:
        typer.echo(f"  {line}")
    typer.secho(f"applied {len(decisions)} icon decisions (round {round_id})",
                fg=typer.colors.GREEN)


@app.command()
def status(pack: str) -> None:
    """Show icon states, costs, and open icons."""
    _not_implemented("status")


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
                typer.secho(f"  ? {svg} — not in <variant>/<icon>/<cand>.svg layout, skipped",
                            fg=typer.colors.YELLOW)
                continue
            v_id, i_id = rel[0], rel[1]
            icon = icons.get(i_id)
            v = icon and icon["variants"].get(v_id)
            if not v or "style" not in v:
                typer.secho(f"  ? {svg} — no authored variant {i_id}#{v_id}, skipped",
                            fg=typer.colors.YELLOW)
                continue
            if _gate_one(svg, pack_data, styles[v["style"]], as_json, write_report=True):
                passed += 1
            else:
                failed += 1
        typer.secho(f"batch: {passed} passed, {failed} failed", fg=typer.colors.GREEN if not failed else typer.colors.RED)
        raise typer.Exit(code=0 if not failed else 1)

    # single file
    target_v = None
    if variant:
        for icon in icons.values():
            if variant in icon.get("variants", {}):
                target_v = icon["variants"][variant]
                break
        if target_v is None or "style" not in target_v:
            typer.secho(f"variant '{variant}' not found as an authored variant", fg=typer.colors.RED, err=True)
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

    pack_dir = Path(pack)
    if pack_dir.is_file():
        pack_dir = pack_dir.parent
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
def export(pack: str, target: str = typer.Option(..., "--target"), out: str = typer.Option(..., "--out")) -> None:
    """Export approved icons (svg, sprite-svg, maplibre, iconify, font)."""
    _not_implemented("export")


@app.command()
def link(write_design_md: bool = typer.Option(False, "--write-design-md")) -> None:
    """In a consuming project: create iconpilot.toml."""
    _not_implemented("link")


@app.command(name="install-skill")
def install_skill() -> None:
    """Symlink skill/ into ~/.agents/skills/iconpilot (+ ~/.claude/skills/)."""
    _not_implemented("install-skill")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
