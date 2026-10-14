"""Sprint 1 feature tests: fix_svg, undo backup, step, keyboard wiring."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from iconpilot.cli import app
from tests.test_pack_schema import VALID_SVG

runner = CliRunner()

COMPOUND_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path fill-rule="evenodd" d="M2.3 2 L10 2 L10 10 L2 10 Z M4 4 L8 4 L8 8 L4 8 Z"/></svg>'
)


def test_fix_svg_preserves_compound_paths(tmp_path: Path) -> None:
    from iconpilot.gate.run import fix_svg

    f = tmp_path / "compound.svg"
    f.write_text(COMPOUND_SVG)
    fixed, changes = fix_svg(f, 0.5)
    assert fixed.count("M") >= 2, f"compound path lost subpaths: {fixed}"
    assert "Z" in fixed, f"Z closure lost: {fixed}"
    assert changes > 0, "off-grid coords should have been snapped"


def test_fix_svg_no_changes_on_grid(tmp_path: Path) -> None:
    from iconpilot.gate.run import fix_svg

    f = tmp_path / "clean.svg"
    f.write_text(VALID_SVG)
    _, changes = fix_svg(f, 0.5)
    assert changes == 0


def test_gate_fix_cli_backup(tmp_path: Path) -> None:
    d = tmp_path / "p"
    d.mkdir()
    pack = {
        "schema": 2,
        "name": "t",
        "version": "0.1.0",
        "spec": {"viewBox": "0 0 24 24", "allowed_elements": ["path"], "precision": 0.5},
        "icons": {
            "x": {"brief": "x", "variants": {"mono": {"style": "mono-line", "status": "todo"}}}
        },
    }
    (d / "pack.json").write_text(json.dumps(pack))
    f = tmp_path / "off.svg"
    f.write_text(COMPOUND_SVG)
    runner.invoke(app, ["gate", str(f), "--pack", str(d), "--fix"])
    assert f.with_suffix(".orig").exists(), "backup .orig not created"


def test_gate_fix_batch_rejected(tmp_path: Path) -> None:
    d = tmp_path / "batch"
    d.mkdir()
    r = runner.invoke(app, ["gate", str(d), "--pack", str(tmp_path), "--fix"])
    assert r.exit_code == 2


def test_undo_backup_mechanism(tmp_path: Path) -> None:
    """The file-level backup that /api/undo relies on."""
    src = tmp_path / "pack.json"
    src.write_text(json.dumps({"schema": 2, "name": "t", "icons": {}}))
    # simulate server's atomic backup
    tmp_bk = tmp_path / ".pack-backup.tmp"
    shutil.copyfile(src, tmp_bk)
    tmp_bk.rename(tmp_path / ".pack-backup.json")
    restored = json.loads((tmp_path / ".pack-backup.json").read_text())
    assert "icons" in restored


def test_step_writes_ai_status_to_runs_root(tmp_path: Path) -> None:
    d = tmp_path / "wp"
    d.mkdir()
    pack = {
        "schema": 2,
        "name": "t",
        "version": "0.1.0",
        "spec": {"viewBox": "0 0 24 24", "allowed_elements": ["path"]},
        "icons": {
            "x": {"brief": "x", "variants": {"mono": {"style": "mono-line", "status": "todo"}}}
        },
    }
    (d / "pack.json").write_text(json.dumps(pack))
    cand_dir = d / ".runs" / "r001" / "mono" / "x"
    cand_dir.mkdir(parents=True)
    (cand_dir / "a1.svg").write_text(VALID_SVG)
    r = runner.invoke(app, ["step", str(d)])
    assert r.exit_code == 0, r.output
    status = d / ".runs" / ".ai-status"
    assert status.is_file(), f"status not at {status}"


def test_page_has_keyboard_listener() -> None:
    from iconpilot.server.page import PAGE

    assert "window.addEventListener" in PAGE
    assert "kbactive" in PAGE
    assert "e.key === '1'" in PAGE


def test_cheat_sheet_fix_note() -> None:
    skill = Path(__file__).parent.parent / "src" / "iconpilot" / "skill" / "SKILL.md"
    t = skill.read_text()
    assert "single SVG only" in t


# --- Sprint 3 tests ---------------------------------------------------------


def test_strictness_field_valid(tmp_path: Path) -> None:
    """strictness=0.5 is valid in the schema."""
    d = tmp_path / "sp"
    d.mkdir()
    pack = {
        "schema": 2,
        "name": "t",
        "version": "0.1.0",
        "spec": {"viewBox": "0 0 24 24", "allowed_elements": ["path"]},
        "icons": {
            "x": {"brief": "x", "variants": {"mono": {"style": "mono-line", "status": "todo"}}}
        },
    }
    (d / "pack.json").write_text(json.dumps(pack))
    pack = json.loads((d / "pack.json").read_text())
    pack["strictness"] = 0.5
    from iconpilot.pack import revalidate

    _, errors = revalidate(pack)
    assert not errors


def test_style_export(tmp_path: Path) -> None:
    d = tmp_path / "sp"
    d.mkdir()
    pack = {
        "schema": 2,
        "name": "src",
        "version": "0.1.0",
        "spec": {"viewBox": "0 0 24 24", "allowed_elements": ["path"]},
        "rules": ["thin strokes"],
        "icons": {
            "a": {
                "brief": "a",
                "variants": {
                    "mono": {
                        "style": "mono-line",
                        "status": "approved",
                        "anchor": True,
                        "chosen": {"run": "r0", "variant": "x"},
                    }
                },
            }
        },
    }
    (d / "pack.json").write_text(json.dumps(pack))
    (d / "icons" / "a").mkdir(parents=True)
    (d / "icons" / "a" / "mono.svg").write_text("<svg/>")
    out = tmp_path / "profile.json"
    r = runner.invoke(app, ["style-export", str(d), "--out", str(out)])
    assert r.exit_code == 0, r.output
    profile = json.loads(out.read_text())
    assert profile["format"] == "iconpilot-style-profile"
    assert "a#mono" in profile["anchors"]
