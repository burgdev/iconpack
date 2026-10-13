"""iconpilot CLI."""

from __future__ import annotations

import typer

from iconpilot import __version__

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


@app.command()
def gate(file: str, pack: str = typer.Option(..., "--pack")) -> None:
    """Run the deterministic gate on any SVG (debug / hand-made icons)."""
    _not_implemented("gate")


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
