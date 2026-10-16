"""Decision parsing and application — the round state machine.

The agent (or review page) produces decisions; this module is the only
writer of pack state transitions. Compact text grammar (one icon per line):

    hut/mono: a2 keep "thinner roof" · b1 no · more 2
    lake/mono: a1 ok
    peak/color: * no · restart "too abstract"

Items are separated by " · " or ";". `<variant>` defaults to the icon's
single non-approved authored variant, else "mono".

  <cand> ok ["comment"]    approve candidate → icons/<icon>/<variant>.svg, frozen
  <cand> keep ["comment"]  materialize as working copy, stays in_review
  <cand> no ["comment"]    drop candidate (comment recorded)
  <cand> rate <0-10>       rate a candidate; 0 drops it, ratings feed the next draft
  * no                     reject all → variant back to todo
  more <N>                 N more variants next round (recorded as request)
  like <cand> <N>          N variants based on candidate
  restart ["note"]         back to concept; rejected ideas carried forward
  note "text"              icon-level note (comment)

Dependency rule: when an approved variant that others anchor/reference
changes, dependents become "stale".
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from iconpilot.edits import detect_edits
from iconpilot.pack import file_sha256
from iconpilot.styles import Style

_CAND = r"[a-z][a-z0-9-]*"
_ITEM_RE = re.compile(
    rf"""^\s*
    (?:
      (?P<star>\*)\s+no
      |(?P<cand>{_CAND})\s+(?P<action>ok|keep|no)
      |(?P<rate_cand>{_CAND})\s+rate\s+(?P<rate_n>10|[0-9])
      |more\s+(?P<more>\d+)
      |like\s+(?P<like_cand>{_CAND})\s+(?P<like_n>\d+)
      |(?P<restart>restart)
      |(?P<note>note)
    )
    (?:\s+"(?P<comment>[^"]*)")?
    \s*$""",
    re.VERBOSE,
)


_GROUP_RE = re.compile(rf"^(?P<name>{_CAND}(?:/{_CAND})?):\s*(?P<rest>.*)$")


def _split_top(s: str) -> list[str]:
    """Split on '·' or ';' outside double quotes."""
    parts: list[str] = []
    buf: list[str] = []
    in_quote = False
    for ch in s:
        if ch == '"':
            in_quote = not in_quote
            buf.append(ch)
        elif ch in "·;" and not in_quote:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def parse_decision_text(text: str) -> dict[str, dict]:
    """Parse compact text into {icon/variant: {items: [...]}}.

    One icon per line — but multiple icons may share a line when separated
    by '·' or ';': any segment shaped '<name>:' starts a new group.
    """
    groups: dict[str, list[str]] = {}
    order: list[str] = []
    current: str | None = None
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for seg in _split_top(line):
            seg = seg.strip()
            if not seg:
                continue
            m = _GROUP_RE.match(seg)
            if m:
                current = m.group("name")
                if current not in groups:
                    groups[current] = []
                    order.append(current)
                rest = m.group("rest").strip()
                if rest:
                    groups[current].append(rest)
            else:
                if current is None:
                    raise ValueError(
                        f"decision item before any '<icon>:' group: {seg!r} (line: {raw!r})"
                    )
                groups[current].append(seg)
    result: dict[str, dict] = {}
    for name in order:
        items = []
        for part in groups[name]:
            m = _ITEM_RE.match(part)
            if not m:
                # lenient note fallback: notes are free text; inner quotes are common
                if part.startswith("note"):
                    comment = part[4:].strip().strip('"').strip()
                    items.append({"note": "note", "comment": comment})
                    continue
                raise ValueError(f"unparseable decision item: {part!r} (icon: {name})")
            items.append({k: v for k, v in m.groupdict().items() if v is not None})
        result[name] = {"items": items}
    if not result:
        raise ValueError("no decisions found in text")
    return result


def _resolve_variant(
    icon: dict,
    requested: str | None,
    probe_cands: list[str] | None = None,
    pack_dir=None,
    round_id: str = "",
    icon_id: str = "",
) -> str:
    if requested:
        if requested not in icon["variants"] or "style" not in icon["variants"][requested]:
            raise ValueError(f"variant '{requested}' is not an authored variant")
        return requested
    authored = [
        v for v, d in icon["variants"].items() if "style" in d and d.get("status") != "approved"
    ]
    if len(authored) == 1:
        return authored[0]
    # variant unspecified + several open: resolve by where the named
    # candidate actually lives (candidate ids like r1 collide across
    # variant dirs — picking "mono" blindly can approve the wrong one)
    if probe_cands and pack_dir is not None:
        for cand in probe_cands:
            if not cand or cand == "*":
                continue
            homes = [
                v
                for v in authored
                if (pack_dir / ".runs" / round_id / v / icon_id / f"{cand}.svg").is_file()
            ]
            if len(homes) == 1:
                return homes[0]
            if len(homes) > 1:
                raise ValueError(
                    f"candidate '{cand}' exists in several open variants {sorted(homes)} — "
                    f"specify '<icon>/<variant>:'"
                )
    if "mono" in icon["variants"] and "style" in icon["variants"]["mono"]:
        return "mono"
    raise ValueError("multiple candidate variants — specify '<icon>/<variant>:'")


def _find_candidates(
    pack_dir: Path, round_id: str, icon_id: str, variant_id: str
) -> dict[str, Path]:
    d = pack_dir / ".runs" / round_id / variant_id / icon_id
    if not d.is_dir():
        return {}
    return {p.stem: p for p in sorted(d.glob("*.svg"))}


def _dependents_of(pack: dict, icon_id: str, variant_id: str) -> list[str]:
    """All 'icon#variant' keys that anchor/reference the given target."""
    target = f"{icon_id}#{variant_id}"
    out = []
    for iid, icon in pack["icons"].items():
        anchor = [v for v, d in icon["variants"].items() if d.get("anchor")]
        for vid, v in icon["variants"].items():
            if "link" in v:
                continue
            deps = list(v.get("reference") and [v["reference"]] or [])
            if anchor and anchor[0] != vid:
                deps.append(f"{iid}#{anchor[0]}")
            if target in deps and v.get("status") in ("approved", "stale"):
                out.append(f"{iid}#{vid}")
    return out


def _stale_dependents(pack: dict, icon_id: str, variant_id: str, log: list[str]) -> None:
    """Transitive: staling a node stales its dependents too."""
    queue = [f"{icon_id}#{variant_id}"]
    seen: set[str] = set()
    while queue:
        node = queue.pop(0)
        for dep in _dependents_of(pack, *node.split("#")):
            if dep in seen:
                continue
            seen.add(dep)
            di, _, dv = dep.partition("#")
            pack["icons"][di]["variants"][dv]["status"] = "stale"
            log.append(f"{dep}: stale (dependency {node} changed)")
            queue.append(dep)


def _apply_hand_edit_staleness(pack_dir: Path, pack: dict, log: list[str]) -> None:
    """Hand-edited originals need re-review; their dependents go stale."""
    for edit in detect_edits(pack_dir, pack):
        iid, vid = edit["icon"], edit["variant"]
        v = pack["icons"][iid]["variants"][vid]
        if v.get("status") == "approved":
            v["status"] = "in_review"
            log.append(f"{iid}#{vid}: icons file hand-edited since approval → in_review")
            _stale_dependents(pack, iid, vid, log)


def apply_decisions(
    pack_dir: Path,
    pack: dict,
    styles: dict[str, Style],
    decisions: dict,
    round_id: str,
    source: str,
    instructions: str | None = None,
) -> list[str]:
    """Apply parsed decisions to pack.json + icons/. Returns a change log."""
    log: list[str] = []
    icons_dir = pack_dir / "icons"
    icons_dir.mkdir(exist_ok=True)
    _apply_hand_edit_staleness(pack_dir, pack, log)

    def comment(v: dict, text: str) -> None:
        v.setdefault("comments", []).append({"round": round_id, "text": text})
        log.append(f"comment: {text}")

    for name, payload in decisions.items():
        icon_id, _, req_variant = name.partition("/")
        icon = pack["icons"].get(icon_id)
        if icon is None:
            raise ValueError(f"unknown icon '{icon_id}'")
        if req_variant and (
            req_variant not in icon["variants"] or "style" not in icon["variants"][req_variant]
        ):
            # self-heal: orphan decision (variant not authored — stale run
            # data) — skip visibly instead of blocking the whole apply
            log.append(f"skipped {icon_id}/{req_variant}: variant not authored")
            continue
        probe = [
            str(it.get("cand") or it.get("rate_cand") or "") for it in payload.get("items", [])
        ]
        variant_id = _resolve_variant(
            icon,
            req_variant or None,
            probe_cands=probe,
            pack_dir=pack_dir,
            round_id=round_id,
            icon_id=icon_id,
        )
        variant = icon["variants"][variant_id]
        cands = _find_candidates(pack_dir, round_id, icon_id, variant_id)
        for item in payload["items"]:
            comment_text = item.get("comment")
            if "star" in item:
                variant["status"] = "todo"
                log.append(f"{icon_id}#{variant_id}: all rejected → todo")
                if comment_text:
                    comment(variant, comment_text)
                    variant.setdefault("rejected_ideas", []).append(comment_text)
            elif "rate_cand" in item:
                cand = item["rate_cand"]
                n = int(item["rate_n"])
                if cand not in cands:
                    raise ValueError(
                        f"{icon_id}#{variant_id}: rate candidate '{cand}' not in run "
                        f"{round_id} (found: {sorted(cands) or 'none'})"
                    )
                if n == 0:
                    log.append(f"{icon_id}#{variant_id}: dropped {cand} (rated 0)")
                else:
                    comment(variant, f"[{cand}] rated {n}/10")
                    log.append(f"{icon_id}#{variant_id}: {cand} rated {n}/10")
            elif "action" in item:
                cand = item["cand"]
                action = item["action"]
                if cand not in cands:
                    raise ValueError(
                        f"{icon_id}#{variant_id}: candidate '{cand}' not in run "
                        f"{round_id} (found: {sorted(cands) or 'none'})"
                    )
                dest = icons_dir / icon_id / f"{variant_id}.svg"
                if action == "ok":
                    prev = variant.get("chosen")
                    changed = prev != {"run": round_id, "variant": cand}
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(cands[cand], dest)
                    variant["status"] = "approved"
                    variant["chosen"] = {"run": round_id, "variant": cand}
                    variant["content_hash"] = file_sha256(dest)
                    log.append(
                        f"{icon_id}#{variant_id}: approved {cand} → {dest.relative_to(pack_dir)}"
                    )
                    if changed:
                        _stale_dependents(pack, icon_id, variant_id, log)
                elif action == "keep":
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(cands[cand], dest)
                    variant["status"] = "in_review"
                    variant["content_hash"] = file_sha256(dest)
                    log.append(
                        f"{icon_id}#{variant_id}: kept {cand} → {dest.relative_to(pack_dir)} (working copy)"
                    )
                elif action == "no":
                    log.append(f"{icon_id}#{variant_id}: dropped candidate {cand}")
                if comment_text:
                    comment(variant, f"[{cand}] {comment_text}")
            elif "more" in item:
                variant["request"] = {"type": "more", "n": int(item["more"])}
                log.append(f"{icon_id}#{variant_id}: requested {item['more']} more")
            elif "like_cand" in item:
                variant["request"] = {
                    "type": "like",
                    "n": int(item["like_n"]),
                    "from": item["like_cand"],
                }
                log.append(
                    f"{icon_id}#{variant_id}: requested {item['like_n']} like {item['like_cand']}"
                )
            elif "restart" in item or "note" in item:
                if "restart" in item:
                    variant["status"] = "todo"
                    variant.pop("chosen", None)
                    log.append(f"{icon_id}#{variant_id}: restart")
                    if comment_text:
                        variant.setdefault("rejected_ideas", []).append(comment_text)
                if comment_text:
                    comment(variant, comment_text)

    # never persist a pack we just broke
    from iconpilot.pack import revalidate as _revalidate

    _, errors = _revalidate(pack)
    if errors:
        raise ValueError("decisions would produce an invalid pack:\n  - " + "\n  - ".join(errors))

    # persist: decisions echo + pack.json (atomic, rev bump)
    runs = pack_dir / ".runs" / round_id
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "decisions.json").write_text(
        json.dumps(
            {
                "round": round_id,
                "decided_at": datetime.now(UTC).isoformat(),
                "source": source,
                "instructions": instructions,
                "icons": decisions,
            },
            indent=2,
        )
    )
    from iconpilot.pack import write_pack_atomic

    write_pack_atomic(pack_dir, pack)
    return log
