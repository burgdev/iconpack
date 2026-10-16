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
    assert pack["recraft"]["style_ids"] == {"flat-color": "st-1", "mono-line": "st-2"}
    assert made == [[_pack.__defaults__ and "x" or "x"] for _ in range(2)] or len(made) == 2


def test_draft_picks_per_style_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _pack(tmp_path, with_style_id=True)
    pack = json.loads((d / "pack.json").read_text())
    pack["recraft"]["style_ids"] = {"flat-color": "per-style-9"}
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
        "variants": {"flat": {"style": "flat-color", "status": "todo"}},
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
        {"outline-color": {"extends": "filled", "size": 48, "palette": ["#123456"]}}
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
        resolve_styles({})["flat-color"],
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
    r = runner.invoke(app, ["add", str(d), "sun", "--brief", "sun", "--variant", "m:duotone"])
    assert r.exit_code == 0, r.output
    pack = json.loads((d / "pack.json").read_text())
    snap = pack["styles"]["duotone"]
    assert snap["extends"] == "duotone" and snap["color_mode"] == "bicolor"
    # pack is now independent: even a hypothetical registry change wouldn't drift


def test_gate_config_toggles_check(tmp_path: Path) -> None:
    from iconpilot.gate.run import run_gate
    from iconpilot.styles import resolve_styles

    style = resolve_styles({"broken-line": {"extends": "mono-line", "gate": {"min_gap": False}}})[
        "broken-line"
    ]
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
    # two strokes 1.0 apart → min_gap failure on mono-line; waived on broken-line
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


def test_pack_sheet_prompt_different_icons_per_cell() -> None:
    p = rc.pack_sheet_prompt(["a tent", "a map", "a boot"], "Lineal color", 2)
    assert "distinct icons" in p and "one icon per cell" in p
    assert "cell 1: a tent" in p and "cell 3: a boot" in p
    assert "same stroke weight" in p  # cross-cell consistency demand
    assert "variations of ONE" not in p  # different pattern than sheet_prompt


def test_pack_grid_fits_icons() -> None:
    assert rc.pack_grid(4) == 2
    assert rc.pack_grid(5) == 3
    assert rc.pack_grid(9) == 3


def test_create_style_bakes_prompt_and_palette() -> None:
    import dataclasses

    from iconpilot.recraft import create_style, style_prompt_text
    from iconpilot.styles import resolve_styles

    style = dataclasses.replace(resolve_styles({})["duotone"], palette=("#c05621", "#2b6cb0"))
    sent = {}

    def fake(token, method, path, payload=None):
        sent.update(payload or {})
        return {"id": "uuid-1"}

    rc._request = fake
    out = create_style(
        "T", ["<svg/>"], prompt=style_prompt_text(style), palette=list(style.palette)
    )
    assert out["id"] == "uuid-1"
    assert sent["prompt"].startswith("Duotone icon style")
    assert sent["palette"] == {"colors": [{"rgb": [192, 86, 33]}, {"rgb": [43, 108, 176]}]}
    assert sent["model"] == "recraftv4_styles"
    assert "style" not in sent  # base 'icon' style is V2-only


def test_draft_prompt_styled_false_subject_only() -> None:
    # with a Recraft style_id attached, look + palette live in the style
    icon = {"brief": "a tent", "main_color": "#2b6cb0"}
    import dataclasses

    from iconpilot.styles import resolve_styles

    style = dataclasses.replace(
        resolve_styles({})["flat-color"], palette=("#2b6cb0",), style_words=("flat fills",)
    )
    p = rc.draft_prompt(icon, style, {}, styled=False)
    assert p.startswith("vector icon of a tent")
    assert "#2b6cb0" not in p  # colors are baked into the style
    assert "flat-color" not in p and "flat fills" not in p


def test_draft_prompt_colors_before_style() -> None:
    # Recraft priority: earlier elements dominate — color must precede style
    icon = {"brief": "Two alpine peaks", "main_color": "#2b6cb0"}
    import dataclasses

    from iconpilot.styles import resolve_styles

    style = dataclasses.replace(resolve_styles({})["flat-color"], palette=("#2b6cb0",))
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
    cells = rc.generate_refs_curated("t", "broken-line", ["home", "leaf", "zap"], 3)
    assert captured["payload"]["style"] == "Broken line"
    assert captured["payload"]["model"] == "recraftv2_vector"
    assert len(cells) == 9
