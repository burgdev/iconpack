"""Recraft integration tests — all HTTP mocked, no network."""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from iconpilot import recraft as rc
from iconpilot.cli import app

runner = CliRunner()


def _pack(tmp_path: Path, *, with_style_id: bool = False, pinned: bool = False) -> Path:
    d = tmp_path / "pk"
    d.mkdir()
    flat: dict = {"style": "color-flat", "status": "approved" if pinned else "todo"}
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
    monkeypatch.setattr(rc, "png_data_url", lambda s, size=512: "data:image/png;base64,VEVTVA==")
    out = rc.create_style("tok", ["<svg/>"])
    assert out["id"] == "st-42"
    assert captured["path"] == "/styles"
    urls = captured["payload"]["image_urls"]
    assert urls[0].startswith("data:image/png;base64,")  # /styles needs raster
    assert captured["payload"]["model"] == "recraftv4_styles"
    assert captured["payload"]["match"] == "precise"
    assert captured["payload"]["style"] == "vector_illustration"


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

    def fake_generate(token, prompt, n=4, style_id=None, model=None, reference_urls=None):
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
    assert pack["recraft"]["style_ids"] == {"color-flat": "st-1", "mono-line": "st-2"}
    assert made == [[_pack.__defaults__ and "x" or "x"] for _ in range(2)] or len(made) == 2


def test_draft_picks_per_style_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path, with_style_id=True)
    pack = json.loads((d / "pack.json").read_text())
    pack["recraft"]["style_ids"] = {"color-flat": "per-style-9"}
    (d / "pack.json").write_text(json.dumps(pack))
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")

    seen: dict = {}

    def fake_generate(token, prompt, n=4, style_id=None, model=None, reference_urls=None):
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


# --- description vs feedback + pricing ----------------------------------------


