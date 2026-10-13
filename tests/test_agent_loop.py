"""Agent-loop plumbing tests: decide state machine, context, batch gate, sheet."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from iconpilot.cli import app
from iconpilot.gate.run import run_gate
from iconpilot.pack import load_pack
from tests.test_pack_schema import VALID_SVG, example_pack

runner = CliRunner()

OTHER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 5 L19 19 M19 5 L5 19"/></svg>'
)


@pytest.fixture
def workpack(tmp_path: Path) -> Path:
    d = tmp_path / "outdoor-poi"
    d.mkdir()
    (d / "pack.json").write_text(json.dumps(example_pack()))
    # run r001 with candidates for hut#mono and selfhut#mono
    for icon, cand, svg in [
        ("hut", "a1", VALID_SVG),
        ("hut", "a2", OTHER_SVG),
        ("selfhut", "a1", VALID_SVG),
    ]:
        p = d / ".runs" / "r001" / "mono" / icon
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{cand}.svg").write_text(svg)
    return d


# --- decide -------------------------------------------------------------------


def test_decide_restart_and_note_are_applied(workpack: Path) -> None:
    # regression: bare regex alternatives parsed to empty dicts — silent no-op (0.0.1)
    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            'hut/mono: a1 ok · selfhut/mono: restart "cutlery concept wrong"',
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    hut = out["icons"]["hut"]["variants"]["mono"]
    selfhut = out["icons"]["selfhut"]["variants"]["mono"]
    assert hut["status"] == "approved"
    assert selfhut["status"] == "todo"  # restart actually applied
    assert "chosen" not in selfhut
    assert any("cutlery concept wrong" in c["text"] for c in selfhut["comments"])

    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            'hut/mono: note "revisit door proportion"',
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    hut = out["icons"]["hut"]["variants"]["mono"]
    assert any("revisit door proportion" in c["text"] for c in hut["comments"])
    assert hut["status"] == "approved"  # note alone must not change status


def test_decide_like_request(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            "hut/mono: like a1 3",
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["hut"]["variants"]["mono"]["request"] == {
        "type": "like",
        "n": 3,
        "from": "a1",
    }


def test_parse_two_icons_one_line() -> None:
    from iconpilot.decide import parse_decision_text

    d = parse_decision_text('hut/mono: a1 ok · selfhut/mono: a1 keep "cutlery next round" · more 2')
    assert list(d) == ["hut/mono", "selfhut/mono"]
    assert d["hut/mono"]["items"] == [{"cand": "a1", "action": "ok"}]
    assert d["selfhut/mono"]["items"] == [
        {"cand": "a1", "action": "keep", "comment": "cutlery next round"},
        {"more": "2"},
    ]


def test_decide_approve_keep_reject(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            'hut/mono: a1 keep "thinner roof" · a2 no · more 2',
        ],
    )
    assert r.exit_code == 0, r.output
    kept = workpack / "icons" / "hut" / "mono.svg"
    assert kept.read_text() == VALID_SVG
    pack = json.loads((workpack / "pack.json").read_text())
    v = pack["icons"]["hut"]["variants"]["mono"]
    assert v["status"] == "in_review"
    assert v["request"] == {"type": "more", "n": 2}
    assert any("thinner roof" in c["text"] for c in v["comments"])
    assert (workpack / ".runs" / "r001" / "decisions.json").is_file()


def test_decide_ok_marks_dependents_stale(workpack: Path) -> None:
    # hut/mono is referenced by selfhut#mono; approving a NEW hut#mono
    # candidate must stale the previously-approved dependent.
    pack = json.loads((workpack / "pack.json").read_text())
    pack["icons"]["selfhut"]["variants"]["mono"]["status"] = "approved"
    (workpack / "pack.json").write_text(json.dumps(pack))

    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            "hut/mono: a2 ok",
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["hut"]["variants"]["mono"]["status"] == "approved"
    assert out["icons"]["hut"]["variants"]["mono"]["chosen"] == {"run": "r001", "variant": "a2"}
    assert out["icons"]["selfhut"]["variants"]["mono"]["status"] == "stale"


def test_decide_star_reject_resets(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            "selfhut/mono: * no",
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["selfhut"]["variants"]["mono"]["status"] == "todo"


def test_decide_unknown_candidate_rejected(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            "hut/mono: z9 ok",
        ],
    )
    assert r.exit_code == 2


def test_decide_revalidates_pack(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            "hut/mono: a1 ok",
        ],
    )
    assert r.exit_code == 0
    # resulting pack must still pass full validation
    from iconpilot.pack import load_pack

    load_pack(workpack / "pack.json")


# --- context ------------------------------------------------------------------


def test_context_markdown(workpack: Path) -> None:
    # approve hut#mono first so it exists as a reference target
    runner.invoke(app, ["decide", str(workpack), "--round", "r001", "--text", "hut/mono: a1 ok"])
    r = runner.invoke(
        app,
        [
            "context",
            str(workpack),
            "--icon",
            "selfhut",
            "--variant",
            "mono",
        ],
    )
    assert r.exit_code == 0, r.output
    assert "Self-catering hut" in r.output
    assert "Reference (visually match)" in r.output
    assert "≤ 40 nodes" in r.output


def test_context_json_has_gate_contract(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "context",
            str(workpack),
            "--icon",
            "hut",
            "--variant",
            "mono",
            "--json",
        ],
    )
    assert r.exit_code == 0
    ctx = json.loads(r.output)
    assert ctx["gate"]["max_nodes"] == 40
    assert ctx["style"]["id"] == "mono-line"


# --- batch gate -----------------------------------------------------------------


def test_batch_gate_writes_reports(workpack: Path) -> None:
    r = runner.invoke(app, ["gate", str(workpack / ".runs" / "r001"), "--pack", str(workpack)])
    assert r.exit_code == 0, r.output
    report = json.loads((workpack / ".runs" / "r001" / "mono" / "hut" / "a1.gate.json").read_text())
    assert report["passed"] is True


def test_batch_gate_fails_bad_svg(workpack: Path) -> None:
    bad = workpack / ".runs" / "r001" / "mono" / "hut" / "b1.svg"
    bad.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><text>x</text></svg>'
    )
    r = runner.invoke(app, ["gate", str(workpack / ".runs" / "r001"), "--pack", str(workpack)])
    assert r.exit_code == 1
    assert "batch: 3 passed, 1 failed" in r.output


# --- contact sheet ---------------------------------------------------------------


def test_contact_sheet(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "contact-sheet",
            str(workpack / ".runs" / "r001"),
            "--pack",
            str(workpack),
        ],
    )
    assert r.exit_code == 0, r.output
    sheet = workpack / ".runs" / "r001" / "contact-sheet.png"
    assert sheet.is_file()
    assert sheet.stat().st_size > 500


# --- review-fix regressions ---------------------------------------------------

BEZIER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 12 C4 -6 20 -6 20 12"/></svg>'
)

CIRCLE_OUT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="23" r="8"/></svg>'
)


def test_gate_catches_bezier_overshoot(workpack: Path) -> None:
    # regression: segment start/end-only bbox missed bezier bulges (false PASS)
    svg = workpack / ".runs" / "r001" / "mono" / "hut" / "bez.svg"
    svg.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text(BEZIER_SVG)
    pack, styles = load_pack(workpack / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert any("live area" in e for e in report.errors), report.checks


def test_gate_catches_outside_circle(workpack: Path) -> None:
    # regression: shapes contributed zero geometry (false PASS)
    svg = workpack / ".runs" / "r001" / "mono" / "hut" / "circ.svg"
    svg.write_text(CIRCLE_OUT_SVG)
    pack, styles = load_pack(workpack / "pack.json")
    report = run_gate(svg, pack, styles["mono-line"])
    assert any("live area" in e for e in report.errors)


def test_staleness_is_transitive(workpack: Path) -> None:
    # lake/mono references hut/mono; peak/mono references lake/mono
    pack = json.loads((workpack / "pack.json").read_text())
    pack["icons"]["lake"] = {
        "brief": "lake",
        "variants": {
            "mono": {
                "style": "mono-line",
                "status": "approved",
                "reference": "hut#mono",
                "chosen": {"run": "r000", "variant": "x"},
            }
        },
    }
    pack["icons"]["peak"] = {
        "brief": "peak",
        "variants": {
            "mono": {
                "style": "mono-line",
                "status": "approved",
                "reference": "lake#mono",
                "chosen": {"run": "r000", "variant": "x"},
            }
        },
    }
    (workpack / "pack.json").write_text(json.dumps(pack))

    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            "hut/mono: a2 ok",
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["lake"]["variants"]["mono"]["status"] == "stale"
    assert out["icons"]["peak"]["variants"]["mono"]["status"] == "stale"  # transitive


def test_page_field_ids_match_saveicon() -> None:
    # regression: Save read main_color-<id> but the input was color-<id>
    import re as _re

    from iconpilot.server.page import PAGE

    fields = _re.search(r"for \(const f of \[([^\]]+)\]", PAGE).group(1)
    names = [f.strip().strip("'\"") for f in fields.split(",")]
    assert "main_color" in names
    for n in names:
        assert f'id="{n}-$' in PAGE, f"page has no input id {n}-<icon>"


def test_hand_edit_stales_dependents(workpack: Path) -> None:
    # approve hut/mono, then hand-edit its file → decide flags + stales chain
    runner.invoke(app, ["decide", str(workpack), "--round", "r001", "--text", "hut/mono: a1 ok"])
    hut_mono = workpack / "icons" / "hut" / "mono.svg"
    original = hut_mono.read_text()
    hut_mono.write_text(original.replace("M10 20", "M11 20"))

    # selfhut/mono references hut#mono → must go stale via the edit
    pack = json.loads((workpack / "pack.json").read_text())
    pack["icons"]["selfhut"]["variants"]["mono"]["status"] = "approved"
    pack["icons"]["selfhut"]["variants"]["mono"]["chosen"] = {"run": "r000", "variant": "x"}
    (workpack / "pack.json").write_text(json.dumps(pack))

    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            'selfhut/mono: a1 keep "pinning base"',
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["hut"]["variants"]["mono"]["status"] == "in_review"  # edit flagged
    assert out["icons"]["selfhut"]["variants"]["mono"]["status"] == "in_review"  # own decision


def test_hand_edit_flags_reference_chain(workpack: Path) -> None:
    runner.invoke(app, ["decide", str(workpack), "--round", "r001", "--text", "hut/mono: a1 ok"])
    hut_mono = workpack / "icons" / "hut" / "mono.svg"
    hut_mono.write_text(hut_mono.read_text().replace("M10 20", "M11 20"))
    pack = json.loads((workpack / "pack.json").read_text())
    pack["icons"]["selfhut"]["variants"]["mono"]["status"] = "approved"
    pack["icons"]["selfhut"]["variants"]["mono"]["chosen"] = {"run": "r000", "variant": "x"}
    (workpack / "pack.json").write_text(json.dumps(pack))
    # any decision run applies edit-staleness first
    runner.invoke(app, ["decide", str(workpack), "--round", "r001", "--text", "hut/mono: a1 ok"])
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["selfhut"]["variants"]["mono"]["status"] == "stale"


def test_status_reports_edited(workpack: Path) -> None:
    runner.invoke(app, ["decide", str(workpack), "--round", "r001", "--text", "hut/mono: a1 ok"])
    f = workpack / "icons" / "hut" / "mono.svg"
    f.write_text(f.read_text().replace("M10 20", "M11 20"))
    r = runner.invoke(app, ["status", str(workpack)])
    assert "✎edited" in r.output


def test_rejected_ideas_recorded(workpack: Path) -> None:
    r = runner.invoke(
        app,
        [
            "decide",
            str(workpack),
            "--round",
            "r001",
            "--text",
            'selfhut/mono: restart "cutlery next to door"',
        ],
    )
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    ideas = out["icons"]["selfhut"]["variants"]["mono"].get("rejected_ideas", [])
    assert any("cutlery next to door" in i for i in ideas)


def test_new_author_designer(tmp_path: Path) -> None:
    d = tmp_path / "designed"
    r = runner.invoke(app, ["new", str(d), "--author", "designer"])
    assert r.exit_code == 0, r.output
    pack = json.loads((d / "pack.json").read_text())
    assert pack["provenance"]["created_by"] == "designer"
    assert "schedule" not in pack
    r = runner.invoke(app, ["check", str(d)])
    assert r.exit_code == 0
    r = runner.invoke(app, ["new", str(tmp_path / "x"), "--author", "llm"])
    assert r.exit_code == 2
