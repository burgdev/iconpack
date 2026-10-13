"""Small CLI commands: new, add, status, install-skill."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from iconpilot.cli import app

runner = CliRunner()


def test_new_add_check_status_flow(tmp_path: Path) -> None:
    d = tmp_path / "alpine"
    r = runner.invoke(app, ["new", str(d)])
    assert r.exit_code == 0, r.output

    r = runner.invoke(app, ["add", str(d), "hut", "--brief",
                            "Alpine hut: steep roof, small door"])
    assert r.exit_code == 0, r.output
    assert "added hut (mono)" in r.output

    r = runner.invoke(app, ["check", str(d)])
    assert r.exit_code == 0, r.output

    r = runner.invoke(app, ["status", str(d)])
    assert r.exit_code == 0
    assert "hut" in r.output and "mono:todo" in r.output

    pack = json.loads((d / "pack.json").read_text())
    assert pack["icons"]["hut"]["variants"]["mono"]["style"] == "mono-line"


def test_new_refuses_overwrite(tmp_path: Path) -> None:
    d = tmp_path / "alpine"
    runner.invoke(app, ["new", str(d)])
    r = runner.invoke(app, ["new", str(d)])
    assert r.exit_code == 2


def test_add_multi_variant_and_unknown_style(tmp_path: Path) -> None:
    d = tmp_path / "alpine"
    runner.invoke(app, ["new", str(d)])
    r = runner.invoke(app, [
        "add", str(d), "lake", "--brief", "Mountain lake",
        "--variant", "primitive:primitive", "--variant", "mono:mono-line",
        "--variant", "color:lineal-color",
    ])
    assert r.exit_code == 0, r.output
    pack = json.loads((d / "pack.json").read_text())
    assert set(pack["icons"]["lake"]["variants"]) == {"primitive", "mono", "color"}

    r = runner.invoke(app, ["add", str(d), "peak", "--brief", "Peak",
                            "--variant", "mono:nope"])
    assert r.exit_code == 2
    assert "unknown style" in r.output
    # nothing written
    pack = json.loads((d / "pack.json").read_text())
    assert "peak" not in pack["icons"]


def test_add_duplicate_icon_rejected(tmp_path: Path) -> None:
    d = tmp_path / "alpine"
    runner.invoke(app, ["new", str(d)])
    runner.invoke(app, ["add", str(d), "hut", "--brief", "x"])
    r = runner.invoke(app, ["add", str(d), "hut", "--brief", "y"])
    assert r.exit_code == 2


def test_install_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    (home / ".agents" / "skills").mkdir(parents=True)
    (home / ".claude" / "skills").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home)

    r = runner.invoke(app, ["install-skill"])
    assert r.exit_code == 0, r.output
    agents = home / ".agents" / "skills" / "iconpilot"
    claude = home / ".claude" / "skills" / "iconpilot"
    assert agents.is_symlink() and (agents / "SKILL.md").is_file()
    assert (agents / "craft.md").is_file()
    assert claude.is_symlink() and claude.resolve() == agents.resolve()

    # idempotent
    r = runner.invoke(app, ["install-skill"])
    assert r.exit_code == 0, r.output
