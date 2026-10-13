"""The public API is importable from the package root and matches __all__."""

from __future__ import annotations

import iconpilot


def test_public_api_surface() -> None:
    for name in iconpilot.__all__:
        assert hasattr(iconpilot, name), f"{name} missing from package root"
        assert getattr(iconpilot, name) is not None


def test_all_covers_expected_core() -> None:
    core = {
        "load_pack",
        "run_gate",
        "collect_exportables",
        "export_maplibre",
        "resolve_styles",
        "parse_decision_text",
        "build_context",
    }
    assert core <= set(iconpilot.__all__)


def test_library_roundtrip(tmp_path) -> None:
    """The documented library pattern works from the package root alone."""
    import json

    from iconpilot import load_pack

    pack = {
        "schema": 2,
        "name": "libtest",
        "version": "0.1.0",
        "spec": {"viewBox": "0 0 24 24", "allowed_elements": ["path"]},
        "icons": {
            "x": {"brief": "cross", "variants": {"mono": {"style": "mono-line", "status": "todo"}}}
        },
    }
    (tmp_path / "pack.json").write_text(json.dumps(pack))
    loaded, styles = load_pack(tmp_path / "pack.json")
    assert loaded["name"] == "libtest"
    assert "mono-line" in styles
