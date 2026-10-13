"""Export target tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from iconpilot.cli import app
from iconpilot.export.export import export_maplibre
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
    # deterministic shelf order: size desc, then variant/icon desc
    assert layout["primitive-selfhut"] == {
        "x": 0,
        "y": 0,
        "width": 24,
        "height": 24,
        "pixelRatio": 1,
        "sdf": False,
    }
    assert layout["primitive-hut"]["x"] == 24 and layout["primitive-hut"]["y"] == 0
    assert layout["mono-hut"]["x"] == 0 and layout["mono-hut"]["y"] == 24
    assert set(layout) == {"mono-hut", "primitive-hut", "primitive-selfhut"}
    img = Image.open(out / "sprite@2x.png")
    assert img.size == (96, 96)  # width = max_px × ceil(sqrt(n)), @2x
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


COLOR_GRID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M8 22 L24 8 L40 22"/><path d="M12 22 L12 40 L36 40 L36 22"/></svg>'
)


def test_export_sprite_uses_design_sizes(exportpack: Path, tmp_path: Path) -> None:
    from iconpilot.export.export import collect_exportables
    from iconpilot.pack import load_pack, revalidate, write_pack_atomic

    pack, styles = load_pack(exportpack / "pack.json")
    pack["icons"]["hut"]["variants"]["color"]["status"] = "approved"
    (exportpack / "icons" / "hut" / "color.svg").write_text(COLOR_GRID_SVG)
    _, errors = revalidate(pack)
    assert not errors, errors
    write_pack_atomic(exportpack, pack)

    entries, _ = collect_exportables(exportpack, pack, styles)
    sizes = {(e.variant, e.icon): e.size for e in entries}
    assert sizes[("mono", "hut")] == 24 and sizes[("color", "hut")] == 48
    out = tmp_path / "sprite"
    export_maplibre(entries, out)
    layout = json.loads((out / "sprite.json").read_text())
    assert layout["mono-hut"]["width"] == 24
    assert layout["color-hut"]["width"] == 48
