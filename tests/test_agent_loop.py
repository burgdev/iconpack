"""Agent-loop plumbing tests: decide state machine, context, batch gate, sheet."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from iconpilot.cli import app
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
        ("hut", "a1", VALID_SVG), ("hut", "a2", OTHER_SVG),
        ("selfhut", "a1", VALID_SVG),
    ]:
        p = d / ".runs" / "r001" / "mono" / icon
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{cand}.svg").write_text(svg)
    return d


# --- decide -------------------------------------------------------------------

def test_parse_two_icons_one_line() -> None:
    from iconpilot.decide import parse_decision_text

    d = parse_decision_text(
        'hut/mono: a1 ok · selfhut/mono: a1 keep "cutlery next round" · more 2'
    )
    assert list(d) == ["hut/mono", "selfhut/mono"]
    assert d["hut/mono"]["items"] == [{"cand": "a1", "action": "ok"}]
    assert d["selfhut/mono"]["items"] == [
        {"cand": "a1", "action": "keep", "comment": "cutlery next round"},
        {"more": "2"},
    ]


def test_decide_approve_keep_reject(workpack: Path) -> None:
    r = runner.invoke(app, [
        "decide", str(workpack), "--round", "r001", "--text",
        'hut/mono: a1 keep "thinner roof" · a2 no · more 2',
    ])
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

    r = runner.invoke(app, [
        "decide", str(workpack), "--round", "r001", "--text", "hut/mono: a2 ok",
    ])
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["hut"]["variants"]["mono"]["status"] == "approved"
    assert out["icons"]["hut"]["variants"]["mono"]["chosen"] == {"run": "r001", "variant": "a2"}
    assert out["icons"]["selfhut"]["variants"]["mono"]["status"] == "stale"


def test_decide_star_reject_resets(workpack: Path) -> None:
    r = runner.invoke(app, [
        "decide", str(workpack), "--round", "r001", "--text", 'selfhut/mono: * no',
    ])
    assert r.exit_code == 0, r.output
    out = json.loads((workpack / "pack.json").read_text())
    assert out["icons"]["selfhut"]["variants"]["mono"]["status"] == "todo"


def test_decide_unknown_candidate_rejected(workpack: Path) -> None:
    r = runner.invoke(app, [
        "decide", str(workpack), "--round", "r001", "--text", "hut/mono: z9 ok",
    ])
    assert r.exit_code == 2


def test_decide_revalidates_pack(workpack: Path) -> None:
    r = runner.invoke(app, [
        "decide", str(workpack), "--round", "r001", "--text", "hut/mono: a1 ok",
    ])
    assert r.exit_code == 0
    # resulting pack must still pass full validation
    from iconpilot.pack import load_pack
    load_pack(workpack / "pack.json")


# --- context ------------------------------------------------------------------

def test_context_markdown(workpack: Path) -> None:
    # approve hut#mono first so it exists as a reference target
    runner.invoke(app, ["decide", str(workpack), "--round", "r001", "--text", "hut/mono: a1 ok"])
    r = runner.invoke(app, [
        "context", str(workpack), "--icon", "selfhut", "--variant", "mono",
    ])
    assert r.exit_code == 0, r.output
    assert "Self-catering hut" in r.output
    assert "Reference (visually match)" in r.output
    assert "≤ 40 nodes" in r.output


def test_context_json_has_gate_contract(workpack: Path) -> None:
    r = runner.invoke(app, [
        "context", str(workpack), "--icon", "hut", "--variant", "mono", "--json",
    ])
    assert r.exit_code == 0
    ctx = json.loads(r.output)
    assert ctx["gate"]["max_nodes"] == 40
    assert ctx["style"]["id"] == "mono-line"


# --- batch gate -----------------------------------------------------------------

def test_batch_gate_writes_reports(workpack: Path) -> None:
    r = runner.invoke(app, ["gate", str(workpack / ".runs" / "r001"), "--pack", str(workpack)])
    assert r.exit_code == 0, r.output
    report = json.loads(
        (workpack / ".runs" / "r001" / "mono" / "hut" / "a1.gate.json").read_text()
    )
    assert report["passed"] is True


def test_batch_gate_fails_bad_svg(workpack: Path) -> None:
    bad = workpack / ".runs" / "r001" / "mono" / "hut" / "b1.svg"
    bad.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><text>x</text></svg>')
    r = runner.invoke(app, ["gate", str(workpack / ".runs" / "r001"), "--pack", str(workpack)])
    assert r.exit_code == 1
    assert "batch: 3 passed, 1 failed" in r.output


# --- contact sheet ---------------------------------------------------------------

def test_contact_sheet(workpack: Path) -> None:
    r = runner.invoke(app, [
        "contact-sheet", str(workpack / ".runs" / "r001"), "--pack", str(workpack),
    ])
    assert r.exit_code == 0, r.output
    sheet = workpack / ".runs" / "r001" / "contact-sheet.png"
    assert sheet.is_file()
    assert sheet.stat().st_size > 500
