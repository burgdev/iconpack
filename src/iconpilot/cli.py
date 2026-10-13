"""iconpilot CLI."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from iconpilot import __version__
from iconpilot.gate.run import run_gate
from iconpilot.pack import PackError, load_pack
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
def bakeoff(pack: str, models: str = typer.Option(..., "--models"), icons: int = typer.Option(..., "--icons")) -> None:
    """Compare candidate drafters before the first real pack."""
    _not_implemented("bakeoff")


@app.command()
def round(
    pack: str,
    icons: str | None = typer.Option(None, "--icons"),
    no_claude: bool = typer.Option(False, "--no-claude"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Run one round: generate → gate → screen → set review."""
    _not_implemented("round")


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
def decide(
    pack: str,
    text: str | None = typer.Option(None, "--text"),
    file: str | None = typer.Option(None, "--file"),
) -> None:
    """Apply decisions from compact text or a decisions.json file."""
    _not_implemented("decide")


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


@app.command()
def gate(
    file: str,
    pack: str = typer.Option(..., "--pack", help="Pack directory or pack.json path."),
    variant: str = typer.Option(
        None, "--variant", help="Variant name; defaults to 'mono' then first authored."
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run the deterministic gate on any SVG (debug / hand-made icons)."""
    try:
        pack_data, styles = _load_pack_arg(pack)
    except PackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    icons = pack_data["icons"]
    target = None
    if variant:
        for icon_id, icon in icons.items():
            if variant in icon.get("variants", {}):
                target = icon["variants"][variant]
                break
        if target is None or "style" not in target:
            typer.secho(f"variant '{variant}' not found as an authored variant", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
    else:
        for icon_id, icon in icons.items():
            vs = icon.get("variants", {})
            if "mono" in vs and "style" in vs["mono"]:
                target, variant = vs["mono"], "mono"
                break
        if target is None:
            for icon_id, icon in icons.items():
                for vid, v in icon.get("variants", {}).items():
                    if "style" in v:
                        target, variant = v, vid
                        break
                if target:
                    break
    if target is None:
        typer.secho("pack has no authored variants to gate against", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    report = run_gate(file, pack_data, styles[target["style"]])
    if as_json:
        typer.echo(json.dumps(report.as_dict(), indent=2))
    else:
        for c in report.checks:
            typer.secho(f"  ✓ {c}", fg=typer.colors.GREEN)
        for e in report.errors:
            typer.secho(f"  ✗ {e}", fg=typer.colors.RED)
        typer.secho(
            f"{'PASS' if report.passed else 'FAIL'} — {file} against style '{target['style']}'"
            + (f" (variant {variant})" if variant else ""),
            fg=typer.colors.GREEN if report.passed else typer.colors.RED,
        )
    raise typer.Exit(code=0 if report.passed else 1)


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
