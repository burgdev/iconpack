"""Schema tests: the documented example pack must validate."""

from __future__ import annotations

import json
from importlib import resources

import jsonschema

EXAMPLE_PACK = {
    "schema": 1,
    "name": "outdoor-poi",
    "version": "0.1.0",
    "inherits": {"design_md": None},
    "spec": {
        "viewBox": "0 0 24 24",
        "live_area": {"padding": 2},
        "stroke": {"width": 2, "linecap": "round", "linejoin": "round"},
        "corner_radius": 2,
        "fill": "none",
        "color": "currentColor",
        "allowed_elements": [
            "path", "circle", "rect", "line", "polyline", "polygon", "ellipse",
        ],
        "precision": 0.5,
        "max_nodes": 40,
        "min_gap": 1.5,
    },
    "style": {
        "description": "Calm, geometric, readable at 16px.",
        "anti_references": ["skeuomorphic detail", "hairline strokes"],
    },
    "rules": ["Door gap at least 2 units"],
    "schedule": [4, 2, 1],
    "anchors": ["hut"],
    "icons": {
        "hut": {
            "brief": "Alpine hut: steep roof, small door, no chimney",
            "tags": ["building", "shelter"],
            "status": "approved",
            "chosen": {"run": "r002", "variant": "a1"},
            "comments": [{"round": "r001", "text": "thinner roof"}],
            "rejected_ideas": ["house with flag"],
        }
    },
}


def _schema() -> dict:
    text = (
        resources.files("iconpilot.schema").joinpath("pack.schema.json").read_text()
    )
    return json.loads(text)


def test_example_pack_validates() -> None:
    jsonschema.validate(EXAMPLE_PACK, _schema())


def test_bad_status_rejected() -> None:
    bad = json.loads(json.dumps(EXAMPLE_PACK))
    bad["icons"]["hut"]["status"] = "done"
    try:
        jsonschema.validate(bad, _schema())
    except jsonschema.ValidationError:
        return
    raise AssertionError("invalid status must be rejected")


def test_missing_spec_rejected() -> None:
    bad = json.loads(json.dumps(EXAMPLE_PACK))
    del bad["spec"]
    try:
        jsonschema.validate(bad, _schema())
    except jsonschema.ValidationError:
        return
    raise AssertionError("missing spec must be rejected")
