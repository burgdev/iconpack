"""Export target tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from iconpilot.cli import app
from tests.test_pack_schema import VALID_SVG, example_pack

runner = CliRunner()


@pytest.fixture
def exportpack(tmp_path: Path) -> Path:
    """hut: primitive+mono approved; selfhut: primitive links hut, mono not approved."""
    d = tmp_path / "outdoor-poi"
    d.mkdir()
    pack = example_pack()
    pack["icons"]["hut"]["variants"]["primitive"]["status"] = "approved"
    (d / "icons" / "hut").mkdir(parents=True)
    (d / "icons" / "hut" / "primitive.svg").write_text(VALID_SVG)
    (d / "icons" / "hut" / "mono.svg").write_text(VALID_SVG)
    (d / "pack.json").write_text(json.dumps(pack))
    return d


def test_export_svg_materializes_links(exportpack: Path, tmp_path: Path) -> None:
    out = tmp_path / "svg-out"
    r = runner.invoke(app, ["export", str(exportpack), "--target", "svg", "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert (out / "mono" / "hut.svg").read_text().startswith("<svg")
    # selfhut primitive is a link to approved hut primitive → materialized
    assert (out / "primitive" / "hut.svg").is_file()
    assert (out / "primitive" / "selfhut.svg").is_file()
    # selfhut mono not approved → skipped
    assert not (out / "mono" / "selfhut.svg").exists()
    assert "skipped" in r.output


def test_export_sprite_svg(exportpack: Path, tmp_path: Path) -> None:
    out = tmp_path / "sprite"
    r = runner.invoke(app, ["export", str(exportpack), "--target", "sprite-svg", "--out", str(out)])
    assert r.exit_code == 0, r.output
    text = (out / "sprite.svg").read_text()
    for sid in ("mono-hut", "primitive-hut", "primitive-selfhut"):
        assert f'id="{sid}"' in text
    assert "<symbol" in text and "stroke-linecap" in text


def test_export_maplibre(exportpack: Path, tmp_path: Path) -> None:
    out = tmp_path / "maplibre"
    r = runner.invoke(app, ["export", str(exportpack), "--target", "maplibre", "--out", str(out)])
    assert r.exit_code == 0, r.output
    layout = json.loads((out / "sprite.json").read_text())
    assert layout["mono-hut"] == {
        "x": 0,
        "y": 0,
        "width": 24,
        "height": 24,
        "pixelRatio": 1,
        "sdf": False,
    }
    assert set(layout) == {"mono-hut", "primitive-hut", "primitive-selfhut"}
    img = Image.open(out / "sprite@2x.png")
    assert img.size == (96, 96)  # 3 icons @48px: 2 cols × 2 rows (shelf pack)
    at2x = json.loads((out / "sprite@2x.json").read_text())
    assert at2x["mono-hut"]["pixelRatio"] == 2


def test_export_iconify(exportpack: Path, tmp_path: Path) -> None:
    out = tmp_path / "iconify"
    r = runner.invoke(app, ["export", str(exportpack), "--target", "iconify", "--out", str(out)])
    assert r.exit_code == 0, r.output
    coll = json.loads((out / "outdoor-poi.json").read_text())
    assert coll["prefix"] == "outdoor-poi"
    assert set(coll["icons"]) == {"hut-mono", "hut-primitive"}
    assert coll["aliases"] == {"selfhut-primitive": {"parent": "hut-primitive"}}
    assert "body" in coll["icons"]["hut-mono"]
    assert coll["icons"]["hut-mono"]["width"] == 24


def test_export_rejects_unknown_target(exportpack: Path, tmp_path: Path) -> None:
    r = runner.invoke(app, ["export", str(exportpack), "--target", "font", "--out", str(tmp_path)])
    assert r.exit_code == 2
