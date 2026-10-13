"""Wait for the user: block until pack state changes (rev bump).

Closes the agent loop — after handing the review page to the user, the agent
runs `iconpilot wait <pack>`; it returns as soon as decisions are applied
(or briefs/styles edited), so the loop continues automatically.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def current_rev(pack_dir: Path) -> int:
    try:
        return json.loads((pack_dir / "pack.json").read_text()).get("rev", 0)
    except (OSError, ValueError):
        return 0


def latest_decisions_summary(pack_dir: Path) -> str:
    runs = pack_dir / ".runs"
    if not runs.is_dir():
        return ""
    for run in sorted((p for p in runs.glob("r*") if p.is_dir()), reverse=True):
        f = run / "decisions.json"
        if f.is_file():
            try:
                data = json.loads(f.read_text())
            except ValueError:
                continue
            icons = data.get("icons", {})
            if icons:
                return f"{run.name}: " + ", ".join(sorted(icons)) + " decided"
    return ""


def wait_for_change(
    pack_dir: Path,
    timeout: float = 3600.0,
    interval: float = 2.0,
    start_rev: int | None = None,
) -> dict:
    """Block until pack.json rev changes. Returns {"rev", "changed", "summary"}."""
    baseline = start_rev if start_rev is not None else current_rev(pack_dir)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rev = current_rev(pack_dir)
        if rev != baseline:
            return {
                "rev": rev,
                "changed": True,
                "summary": latest_decisions_summary(pack_dir),
            }
        time.sleep(interval)
    return {"rev": baseline, "changed": False, "summary": ""}
