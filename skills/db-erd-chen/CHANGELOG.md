# Changelog: db-erd-chen

Semantic versioning: MAJOR = output contract or breaking model-schema change; MINOR = new
capabilities or checks; PATCH = fixes.

## 0.2.0 — 2026-11-11
- New: diagram language. English stays the default. When the user writes in another language, the
  agent asks which language to use for names and notes (clarification N6). The model's `language`
  field records the answer. Spanish (`es`) translates the title, page names, legend, summary and
  note prefixes (`Restricción:` / `Regla:`). Other languages fall back to English for these texts,
  with a warning.
- Validator: accepts translated titles, Overview names and note prefixes; detects Spanish-style
  foreign-key attributes (`ID de Dueño`); its Title Case check ignores short connecting words such
  as "de" or "of".
- Clarification: a test run with v0.1.1 still drafted `total (default)`. The rule is now one of the
  non-negotiable rules at the top of SKILL.md, and the draft gets a self-check step before it is
  sent (no `total (default)`, unknown maximums asked, species-like attributes asked, language
  question for requests not in English).
- Guide: new §2.9 "Diagram language"; naming rules now refer to the diagram language.
- SKILL.md §12 details moved to `references/maintenance.md`, to keep SKILL.md under 500 lines.

## 0.1.1 — 2026-11-11
- Clarification: a `(default)` participation is always partial, never total (found in a test run where
  the draft proposed "total (default)" for unstated minimums).
- Clarification: *Species*, *Type*, *Status* added to the entity-or-attribute (B3) examples.
- Renderer: the legend box height now fits its text instead of a fixed 320 px.

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
