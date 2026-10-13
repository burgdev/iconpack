"""Semantic pack validation — everything JSON Schema cannot express.

Runs on EVERY pack load (CLI, server, `new`). JSON Schema validates shape;
this validates meaning:

  - style ids resolve against the registry
  - link targets exist, are single-hop, and carry no own state (schema enforces)
  - anchor/reference targets exist
  - the anchor/reference dependency graph is acyclic
  - links on non-mono styles require equal main_color on both icons
  - designer-authored packs (provenance.created_by == "designer") are todo-only:
    no status beyond "todo", no chosen — approval is always the user's action
"""

from __future__ import annotations

from iconpilot.styles import Style


def _target(pack: dict, ref: str) -> tuple[str, str] | None:
    """Resolve 'icon#variant'; returns (icon, variant) or None if missing."""
    icon_id, _, variant_id = ref.partition("#")
    icon = pack["icons"].get(icon_id)
    if icon is None or variant_id not in icon.get("variants", {}):
        return None
    return icon_id, variant_id


def _dependencies(pack: dict) -> list[tuple[str, str, str]]:
    """Edges: (icon, variant, dependency 'icon#variant')."""
    edges: list[tuple[str, str, str]] = []
    for icon_id, icon in pack["icons"].items():
        for variant_id, v in icon.get("variants", {}).items():
            if "link" in v:
                continue  # links are aliases, not drafting dependencies
            for key in ("reference",):
                if key in v:
                    edges.append((icon_id, variant_id, v[key]))
            # anchor: every authored sibling depends on the anchor variant
            if v.get("anchor"):
                for sib_id, sib in icon["variants"].items():
                    if sib_id != variant_id and "link" not in sib:
                        edges.append((icon_id, sib_id, f"{icon_id}#{variant_id}"))
    return edges


def validate_pack(pack: dict, styles: dict[str, Style]) -> list[str]:
    """Return a list of semantic errors (empty = valid)."""
    errors: list[str] = []
    icons = pack["icons"]

    # --- style resolution -------------------------------------------------
    for icon_id, icon in icons.items():
        for variant_id, v in icon.get("variants", {}).items():
            if "style" in v and v["style"] not in styles:
                errors.append(f"{icon_id}#{variant_id}: unknown style '{v['style']}'")

    # --- anchors: at most one per icon ------------------------------------
    for icon_id, icon in icons.items():
        anchors = [k for k, v in icon["variants"].items() if v.get("anchor")]
        if len(anchors) > 1:
            errors.append(
                f"{icon_id}: multiple anchors {anchors} — exactly one form baseline allowed"
            )

    # --- link integrity ----------------------------------------------------
    for icon_id, icon in icons.items():
        for variant_id, v in icon["variants"].items():
            if "link" not in v:
                continue
            target = _target(pack, v["link"])
            if target is None:
                errors.append(
                    f"{icon_id}#{variant_id}: dangling link '{v['link']}' "
                    f"(delete the master, or unlink these first)"
                )
                continue
            t_icon, t_variant = target
            if "link" in icons[t_icon]["variants"][t_variant]:
                errors.append(
                    f"{icon_id}#{variant_id}: link chain — '{v['link']}' is itself a link"
                )
                continue
            # color soundness: linked non-mono styles must share main_color
            t_style_id = icons[t_icon]["variants"][t_variant].get("style")
            t_style = styles.get(t_style_id) if t_style_id else None
            if t_style and t_style.color_mode != "mono":
                a = icons[t_icon].get("main_color")
                b = icon.get("main_color")
                if not (a and b and a.lower() == b.lower()):
                    errors.append(
                        f"{icon_id}#{variant_id}: links to non-mono style "
                        f"'{t_style_id}' but main_color differs — linked paint would be wrong"
                    )

    # --- reference targets + DAG acyclicity -------------------------------
    for icon_id, variant_id, dep in _dependencies(pack):
        if _target(pack, dep) is None:
            errors.append(f"{icon_id}#{variant_id}: reference target '{dep}' does not exist")
        if dep == f"{icon_id}#{variant_id}":
            errors.append(f"{icon_id}#{variant_id}: references itself")

    graph: dict[str, set[str]] = {}
    for icon_id, variant_id, dep in _dependencies(pack):
        graph.setdefault(f"{icon_id}#{variant_id}", set()).add(dep)

    state: dict[str, int] = {}  # 0=visiting, 1=done
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 0
        stack.append(node)
        for dep in graph.get(node, ()):  # missing targets reported above
            if state.get(dep) == 0:
                stack.append(dep)
                return stack[stack.index(dep) :]  # cycle
            if state.get(dep) is None and dep in graph:
                cycle = visit(dep)
                if cycle:
                    return cycle
        stack.pop()
        state[node] = 1
        return None

    for node in graph:
        if state.get(node) is None:
            cycle = visit(node)
            if cycle:
                errors.append("dependency cycle: " + " -> ".join(cycle))

    # --- designer-authored packs are todo-only ------------------------------
    if pack.get("provenance", {}).get("created_by") == "designer":
        for icon_id, icon in icons.items():
            for variant_id, v in icon["variants"].items():
                if "style" not in v:
                    continue
                if v.get("status", "todo") != "todo":
                    errors.append(
                        f"{icon_id}#{variant_id}: designer-created pack must be "
                        f"todo-only (found '{v.get('status')}') — approval is the user's action"
                    )
                if v.get("chosen"):
                    errors.append(
                        f"{icon_id}#{variant_id}: designer-created pack must not "
                        f"contain chosen variants"
                    )

    return errors
