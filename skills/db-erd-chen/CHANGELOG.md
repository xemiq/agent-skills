# Changelog: db-erd-chen

Semantic versioning: MAJOR = output contract or breaking model-schema change; MINOR = new
capabilities or checks; PATCH = fixes.

## 0.1.0 — 2026-11-10 (initial public pre-release)
- Published as `db-erd-chen` in https://github.com/xemiq/agent-skills under Apache-2.0.
- First release: SKILL.md (12 components), team guide copy (`references/erd-guide.md`), source
  mapping, model schema, deterministic renderer, validator, worked example (Task Tracker), and
  regression tests.
- Hardened before release after an adversarial review (31 findings: 14 on the spec, 17 on the scripts).
  Changes: full-notation draft confirmation, a min/max mapping table, B10 (single vs multi-valued),
  per-class delegation defaults, no file writes in non-interactive runs, composite keys, the `omitted`
  field, type-safe model checks, empty-area / repeated-ternary-entity rejection, weak-owned-by-weak
  support, collision-aware diamond placement, BFS auto-grid, gap-free versioning, UTF-8 BOM support,
  summary escaping, validator regex false positives and negatives, key checks on attribute-less
  entities, Overview cardinality consistency, identifying owner checks, diagrams.net edge labels and
  groups, and numeric waypoint checks.