def test_schema_description_fields(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    pack = json.loads((d / "pack.json").read_text())
    pack["description"] = "Wodore outdoor accommodation icons"
    pack["icons"]["sun"]["description"] = "A sun with eight rays"
    (d / "pack.json").write_text(json.dumps(pack))
    from iconpilot.pack import revalidate

    _, errors = revalidate(pack)
    assert not errors


def test_context_pack_description_and_feedback(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    pack = json.loads((d / "pack.json").read_text())
    pack["description"] = "pack docs"
    pack["note"] = "pack feedback"
    pack["icons"]["sun"]["note"] = "legacy icon note"
    (d / "pack.json").write_text(json.dumps(pack))
    from iconpilot.context import build_context
    from iconpilot.pack import load_pack

    pack_data, styles = load_pack(d / "pack.json")
    ctx = build_context(d, pack_data, styles, "sun", "flat")
    assert ctx["pack_description"] == "pack docs"
    assert "icon_description" not in ctx  # brief is the single icon description
    assert ctx["brief"]  # the brief is present, shared human+agent
    assert ctx["pack_note"] == "pack feedback"
    assert ctx["icon_note"] == "legacy icon note"


def test_fallback_model_is_cheapest_vector() -> None:
    from iconpilot.recraft import FALLBACK_MODEL, price_per_image

    assert FALLBACK_MODEL == "recraftv2_vector"
    assert price_per_image(FALLBACK_MODEL) == 0.044
    assert price_per_image("recraftv4_styles_vector") == 0.05
    assert price_per_image("unknown") == 0.08


def test_draft_without_style_uses_fallback_and_its_price(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d = _pack(tmp_path)  # no recraft block → fallback model
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")

    seen: dict = {}

    def fake_generate(token, prompt, n=4, style_id=None, model=None, reference_urls=None):
        seen["model"] = model
        return [SRC]

    monkeypatch.setattr(rc, "generate", fake_generate)
    r = runner.invoke(app, ["draft", str(d), "sun", "--n", "1"])
    assert r.exit_code == 0, r.output
    assert "recraftv2_vector" in r.output
    rj = json.loads((d / ".runs" / "r001" / "round.json").read_text())
    assert rj["estimated_cost_usd"] == 0.044


# --- feedback CLI + context ----------------------------------------------------


def test_feedback_cli_lifecycle(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    r = runner.invoke(app, ["feedback", str(d), "--add", "thinner roof", "--icon", "sun"])
    assert r.exit_code == 0 and "added" in r.output
    r = runner.invoke(app, ["feedback", str(d)])
    assert "thinner roof" in r.output
    fid = r.output.split("[")[1].split("]")[0]
    r = runner.invoke(app, ["feedback", str(d), "--promote", fid])
    assert r.exit_code == 0 and "standing note" in r.output
    pack = json.loads((d / "pack.json").read_text())
    assert "thinner roof" in pack["note"] and pack["feedback"] == []


def test_context_includes_feedback_scopes(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    pack = json.loads((d / "pack.json").read_text())
    pack["feedback"] = [
        {"id": "a", "scope": "pack", "text": "pack fb", "author": "user", "round": "r001"},
        {
            "id": "b",
            "scope": "icon",
            "icon": "sun",
            "text": "icon fb",
            "author": "agent",
            "round": "r001",
        },
        {
            "id": "c",
            "scope": "variant",
            "icon": "sun",
            "variant": "flat",
            "text": "var fb",
            "author": "user",
            "round": "r001",
        },
        {
            "id": "d",
            "scope": "icon",
            "icon": "other",
            "text": "not mine",
            "author": "user",
            "round": "r001",
        },
    ]
    (d / "pack.json").write_text(json.dumps(pack))
    from iconpilot.context import build_context, render_markdown
    from iconpilot.pack import load_pack

    pack_data, styles = load_pack(d / "pack.json")
    ctx = build_context(d, pack_data, styles, "sun", "flat")
    texts = [i["text"] for i in ctx["feedback"]]
    assert "pack fb" in texts and "icon fb" in texts and "var fb" in texts
    assert "not mine" not in texts
    md = render_markdown(ctx)
    assert "[user] pack fb" in md and "[agent] icon fb" in md


def test_next_archives_and_migrates_legacy_notes(tmp_path: Path) -> None:
    d = _pack(tmp_path)
    pack = json.loads((d / "pack.json").read_text())
    pack["icons"]["sun"]["note"] = "legacy icon note"
    pack["feedback"] = [
        {"id": "z", "scope": "pack", "text": "live item", "author": "user", "round": "r001"}
    ]
    (d / "pack.json").write_text(json.dumps(pack))
    r = runner.invoke(app, ["next", str(d)])
    assert r.exit_code == 0 and "feedback carried" in r.output
    fb = json.loads((d / ".runs" / "r001" / "feedback.json").read_text())
    texts = [i["text"] for i in fb]
    assert "live item" in texts and "legacy icon note" in texts
    pack = json.loads((d / "pack.json").read_text())
    assert pack["feedback"] == [] and "note" not in pack["icons"]["sun"]


def test_context_archived_feedback_scope_filtered(tmp_path: Path) -> None:
    """Archived feedback for icon A must NOT leak into icon B's context."""
    d = _pack(tmp_path)
    pack = json.loads((d / "pack.json").read_text())
    pack["icons"]["moon"] = {
        "brief": "crescent",
        "variants": {"flat": {"style": "color-flat", "status": "todo"}},
    }
    (d / "pack.json").write_text(json.dumps(pack))
    (d / ".runs" / "r001").mkdir(parents=True)
    (d / ".runs" / "r001" / "feedback.json").write_text(
        json.dumps(
            [
                {
                    "id": "1",
                    "scope": "icon",
                    "icon": "sun",
                    "text": "sun fb",
                    "author": "user",
                    "round": "r001",
                },
                {"id": "2", "scope": "pack", "text": "pack fb", "author": "user", "round": "r001"},
            ]
        )
    )
    from iconpilot.context import build_context, render_markdown
    from iconpilot.pack import load_pack

    pack_data, styles = load_pack(d / "pack.json")
    ctx = build_context(d, pack_data, styles, "moon", "flat")
    texts = [i["text"] for i in ctx.get("feedback", [])]
    assert "pack fb" in texts
    assert "sun fb" not in texts  # no cross-icon bleed
    md = render_markdown(ctx)
    assert "[user] pack fb" in md


def test_styles_extends_resolution() -> None:
    from iconpilot.styles import resolve_styles

    styles = resolve_styles(
        {"outline-color": {"extends": "mono-filled", "size": 48, "palette": ["#123456"]}}
    )
    st = styles["outline-color"]
    assert st.size == 48
    assert st.construction == "solid"  # inherited from filled
    import pytest as _pytest

    with _pytest.raises(ValueError, match="unknown extends"):
        resolve_styles({"bad": {"extends": "nope"}})


def test_draft_prompt_uses_brief_and_colors() -> None:
    from iconpilot.recraft import draft_prompt
    from iconpilot.styles import resolve_styles

    icon = {
        "brief": "Two alpine peaks under a low sun",
        "main_color": "#2b6cb0",
    }
    pack = {"rules": ["no chimneys"], "styles": {}}
    import dataclasses

    style = dataclasses.replace(
        resolve_styles({})["color-flat"],
        palette=("#2b6cb0", "#2f855a", "#c05621", "#4a5568"),
    )
    p = draft_prompt(icon, style, pack)
    assert "Two alpine peaks under a low sun" in p  # the brief describes the icon
    assert "#2b6cb0" in p  # main color + palette
    assert "no chimneys" in p


def test_generate_rejects_non_vector_model() -> None:
    with pytest.raises(rc.RecraftError, match="vector"):
        rc.generate("t", "x", model="recraftv4_1")  # raster model


def test_generate_reference_urls_in_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_request(token, method, path, payload=None):
        captured["payload"] = payload
        import base64

        b64 = base64.b64encode(b"<svg/>").decode()
        return {"data": [{"b64_json": b64}]}

    monkeypatch.setattr(rc, "_request", fake_request)
    rc.generate(
        "t",
        "x",
        n=1,
        model="recraftv4_styles_vector",
        reference_urls=["data:image/svg+xml;base64,PHN2Zy8+"],
    )
    assert captured["payload"]["style_reference_urls"] == ["data:image/svg+xml;base64,PHN2Zy8+"]
    assert "style_id" not in captured["payload"]


# --- style refs, snapshot, gate config, waivers -------------------------------


def test_bundled_refs_exist_for_every_registry_style() -> None:
    from iconpilot.styles import bundled_refs_path, resolve_styles

    for sid in resolve_styles({}):
        refs = list((bundled_refs_path() / sid).glob("*.svg"))
        assert len(refs) >= 3, f"{sid} needs >= 3 bundled refs"


def test_own_refs_beat_bundled(tmp_path: Path) -> None:
    from iconpilot.styles import style_refs

    d = tmp_path / "pk"
    d.mkdir()
    (d / ".style-refs" / "mono-line").mkdir(parents=True)
    (d / ".style-refs" / "mono-line" / "mine.svg").write_text("<svg/>")
    refs = style_refs(d, "mono-line")
    assert [r.name for r in refs] == ["mine.svg"]


def test_add_snapshots_style_into_pack(tmp_path: Path) -> None:
    d = tmp_path / "pk"
    d.mkdir()
    runner.invoke(app, ["new", str(d)])
    r = runner.invoke(
        app, ["add", str(d), "sun", "--brief", "sun", "--variant", "m:color-broken-line"]
    )
    assert r.exit_code == 0, r.output
    pack = json.loads((d / "pack.json").read_text())
    snap = pack["styles"]["color-broken-line"]
    assert snap["extends"] == "color-broken-line" and snap["color_mode"] == "color"
    # pack is now independent: even a hypothetical registry change wouldn't drift


def test_gate_config_toggles_check(tmp_path: Path) -> None:
    from iconpilot.gate.run import run_gate
    from iconpilot.styles import resolve_styles

    style = resolve_styles(
        {"color-broken-line": {"extends": "mono-line", "gate": {"min_gap": False}}}
    )["color-broken-line"]
    pack = {
        "icons": {},
        "spec": {
            "viewBox": "0 0 24 24",
            "allowed_elements": ["path"],
            "precision": 0.5,
            "live_area": {"padding": 2},
            "stroke": {"width": 2, "linecap": "round", "linejoin": "round"},
            "fill": "none",
        },
    }
    # two strokes 1.0 apart → min_gap failure on mono-line; waived on color-broken-line
    svg = tmp_path / "g.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round"><path d="M6 6 H18"/><path d="M6 7 H18"/></svg>'
    )
    base = resolve_styles({})["mono-line"]
    r_base = run_gate(svg, pack, base)
    r_broken = run_gate(svg, pack, style)
    assert not r_base.passed
    assert r_broken.passed
    assert any("style config: min_gap off" in c for c in r_broken.checks)


def test_waiver_suppresses_with_reason(tmp_path: Path) -> None:
    from iconpilot.gate.run import run_gate
    from iconpilot.styles import resolve_styles

    d = tmp_path / "pk"
    (d / "icons" / "sun" / "mono").mkdir(parents=True)
    svg = d / "icons" / "sun" / "mono.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round"><path d="M6 6 H18"/><path d="M6 7 H18"/></svg>'
    )
    pack = {
        "icons": {
            "sun": {"brief": "s", "variants": {"mono": {"style": "mono-line", "status": "todo"}}}
        },
        "spec": {
            "viewBox": "0 0 24 24",
            "allowed_elements": ["path"],
            "precision": 0.5,
            "live_area": {"padding": 2},
            "stroke": {"width": 2, "linecap": "round", "linejoin": "round"},
            "fill": "none",
        },
        "waivers": [
            {"check": "min_gap", "target": "sun#mono", "reason": "gap is intentional", "by": "user"}
        ],
    }
    style = resolve_styles({})["mono-line"]
    rep = run_gate(svg, pack, style)
    assert rep.passed
    assert any("waiver by user" in c and "gap is intentional" in c for c in rep.checks)


# --- sheet mode: 3x3 / 4x4 in one call -----------------------------------------


def _sheet_svg(grid: int = 3) -> str:
    """Synthetic NxN sheet: one small square per cell, cells at 100px pitch."""
    parts = []
    for gy in range(grid):
        for gx in range(grid):
            x, y = gx * 100 + 30, gy * 100 + 30
            parts.append(f'<rect x="{x}" y="{y}" width="40" height="40" fill="#2b6cb0"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {grid * 100} {grid * 100}">'
        + "".join(parts)
        + "</svg>"
    )


def test_sheet_prompt_leads_with_same_subject_semantics() -> None:
    p = rc.sheet_prompt("a sailboat", 3)
    # same-subject variations FIRST (highest priority), not a suffix
    assert p.startswith("Icon design sheet: 9 different design variations of ONE icon")
    assert "same subject" in p and "keep the subject identical" in p
    assert "3 by 3 grid" in p
    assert "a sailboat" in p
    assert len(p) <= 1000
    # and the icon description follows the semantics, not precedes them
    assert p.index("a sailboat") > p.index("ONE icon")


def test_split_sheet_3x3() -> None:
    cells = rc.split_sheet(_sheet_svg(3), 3, target=24.0)
    assert len(cells) == 9
    for svg in cells:
        assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"')
        assert "<rect" in svg


def test_split_sheet_4x4() -> None:
    cells = rc.split_sheet(_sheet_svg(4), 4, target=24.0)
    assert len(cells) == 16


def test_split_sheet_rejects_no_viewbox() -> None:
    with pytest.raises(rc.RecraftError):
        rc.split_sheet("<svg><rect x='1' y='1' width='2' height='2'/></svg>", 3)


def test_draft_sheet_mode_writes_grid_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d = _pack(tmp_path, with_style_id=True)
    monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")

    def fake_generate(token, prompt, n=4, style_id=None, model=None, reference_urls=None):
        assert "3 by 3 grid" in prompt and n == 1
        return [_sheet_svg(3)]

    monkeypatch.setattr(rc, "generate", fake_generate)
    r = runner.invoke(app, ["draft", str(d), "sun", "--sheet", "3"])
    assert r.exit_code == 0, r.output
    seeds = sorted((d / ".runs" / "r001" / "flat" / "sun").glob("r*.svg"))
    assert len(seeds) == 9  # 9 candidates from 1 image
    assert "9 seeds" in r.output


def test_split_sheet_prefers_named_groups() -> None:
    """Named groups or vector bboxes — 9 cells from a proper 2D 3x3 grid."""
    groups = ""
    for gy in range(3):
        for gx in range(3):
            i = gy * 3 + gx + 1
            groups += (
                f'<g id="icon{i}"><rect x="{gx * 120 + 40}" y="{gy * 120 + 40}" '
                f'width="40" height="40" fill="#2b6cb0"/></g>'
            )
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 360">{groups}</svg>'
    cells = rc.split_sheet(svg, 3)
    assert len(cells) == 9
    assert all("<rect" in c and "svg:" not in c for c in cells)


def test_split_sheet_falls_back_when_groups_missing() -> None:
    cells = rc.split_sheet(_sheet_svg(3), 3)  # no ids → clustering
    assert len(cells) == 9
    assert all("svg:" not in c for c in cells)


def test_sheet_prompt_has_clean_margins() -> None:
    p = rc.sheet_prompt("a sailboat", 3)
    assert "clean margins" in p and "no touching" in p
    assert "g id" not in p  # wrapper instruction removed


def test_split_sheet_row_major_order() -> None:
    """Cells map row-major: top-right comes before bottom-left."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
        '<rect x="120" y="20" width="60" height="60" fill="#111111"/>'
        '<rect x="20" y="120" width="60" height="60" fill="#222222"/>'
        "</svg>"
    )
    cells = rc.split_sheet(svg, 2, target=24.0)
    assert len(cells) == 2
    assert "#111111" in cells[0]
    assert "#222222" in cells[1]


def test_normalize_recenters_offcenter_content() -> None:
    raw = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
        '<path fill="#282727" d="M100 100h200v200H100z"/>'
        "</svg>"
    )
    out = rc.normalize(raw, "0 0 24 24")
    assert "translate(" in out and "scale(" in out
    k = 24 / 1024
    tx = (24 - k * 200) / 2 - k * 100
    # probe=256 quantizes bbox edges to 4 source units → tx within ±0.06
    assert any(f"translate({tx + d:.3f}" in out for d in (-0.06, -0.03, 0.0, 0.03, 0.06)), (
        f"centering off: expected ~{tx:.3f}"
    )
    full = rc.normalize(SRC, "0 0 24 24")
    assert '<g transform="scale(' in full and "translate(" not in full


def test_pack_sheet_prompt_different_icons_per_cell() -> None:
    p = rc.pack_sheet_prompt(["a tent", "a map", "a boot"], "Lineal color", 2)
    assert "distinct icons" in p and "one icon per cell" in p
    assert "cell 1 at top left (1,1): a tent" in p
    assert "cell 3 at bottom left (2,1): a boot" in p
    assert "Leave the remaining 1 cell(s) empty" in p
    assert "same stroke weight" in p  # cross-cell consistency demand
    assert "variations of ONE" not in p  # different pattern than sheet_prompt


def test_pack_grid_fits_icons() -> None:
    assert rc.pack_grid(4) == 2
    assert rc.pack_grid(5) == 3
    assert rc.pack_grid(9) == 3
    assert rc.pack_grid(10) == 4
    assert rc.pack_grid(16) == 4
    assert rc.pack_grid(17) == 5
    assert rc.pack_grid(25) == 5


def test_generate_sends_per_icon_colors() -> None:
    sent = {}

    def fake(token, method, path, payload=None):
        sent.update(payload or {})
        return {"data": [{"b64_json": _b64_svg("<path/>")}]}

    rc._request = fake
    rc.generate("T", "a tent", n=1, colors=["#C05621", "notacolor", "#2B6CB0"])
    assert sent["colors"] == [{"rgb": [192, 86, 33]}, {"rgb": [43, 108, 176]}]


def test_draft_prompt_icon_colors_replace_palette() -> None:
    icon = {"brief": "a tent", "main_color": "#2B6CB0", "colors": ["#C05621", "#2F855A"]}
    import dataclasses

    from iconpilot.styles import resolve_styles

    style = dataclasses.replace(resolve_styles({})["color-flat"], palette=("#111111", "#222222"))
    p = rc.draft_prompt(icon, style, {})
    assert "colors #C05621, #2F855A" in p
    assert "#111111" not in p and "#2B6CB0" not in p  # subset replaces both


def _b64_svg(inner: str) -> str:
    import base64

    return base64.b64encode(
        f'<svg xmlns="http://www.w3.org/2000/svg">{inner}</svg>'.encode()
    ).decode()


def test_to_current_color_swaps_literal_paints() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="#4A251E" d="M0 0h1v1z"/>'
        '<path fill="white" d="M1 1h1v1z"/>'
        '<path fill="none" stroke="#B9561A" d="M2 2h1v1z"/>'
        '<circle cx="3" cy="3" r="1" fill="rgb(40,39,39)"/>'
        "</svg>"
    )
    out = rc.to_current_color(svg)
    assert 'fill="currentColor"' in out
    assert 'stroke="currentColor"' in out
    assert 'fill="none"' in out  # none survives
    assert "#4A251E" not in out and "#B9561A" not in out
    assert "rgb(40,39,39)" not in out


def test_normalize_mono_replaces_colors() -> None:
    raw = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
        '<path fill="#282727" d="M0 0h512v512z"/>'
        "</svg>"
    )
    mono = rc.normalize(raw, "0 0 24 24", mono=True)
    assert "currentColor" in mono and "#282727" not in mono
    color = rc.normalize(raw, "0 0 24 24")
    assert "#282727" in color and "currentColor" not in color


def test_mono_styles_enforced_black_palette() -> None:
    from iconpilot.styles import resolve_styles

    rs = resolve_styles({})
    mono_ids = [sid for sid, st in rs.items() if st.color_mode == "mono"]
    assert mono_ids, "registry should have mono styles"
    for sid in mono_ids:
        assert rs[sid].palette == ("#000000",), f"{sid} should enforce black"
    # color styles carry example palettes, not black
    assert set(rs["color-flat"].palette) - {"#000000"}
    # an explicit pack palette on a mono style still wins (styled different later)
    custom = resolve_styles({"mono-line": {"extends": "mono-line", "palette": ["#2B6CB0"]}})
    assert custom["mono-line"].palette == ("#2B6CB0",)


def test_create_style_bakes_prompt_and_palette() -> None:
    import dataclasses

    from iconpilot.recraft import create_style, style_prompt_text
    from iconpilot.styles import resolve_styles

    style = dataclasses.replace(
        resolve_styles({})["color-broken-line"], palette=("#c05621", "#2b6cb0")
    )
    sent = {}

    def fake(token, method, path, payload=None):
        sent.update(payload or {})
        return {"id": "uuid-1"}

    rc._request = fake
    rc.png_data_url = lambda s, size=512: "data:image/png;base64,VEVTVA=="  # raster stub
    out = create_style(
        "T", ["<svg/>"], prompt=style_prompt_text(style), palette=list(style.palette)
    )
    assert out["id"] == "uuid-1"
    assert sent["prompt"].startswith("Color broken line icon style")
    assert sent["palette"] == {"colors": [{"rgb": [192, 86, 33]}, {"rgb": [43, 108, 176]}]}
    assert sent["model"] == "recraftv4_styles"
    assert sent["style"] == "vector_illustration"  # vector base — 'any' is rejected by vector gens


def test_draft_prompt_styled_false_subject_only() -> None:
    # with a Recraft style_id attached, look + palette live in the style
    icon = {"brief": "a tent", "main_color": "#2b6cb0"}
    import dataclasses

    from iconpilot.styles import resolve_styles

    style = dataclasses.replace(
        resolve_styles({})["color-flat"], palette=("#2b6cb0",), style_words=("flat fills",)
    )
    p = rc.draft_prompt(icon, style, {}, styled=False)
    assert p.startswith("vector icon of a tent")
    assert "#2b6cb0" not in p  # colors are baked into the style
    assert "color-flat" not in p and "flat fills" not in p


def test_draft_prompt_colors_before_style() -> None:
    # Recraft priority: earlier elements dominate — color must precede style
    icon = {"brief": "Two alpine peaks", "main_color": "#2b6cb0"}
    import dataclasses

    from iconpilot.styles import resolve_styles

    style = dataclasses.replace(resolve_styles({})["color-flat"], palette=("#2b6cb0",))
    p = rc.draft_prompt(icon, style, {})
    assert p.startswith("vector icon of Two alpine peaks")
    assert p.index("#2b6cb0") < p.index("icon style")


def test_curated_style_map_covers_registry() -> None:
    from iconpilot.recraft import CURATED_STYLE_MAP
    from iconpilot.styles import resolve_styles

    missing = set(resolve_styles({})) - set(CURATED_STYLE_MAP)
    assert not missing, f"styles without curated mapping: {missing}"


def test_generate_refs_curated_uses_style_param(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_request(token, method, path, payload=None):
        captured["payload"] = payload
        import base64

        return {"data": [{"b64_json": base64.b64encode(_sheet_svg(3).encode()).decode()}]}

    monkeypatch.setattr(rc, "_request", fake_request)
    cells = rc.generate_refs_curated("t", "color-broken-line", ["home", "leaf", "zap"], 3)
    assert captured["payload"]["style"] == "Broken line"
    assert captured["payload"]["model"] == "recraftv2_vector"
    assert len(cells) == 9


def test_account_style_cache_shared_across_packs(tmp_path, monkeypatch) -> None:
    """Same refs in two packs → one Recraft create, second pack reuses the id."""
    import iconpilot.recraft as rc

    monkeypatch.setattr(rc, "style_cache_path", lambda: tmp_path / "style_cache.json")
    assert rc.style_cache_get("h1") is None
    rc.style_cache_put("h1", "id-aaa", "mono-line")
    assert rc.style_cache_get("h1") == "id-aaa"
    # one id belongs to one hash: re-registering id-aaa under h2 moves it
    rc.style_cache_put("h2", "id-aaa", "mono-line")
    assert rc.style_cache_get("h1") is None
    assert rc.style_cache_get("h2") == "id-aaa"
    rc.style_cache_put("h1", "id-bbb", "mono-line")
    assert rc.style_cache_get("h1") == "id-bbb"
    # corrupt cache never raises
    (tmp_path / "style_cache.json").write_text("{not json")
    assert rc.style_cache_get("h1") is None


def test_with_px_size_stamps_dimensions() -> None:
    s = rc.with_px_size('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path/></svg>')
    assert 'width="512" height="512"' in s and 'viewBox="0 0 24 24"' in s
    # existing sizes replaced, not duplicated
    s2 = rc.with_px_size('<svg width="24" height="24" viewBox="0 0 24 24"/>')
    assert s2.count("width=") == 1 and 'width="512"' in s2


def test_refine_payload_and_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = {}

    def fake(token, method, path, payload=None):
        sent.update(payload or {})
        sent["_path"] = path
        return {"data": [{"b64_json": _b64_svg("<path/>")}]}

    monkeypatch.setattr(rc, "_request", fake)
    out = rc.refine(
        "T",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path/></svg>',
        "flame too heavy, thin the logs",
        strength=5.0,  # clamped to 1.0
        model="recraftv4_1_vector",
        n=9,  # clamped to 6
    )
    assert len(out) == 1
    assert sent["_path"] == "/images/imageToImage"
    assert sent["model"] == "recraftv4_1_vector"
    assert sent["strength"] == 1.0
    assert sent["n"] == 6
    assert sent["image_url"].startswith("data:image/svg+xml;base64,")
    # feedback is required — no feedback, no refine
    with pytest.raises(rc.RecraftError, match="feedback"):
        rc.refine("T", "<svg/>", "  ", strength=0.3)
    # v4+ only
    with pytest.raises(rc.RecraftError, match="v4"):
        rc.refine("T", "<svg/>", "x", strength=0.3, model="recraftv2_vector")


def test_adopt_svg_deterministic_pipeline(tmp_path) -> None:
    """Seed with transforms, bg rect, gradients, off-palette → pack icon."""
    from iconpilot.adopt import adopt_svg
    from iconpilot.styles import resolve_styles

    seed = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
        '<defs><linearGradient id="g1"><stop offset="0" stop-color="#ff0000"/>'
        '<stop offset="1" stop-color="#0000ff"/></linearGradient></defs>'
        '<rect x="0" y="0" width="1024" height="1024" fill="#ffffff"/>'
        '<g transform="translate(-100 -100) scale(1.5)">'
        '<path fill="url(#g1)" d="M100 100 L700 100 L700 700 Z"/>'
        '<path fill="#123456" d="M200 200 H400 V400 H200 Z"/>'
        "</g></svg>"
    )
    style = resolve_styles({})["color-flat"]
    pack = {"icons": {}, "spec": {"viewBox": "0 0 48 48", "precision": 0.5}}
    out, fixes, _errors, kept = adopt_svg(seed, style, pack)
    assert "0 0 48 48" in out  # style design grid
    assert "<g" not in out and "transform=" not in out  # baked
    assert "url(" not in out and "linearGradient" not in out  # gradients collapsed
    import re

    fills = set(re.findall(r'fill="([^"]+)"', out))
    pal = {c.lower() for c in style.palette}
    # near-duplicates snap into the palette; distinct seed colors stay
    # verbatim and are returned for registration into icon.colors
    assert fills <= pal | set(kept), fills
    assert "#123456" in fills and "#123456" in kept  # distinct → kept verbatim
    assert "kept" in "; ".join(fixes)
    assert any("background" in f for f in fixes)
    assert any("transform" in f for f in fixes)
    assert out.count("<path") >= 2
    # parseable output
    from xml.etree import ElementTree as ET

    ET.fromstring(out)


def test_refine_grid_svg_composition() -> None:
    """Grid sheet: row-major nesting, own viewBox per cell, true total size."""
    import re
    import xml.etree.ElementTree as ET

    from iconpilot.recraft import refine_grid_svg

    # sources already stamped with px size + viewBox (like with_px_size does)
    srcs = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        f'viewBox="0 0 {sz} {sz}"><path d="M1 1"/></svg>'
        for sz in (24, 48)
    ] * 2  # 4 sources → 2×2
    out = refine_grid_svg(srcs, 2)
    ET.fromstring(out)  # must parse: no re-defined attributes
    assert 'width="1024"' in out and 'height="1024"' in out  # 2×512
    assert 'viewBox="0 0 1024 1024"' in out
    # cell 0 top-left, cell 1 top-right, cell 2 bottom-left (row-major)
    # xmlns stays (kept from the source root), geometry attrs appear once
    assert re.search(r'<svg[^>]*\sx="0" y="0" width="512"', out)
    assert re.search(r'<svg[^>]*\sx="512" y="0" width="512"', out)
    assert re.search(r'<svg[^>]*\sx="0" y="512" width="512"', out)
    assert out.count("<svg") == 5  # outer + 4 nested
    # no re-defined attributes anywhere (Recraft XML-parses the sheet)
    for tag in re.findall(r"<svg[^>]*>", out):
        for attr in ("viewBox", "width", "height", "x", "y"):
            assert len(re.findall(rf'\b{attr}="', tag)) <= 1, f"{attr} re-defined in {tag}"


def test_refine_sheet_prompt_anchors() -> None:
    """Cell anchors + per-cell change instructions + empty-cell note."""
    from iconpilot.recraft import refine_sheet_prompt

    p = refine_sheet_prompt(
        [
            "campfire icon (Mono line) — change: flame too heavy",
            "peak icon (Mono line) — change: thinner ridge",
        ],
        2,
    )
    assert "2 by 2 grid" in p
    assert "cell 1 at top left (1,1)" in p
    assert "cell 2 at top right (1,2)" in p
    assert "change: flame too heavy" in p
    assert "Leave the remaining 2 cell(s) empty" in p  # 2 of 4 used
    assert "no text" in p


def test_refine_grid_debug_flow() -> None:
    """Server grid refine: one call per sheet, cells mapped back per icon."""
    from iconpilot.server.server import ReviewHandler

    with tempfile.TemporaryDirectory() as td:
        pack_dir = Path(td)
        (pack_dir / "icons" / "sail").mkdir(parents=True)
        (pack_dir / "icons" / "sail" / "flat.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path d="M4 4H44V44Z"/></svg>'
        )
        (pack_dir / ".runs" / "r001" / "flat" / "campfire").mkdir(parents=True)
        (pack_dir / ".runs" / "r001" / "flat" / "campfire" / "r1.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path d="M4 4L44 44"/></svg>'
        )
        pack = {
            "schema": 2,
            "name": "gridrefine-test",
            "provenance": {"created_by": "user"},
            "spec": {
                "viewBox": "0 0 48 48",
                "live_area": {"padding": 4},
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
            },
            "styles": {},
            "icons": {
                "sail": {
                    "brief": "a sailboat",
                    "variants": {"flat": {"style": "color-flat", "status": "todo"}},
                },
                "campfire": {
                    "brief": "a campfire",
                    "variants": {"flat": {"style": "color-flat", "status": "todo"}},
                },
            },
            "version": "0.1.0",
            "feedback": [
                {
                    "id": "fb1",
                    "scope": "variant",
                    "icon": "sail",
                    "variant": "flat",
                    "round": "r001",
                    "text": "boom longer",
                    "author": "user",
                },
                {
                    "id": "fb2",
                    "scope": "variant",
                    "icon": "campfire",
                    "variant": "flat",
                    "round": "r001",
                    "text": "flame smaller",
                    "author": "user",
                },
            ],
        }
        (pack_dir / "pack.json").write_text(json.dumps(pack))
        h = ReviewHandler.__new__(ReviewHandler)  # skip socket init
        h.pack_dir = pack_dir
        out = h._recraft_refine(
            {"targets": ["sail#flat", "campfire#flat"], "grid": 2, "takes": 2, "debug": True},
        )
        assert out["grid"] == 2
        assert len(out["calls"]) == 1  # ONE sheet for both icons
        call = out["calls"][0]
        assert call["cells"] == 2
        assert "sail" in call["prompt"] and "campfire" in call["prompt"]
        assert "change: boom longer" in call["prompt"] and "change: flame smaller" in call["prompt"]
        assert "items" not in out  # debug preview only
        # per-icon flow unchanged when grid=0
        out1 = h._recraft_refine(
            {"targets": ["sail#flat", "campfire#flat"], "takes": 2, "debug": True}
        )
        assert len(out1["calls"]) == 2  # one call per icon


def test_next_carry_keeps_survivors_drops_rejects(tmp_path: Path) -> None:
    """--carry: surviving takes move into the new round; rejects and 0-ratings stay behind."""
    d = _pack(tmp_path)
    runner.invoke(app, ["next", str(d)])
    cdir = d / ".runs" / "r001" / "flat" / "sun"
    cdir.mkdir(parents=True)
    for n in ("r1.svg", "r2.svg", "r3.svg"):
        (cdir / n).write_text(f"<svg>{n}</svg>")
    # decisions: r2 rejected, r3 rated 0, r1 rated 7
    (d / ".runs" / "r001" / "decisions.json").write_text(
        json.dumps(
            {
                "round": "r001",
                "icons": {
                    "sun/flat": {
                        "items": [
                            {"rate_cand": "r1", "rate_n": "7"},
                            {"cand": "r2", "action": "no"},
                            {"rate_cand": "r3", "rate_n": "0"},
                        ]
                    }
                },
            }
        )
    )
    r = runner.invoke(app, ["next", str(d), "--carry"])
    assert r.exit_code == 0, r.output
    assert "carried takes" in r.output
    new = d / ".runs" / "r002" / "flat" / "sun"
    assert (new / "r1.svg").is_file()  # rated 7 → survives
    assert not (new / "r2.svg").is_file()  # rejected → dropped
    assert not (new / "r3.svg").is_file()  # rated 0 → dropped
    assert (cdir / "r2.svg").is_file()  # history keeps everything


def test_context_embeds_current_candidates_with_verdicts(tmp_path: Path) -> None:
    """context includes prior-round takes + verdicts — feedback names take ids."""
    d = _pack(tmp_path)
    runner.invoke(app, ["next", str(d)])
    cdir = d / ".runs" / "r001" / "flat" / "sun"
    cdir.mkdir(parents=True)
    (cdir / "r1.svg").write_text('<svg viewBox="0 0 24 24"><path d="M2 2"/></svg>')
    (cdir / "r2.svg").write_text('<svg viewBox="0 0 24 24"><path d="M4 4"/></svg>')
    (d / ".runs" / "r001" / "decisions.json").write_text(
        json.dumps(
            {
                "round": "r001",
                "icons": {"sun/flat": {"items": [{"rate_cand": "r2", "rate_n": "8"}]}},
            }
        )
    )
    r = runner.invoke(app, ["context", str(d), "--icon", "sun", "--variant", "flat", "--json"])
    assert r.exit_code == 0, r.output
    ctx = json.loads(r.output)
    cands = ctx["current_candidates"]
    assert len(cands) == 2
    by_id = {c["id"]: c for c in cands}
    assert by_id["r1"]["verdict"] == "unrated"
    assert by_id["r2"]["verdict"] == "rated 8/10"
    assert 'd="M4 4"' in by_id["r2"]["svg"]  # full SVG source embedded


def test_adopt_cli_reports_fixes_and_gate(tmp_path: Path) -> None:
    """adopt converts a raw seed and reports residuals instead of failing."""
    from tests.test_pack_schema import SPEC, example_pack

    d = tmp_path / "adoptpack"
    d.mkdir()
    pack = example_pack()
    pack["spec"] = json.loads(json.dumps(SPEC))
    (d / "pack.json").write_text(json.dumps(pack))
    seed = d / "seed.svg"
    seed.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="0" y="0" width="24" height="24" fill="#ffffff"/>'
        '<g transform="translate(-2 -2) scale(1.2)">'
        '<path fill="rgb(40,80,60)" d="M5 5 L15 5 L15 15 Z"/>'
        "</g></svg>"
    )
    r = runner.invoke(
        app,
        ["adopt", str(seed), "--pack", str(d), "--icon", "hut", "--variant", "mono"],
    )
    assert r.exit_code == 0, r.output
    assert "fixes applied" in r.output or "gate: clean" in r.output


def test_refine_grid_saves_input_and_output_sheets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Grid refine keeps the composed input sheet + returned sheets + prompt."""
    import iconpilot.recraft as rc
    from iconpilot.server.server import ReviewHandler

    with tempfile.TemporaryDirectory() as td:
        pack_dir = Path(td)
        (pack_dir / ".runs" / "r001" / "flat" / "sail").mkdir(parents=True)
        (pack_dir / ".runs" / "r001" / "flat" / "sail" / "r1.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path d="M4 4L44 44"/></svg>'
        )
        pack = {
            "schema": 2,
            "name": "sheets-test",
            "version": "0.1.0",
            "provenance": {"created_by": "user"},
            "spec": {
                "viewBox": "0 0 48 48",
                "live_area": {"padding": 4},
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
            },
            "styles": {},
            "icons": {
                "sail": {
                    "brief": "a sailboat",
                    "variants": {"flat": {"style": "color-flat", "status": "todo"}},
                },
            },
            "feedback": [
                {
                    "id": "fb1",
                    "scope": "variant",
                    "icon": "sail",
                    "variant": "flat",
                    "round": "r001",
                    "text": "boom longer",
                    "author": "user",
                },
            ],
        }
        (pack_dir / "pack.json").write_text(json.dumps(pack))

        def fake_refine(
            token, svg_text, prompt, strength, model="recraftv4_1_vector", n=2, size=512
        ):
            return [
                (
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
                    '<path d="M0 0h512v512H0z"/></svg>'
                )
            ] * n

        monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")
        monkeypatch.setattr(rc, "refine", fake_refine)
        h = ReviewHandler.__new__(ReviewHandler)
        h.pack_dir = pack_dir
        out = h._recraft_refine({"targets": ["sail#flat"], "grid": 2, "takes": 2})
        assert out["grid"] == 2
        sheets = pack_dir / ".runs" / "r001" / "sheets"
        names = sorted(x.name for x in sheets.iterdir())
        assert any("-input.svg" in n for n in names)  # composed source grid
        assert any("-t1.svg" in n for n in names) and any("-t2.svg" in n for n in names)
        assert any(n.endswith(".prompt.txt") for n in names)
        inp = next(x for x in sheets.iterdir() if "-input" in x.name)
        assert 'x="0" y="0" width="512"' in inp.read_text()  # real composed grid


def test_adopt_keeps_distinct_seed_colors_verbatim() -> None:
    """Adopt registers the art's colors; only near-duplicates snap."""
    from iconpilot.adopt import adopt_svg
    from iconpilot.styles import resolve_styles

    seed = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="#5b8fb5" d="M2 2H22V22H2Z"/>'  # distinct blue — must stay
        '<path fill="#3f7f5f" d="M4 4H10V10H4Z"/>'  # distinct green — must stay
        '<path fill="#7fc97f" d="M12 12H18V18H12Z"/>'  # near #7ecc7e palette dup
        "</svg>"
    )
    style = resolve_styles({"palette": ["#7ecc7e", "#cccccc"]}) if False else None
    from dataclasses import replace

    base = resolve_styles({})["color-flat"]
    style = replace(base, palette=["#7ecc7e", "#cccccc"], max_nodes=200)
    pack = {"icons": {}, "spec": {"viewBox": "0 0 48 48", "precision": 0.5}}
    out, fixes, _errs, kept = adopt_svg(seed, style, pack, gate_check=False)
    assert "#5b8fb5" in out and "#3f7f5f" in out  # verbatim, not snapped
    assert "#5b8fb5" in kept and "#3f7f5f" in kept
    assert "kept 2 seed color(s)" in "; ".join(fixes)


def test_refine_prompt_carries_style_anchor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-icon and grid refine prompts both anchor the style contract."""
    import iconpilot.recraft as rc
    from iconpilot.server.server import ReviewHandler

    with tempfile.TemporaryDirectory() as td:
        pack_dir = Path(td)
        (pack_dir / ".runs" / "r001" / "flat" / "sail").mkdir(parents=True)
        (pack_dir / ".runs" / "r001" / "flat" / "sail" / "r1.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path d="M4 4L44 44"/></svg>'
        )
        pack = {
            "schema": 2,
            "name": "anchor-test",
            "version": "0.1.0",
            "provenance": {"created_by": "user"},
            "spec": {
                "viewBox": "0 0 48 48",
                "live_area": {"padding": 4},
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
            },
            "styles": {
                "color-flat": {
                    "extends": "color-flat",
                    "style_words": ["flat", "bold shapes"],
                    "palette": ["#775b44", "#22534f"],
                    "avoid": ["gradients"],
                }
            },
            "icons": {
                "sail": {
                    "brief": "a sailboat",
                    "variants": {"flat": {"style": "color-flat", "status": "todo"}},
                }
            },
            "feedback": [
                {
                    "id": "fb1",
                    "scope": "variant",
                    "icon": "sail",
                    "variant": "flat",
                    "round": "r001",
                    "text": "boom longer",
                    "author": "user",
                },
            ],
        }
        (pack_dir / "pack.json").write_text(json.dumps(pack))

        sent: list[dict] = []

        def fake_refine(token, svg_text, prompt, strength, model="x", n=2, size=512):
            sent.append({"prompt": prompt, "n": n, "size": size})
            return [
                (
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
                    '<path d="M0 0h512v512H0z"/></svg>'
                )
            ] * n

        monkeypatch.setattr(rc, "resolve_token", lambda models_file=None: "tok")
        monkeypatch.setattr(rc, "refine", fake_refine)
        h = ReviewHandler.__new__(ReviewHandler)
        h.pack_dir = pack_dir
        h._recraft_refine({"targets": ["sail#flat"], "takes": 1})
        assert "Style: Color flat" in sent[0]["prompt"]  # anchored
        assert "flat" in sent[0]["prompt"] and "#775b44" in sent[0]["prompt"]
        assert "keep the input image's exact rendering style" in sent[0]["prompt"]
        assert "Change: boom longer" in sent[0]["prompt"]
        # grid path anchors too
        sent.clear()
        h._recraft_refine({"targets": ["sail#flat"], "grid": 2, "takes": 1})
        assert "Style: Color flat" in sent[0]["prompt"]
        assert "keep the input image's exact rendering style" in sent[0]["prompt"]
