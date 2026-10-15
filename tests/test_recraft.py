"""Recraft integration tests — all HTTP mocked, no network."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from iconpilot import recraft as rc
from iconpilot.cli import app

runner = CliRunner()


def _pack(tmp_path: Path, *, with_style_id: bool = False, pinned: bool = False) -> Path:
    d = tmp_path / "pk"
    d.mkdir()
    flat: dict = {"style": "flat-color", "status": "approved" if pinned else "todo"}
    if pinned:
        flat["chosen"] = {"run": "r0", "variant": "x"}
        flat["pinned"] = True
    pack = {
        "schema": 2,
        "name": "t",
        "version": "0.1.0",
        "spec": {
            "viewBox": "0 0 24 24",
            "live_area": {"padding": 3},
            "stroke": {"width": 2, "linecap": "round", "linejoin": "round"},
            "fill": "none",
            "allowed_elements": ["path", "circle", "rect", "line", "g"],
            "precision": 0.5,
        },
        "icons": {"sun": {"brief": "sun with rays", "variants": {"flat": flat}}},
    }
    if with_style_id:
        pack["recraft"] = {"style_id": "sid-1", "model": rc.DEFAULT_MODEL}
    (d / "pack.json").write_text(json.dumps(pack))
    (d / "icons" / "sun").mkdir(parents=True)
    (d / "icons" / "sun" / "flat.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M4 4h16v16H4z"/></svg>'
    )
    return d


# --- token resolution --------------------------------------------------------


def test_token_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECRAFT_API_TOKEN", "envtok")
    assert rc.resolve_token(models_file=Path("/nonexistent")) == "envtok"


def test_token_models_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RECRAFT_API_TOKEN", raising=False)
    f = tmp_path / "models.toml"
    f.write_text('[recraft]\ntoken = "tomltok"\n')
    assert rc.resolve_token(models_file=f) == "tomltok"


def test_token_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RECRAFT_API_TOKEN", raising=False)
    assert rc.resolve_token(models_file=tmp_path / "none.toml") is None


# --- client (mocked _request) ------------------------------------------------


def test_create_style_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_request(token, method, path, payload=None):
        captured.update(token=token, method=method, path=path, payload=payload)
        return {"id": "st-42"}

    monkeypatch.setattr(rc, "_request", fake_request)
    out = rc.create_style("tok", ["<svg/>"])
    assert out["id"] == "st-42"
    assert captured["path"] == "/styles"
    urls = captured["payload"]["image_urls"]
    assert urls[0].startswith("data:image/svg+xml;base64,")
    assert base64.b64decode(urls[0].split(",", 1)[1]).decode() == "<svg/>"
    assert captured["payload"]["model"] == "recraftv4_styles"
    assert captured["payload"]["match"] == "precise"


def test_generate_decodes_b64(monkeypatch: pytest.MonkeyPatch) -> None:
    svg = '<svg viewBox="0 0 1024 1024"><path d="M0 0h1024v1024H0z"/></svg>'
    b64 = base64.b64encode(svg.encode()).decode()

    def fake_request(token, method, path, payload=None):
        return {"data": [{"b64_json": b64}, {"b64_json": b64}]}

    monkeypatch.setattr(rc, "_request", fake_request)
    svgs = rc.generate("tok", "a sun", n=2, style_id="sid")
    assert svgs == [svg, svg]


def test_generate_rejects_out_of_range() -> None:
    with pytest.raises(rc.RecraftError):
        rc.generate("tok", "x", n=7)


# --- normalization -----------------------------------------------------------


SRC = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><path d="M0 0h1024v1024H0z"/></svg>'


def test_normalize_scales_to_target_grid() -> None:
    out = rc.normalize(SRC, "0 0 24 24")
    assert 'viewBox="0 0 24 24"' in out
    assert '<g transform="scale(0.023438)">' in out
    assert out.startswith("<svg")


def test_normalize_bad_target() -> None:
    with pytest.raises(rc.RecraftError):
        rc.normalize(SRC, "12 0 24 24")  # non-zero origin


# --- CLI: draft + recraft-style (mocked) -------------------------------------


def test_draft_writes_seeds_and_round_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path, with_style_id=True)
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")

    def fake_generate(token, prompt, n=4, style_id=None, model=None):
        assert style_id == "sid-1"
        assert "sun with rays" in prompt
        return [SRC] * n

    monkeypatch.setattr(rc, "generate", fake_generate)
    r = runner.invoke(app, ["draft", str(d), "sun", "--n", "3"])
    assert r.exit_code == 0, r.output
    seeds = sorted((d / ".runs" / "r001" / "flat" / "sun").glob("r*.svg"))
    assert len(seeds) == 3
    assert seeds[0].read_text().startswith("<svg")
    rj = json.loads((d / ".runs" / "r001" / "round.json").read_text())
    assert rj["models_used"]["seeder"] == rc.DEFAULT_MODEL
    assert rj["estimated_cost_usd"] == 0.15


def test_draft_requires_variant_choice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path)
    pack = json.loads((d / "pack.json").read_text())
    pack["icons"]["sun"]["variants"]["mono"] = {"style": "mono-line", "status": "todo"}
    (d / "pack.json").write_text(json.dumps(pack))
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")
    r = runner.invoke(app, ["draft", str(d), "sun"])
    assert r.exit_code == 2
    assert "--variant" in r.output


def test_draft_no_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path)
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: None)
    r = runner.invoke(app, ["draft", str(d), "sun"])
    assert r.exit_code == 2


def test_recraft_style_writes_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path, pinned=True)
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")
    monkeypatch.setattr(rc, "create_style", lambda token, refs, match="precise": {"id": "st-9"})
    r = runner.invoke(app, ["recraft-style", str(d)])
    assert r.exit_code == 0, r.output
    pack = json.loads((d / "pack.json").read_text())
    assert pack["recraft"]["style_id"] == "st-9"
    assert pack["rev"] >= 1


def test_recraft_style_needs_references(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path)  # todo status, nothing approved
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")
    r = runner.invoke(app, ["recraft-style", str(d)])
    assert r.exit_code == 2
    assert "approve" in r.output.lower()


def test_schema_allows_recraft_block(tmp_path: Path) -> None:
    d = _pack(tmp_path, with_style_id=True)
    from iconpilot.pack import revalidate

    _, errors = revalidate(json.loads((d / "pack.json").read_text()))
    assert not errors


# --- next round + per-style recraft ------------------------------------------


def test_next_creates_round_and_lists_open(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    r = runner.invoke(app, ["next", str(d)])
    assert r.exit_code == 0, r.output
    assert "r001" in r.output
    assert "sun#flat" in r.output  # todo variant is open work
    rj = json.loads((d / ".runs" / "r001" / "round.json").read_text())
    assert rj["open"] == ["sun#flat"]


def test_next_excludes_approved(tmp_path: Path) -> None:
    d = _pack(tmp_path, pinned=True)  # flat is approved+chosen
    r = runner.invoke(app, ["next", str(d)])
    assert r.exit_code == 0, r.output
    assert "sun#flat" not in r.output
    assert "nothing open" in r.output


def test_next_keeps_history_and_warns_unapplied(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    runner.invoke(app, ["next", str(d)])
    # simulate an undecided previous round then advance
    (d / ".runs" / "r001" / "flat" / "sun").mkdir(parents=True)
    (d / ".runs" / "r001" / "flat" / "sun" / "a1.svg").write_text("<svg/>")
    r = runner.invoke(app, ["next", str(d)])
    assert r.exit_code == 0
    assert "never applied" in r.output
    assert (d / ".runs" / "r001").is_dir()  # history kept
    assert (d / ".runs" / "r002").is_dir()


def test_recraft_style_per_pack_style(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path, pinned=True)
    pack = json.loads((d / "pack.json").read_text())
    pack["icons"]["sun"]["variants"]["mono"] = {
        "style": "mono-line",
        "status": "approved",
        "chosen": {"run": "r0", "variant": "x"},
    }
    (d / "pack.json").write_text(json.dumps(pack))
    (d / "icons" / "sun" / "mono.svg").write_text("<svg/>")

    made: list[list[str]] = []

    def fake_create(token, refs, match="precise"):
        made.append(refs)
        return {"id": f"st-{len(made)}"}

    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")
    monkeypatch.setattr(rc, "create_style", fake_create)
    r = runner.invoke(app, ["recraft-style", str(d)])
    assert r.exit_code == 0, r.output
    pack = json.loads((d / "pack.json").read_text())
    assert pack["recraft"]["style_ids"] == {"flat-color": "st-1", "mono-line": "st-2"}
    assert made == [[_pack.__defaults__ and "x" or "x"] for _ in range(2)] or len(made) == 2


def test_draft_picks_per_style_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path, with_style_id=True)
    pack = json.loads((d / "pack.json").read_text())
    pack["recraft"]["style_ids"] = {"flat-color": "per-style-9"}
    (d / "pack.json").write_text(json.dumps(pack))
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")

    seen: dict = {}

    def fake_generate(token, prompt, n=4, style_id=None, model=None):
        seen["style_id"] = style_id
        return [SRC]

    monkeypatch.setattr(rc, "generate", fake_generate)
    r = runner.invoke(app, ["draft", str(d), "sun", "--n", "1"])
    assert r.exit_code == 0, r.output
    assert seen["style_id"] == "per-style-9"


def test_next_run_number_gap_safe(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    # simulate manual deletion: r001 and r003 exist (gap)
    for r in ("r001", "r003"):
        (d / ".runs" / r).mkdir(parents=True)
    (d / ".runs" / "r003" / "round.json").write_text('{"round": "r003", "sentinel": 1}')
    r = runner.invoke(app, ["next", str(d)])
    assert r.exit_code == 0, r.output
    assert "r004" in r.output  # max+1, not len+1 (=r003, a clobber)
    kept = json.loads((d / ".runs" / "r003" / "round.json").read_text())
    assert kept["sentinel"] == 1  # untouched


def test_viewbox_fallbacks() -> None:
    assert rc._viewbox_size('<svg width="512" height="512"><path/></svg>') == 512.0
    assert rc._viewbox_size("<svg><path/></svg>") == 1024.0  # default


def test_recraft_style_asserts_refs_per_style(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each pack style gets ITS OWN reference set (mono refs ≠ color refs)."""
    d = _pack(tmp_path, pinned=True)
    pack = json.loads((d / "pack.json").read_text())
    pack["icons"]["sun"]["variants"]["mono"] = {
        "style": "mono-line",
        "status": "approved",
        "chosen": {"run": "r0", "variant": "x"},
    }
    (d / "pack.json").write_text(json.dumps(pack))
    (d / "icons" / "sun" / "mono.svg").write_text("<svg>MONO-REF</svg>")

    made: list[list[str]] = []
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")
    monkeypatch.setattr(
        rc,
        "create_style",
        lambda token, refs, match="precise": made.append(refs) or {"id": f"st-{len(made)}"},
    )
    r = runner.invoke(app, ["recraft-style", str(d)])
    assert r.exit_code == 0, r.output
    flat_ref = (d / "icons" / "sun" / "flat.svg").read_text()
    assert made == [[flat_ref], ["<svg>MONO-REF</svg>"]]
