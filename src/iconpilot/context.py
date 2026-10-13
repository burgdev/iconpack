"""Prompt-context emitter — the deterministic contract between pack state
and the agent doing the drafting.

The CLI never calls models; it produces exactly what the drafter needs to
know (brief, style, gate thresholds, anchor/reference SVGs, feedback) and
what the gate will enforce. Markdown for humans/agents, --json for tooling.
"""

from __future__ import annotations

from pathlib import Path

from iconpilot.styles import Style


def build_context(
    pack_dir: Path,
    pack: dict,
    styles: dict[str, Style],
    icon_id: str,
    variant_id: str,
) -> dict:
    icon = pack["icons"][icon_id]
    variant = icon["variants"][variant_id]
    if "link" in variant:
        raise ValueError(f"{icon_id}#{variant_id} is a link — draft its master instead")
    style = styles[variant["style"]]
    spec = pack.get("spec", {})

    def svg_of(iid: str, vid: str) -> str | None:
        f = pack_dir / "icons" / iid / f"{vid}.svg"
        return f.read_text() if f.is_file() else None

    anchor_id = next((v for v, d in icon["variants"].items() if d.get("anchor")), None)
    brief = variant.get("brief") or icon.get("brief") or ""
    prompt = variant.get("prompt") or icon.get("prompt")

    ctx: dict = {
        "icon": icon_id,
        "variant": variant_id,
        "status": variant.get("status", "todo"),
        "brief": brief,
        "style": {
            "id": style.id,
            "label": style.label,
            "construction": style.construction,
            "color_mode": style.color_mode,
            "stroke": style.stroke,
            "fill": style.fill,
            "style_words": list(style.style_words),
            "avoid": list(style.avoid),
        },
        "gate": {
            "viewBox": f"0 0 {style.size} {style.size}" if style.size else spec.get("viewBox"),
            "live_area_padding": spec.get("live_area", {}).get("padding", 0),
            "allowed_elements": spec.get("allowed_elements"),
            "precision": spec.get("precision"),
            "max_nodes": style.max_nodes,
            "min_gap": style.min_gap,
            "render_sizes": list(style.render_sizes),
        },
        "rules": pack.get("rules", []),
    }
    if icon.get("main_color"):
        ctx["main_color"] = icon["main_color"]
    if style.palette:
        ctx["palette"] = list(style.palette)
    dm = pack.get("inherits", {}).get("design_md")
    if dm:
        ctx["design_md"] = dm
    if prompt:
        ctx["prompt"] = prompt
    if anchor_id and anchor_id != variant_id:
        ctx["anchor_svg"] = svg_of(icon_id, anchor_id)
    if variant.get("reference"):
        ref = variant["reference"]
        ri, _, rv = ref.partition("#")
        ctx["reference_svg"] = svg_of(ri, rv)
    if variant.get("comments"):
        ctx["comments"] = variant["comments"]
    if variant.get("rejected_ideas"):
        ctx["rejected_ideas"] = variant["rejected_ideas"]
    if variant.get("request"):
        ctx["request"] = variant["request"]
    if variant.get("content_hash"):
        f = pack_dir / "icons" / icon_id / f"{variant_id}.svg"
        if f.is_file():
            from iconpilot.pack import file_sha256

            if file_sha256(f) != variant["content_hash"]:
                ctx["hand_edited"] = True
    ctx = {k: v for k, v in ctx.items() if v not in (None, [], {})}
    return ctx


def render_markdown(ctx: dict) -> str:
    lines = [f"# {ctx['icon']}#{ctx['variant']} — drafting context", ""]
    lines += [f"**Brief:** {ctx['brief']}", ""]
    if "prompt" in ctx:
        lines += [f"**Composition hints:** {ctx['prompt']}", ""]
    s = ctx["style"]
    desc = f"{s['label']} — {s['construction']}/{s['color_mode']}"
    if s.get("stroke"):
        desc += f", stroke {s['stroke'].get('width')}px {s['stroke'].get('linecap')}"
    if s.get("fill"):
        desc += f", fill {s['fill']}"
    lines += [f"**Style:** {desc}", ""]
    if s["style_words"]:
        lines += ["Style vocabulary: " + ", ".join(s["style_words"])]
    if s["avoid"]:
        lines += ["Avoid: " + ", ".join(s["avoid"])]
    lines += [""]
    g = ctx["gate"]
    lines += [
        "**The gate enforces (deterministic, your SVG must pass):**",
        f"- viewBox `{g['viewBox']}`, live area padding {g['live_area_padding']} (true bbox incl. beziers/shapes)",
        f"- elements: {', '.join(g['allowed_elements'] or [])}",
        f"- ≤ {g['max_nodes']} nodes; stroke/fill/width/caps per style",
        f"- no near-miss gaps below {g['min_gap']}; coordinates snapped to the {g['precision']} grid",
        f"- renders at {g['render_sizes']}px, no inline styles, no transforms, no ids",
        "",
    ]
    if "main_color" in ctx:
        lines += [f"**Main color:** `{ctx['main_color']}`", ""]
    if "palette" in ctx:
        lines += [f"**Palette (only these colors):** {', '.join(ctx['palette'])}", ""]
    if "design_md" in ctx:
        lines += [f"**Design system:** read `{ctx['design_md']}` before drafting.", ""]
    for key, title in (
        ("anchor_svg", "Anchor (family form baseline)"),
        ("reference_svg", "Reference (visually match)"),
    ):
        if key in ctx:
            lines += [f"**{title}:**", "", "```svg", ctx[key].rstrip(), "```", ""]
    if "comments" in ctx:
        lines += ["**Feedback:**"]
        lines += [f"- [{c['round']}] {c['text']}" for c in ctx["comments"]] + [""]
    if "hand_edited" in ctx:
        note = (
            "**Note:** the current `icons/` file was **hand-edited after the last "
            "decision** — your draft refines from that edited file."
        )
        lines += [note, ""]
    if "rejected_ideas" in ctx:
        lines += ["**Rejected ideas (do not repeat):**", ", ".join(ctx["rejected_ideas"]), ""]
    if "request" in ctx:
        lines += [f"**User request:** `{ctx['request']}`", ""]
    return "\n".join(lines)
