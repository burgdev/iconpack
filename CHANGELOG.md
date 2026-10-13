# Changelog

## 0.0.2 (unreleased)

- Fix decide writing pack.json without the pack lock (lost-update race with the review server)
- Fix review page Save button (field id mismatch made every save throw)
- Gate: true geometry — bezier control points via segment.bbox(), shape bboxes (circle/ellipse/rect/line/polyline/polygon) counted, variable shadowing fixed
- Gate: lint stroke-linecap/linejoin against the style when present
- Staleness is now transitive across the dependency chain
- decide revalidates the pack before persisting (no broken state on disk)
- Drafting context no longer advertises unenforced checks (min_gap/precision are style targets)

## 0.0.1

- Initial scaffold: pack schema v2, style registry, semantic validator, deterministic gate,
  agent loop (context/gate/contact-sheet/decide), review server, exports, skill, docs, CI
