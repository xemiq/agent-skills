# Changelog: db-erd-chen

Semantic versioning: MAJOR = output contract or breaking model-schema change; MINOR = new
capabilities or checks; PATCH = fixes.

## 0.2.2 — 2026-11-12
- SKILL.md restructured for progressive disclosure (495 → 353 lines), with no change in
  behaviour or in the model and output contract. The metadata section (it repeated the front
  matter) and the automatic checklist (the validator enforces it) were removed. The trigger and
  scope sections were merged and shortened, and the notation section now holds only the points that
  need judgement.
- New `references/edge-cases.md`: the full edge-case table and the procedure for runs where the
  user cannot or will not answer (non-interactive, "don't ask", delegated decisions). SKILL.md keeps
  the hard limits inline.
- New `references/manual-fallback.md`: the hand-written XML procedure (no python3) and the XML
  template, which moved out of the worked-example section. The documentation-sync test now reads it.
- New rule 7 in the non-negotiable rules: never overwrite or delete previous versions (it was
  already in the checklist and the workflow).
- SKILL.md sections renumbered (§1 When to use … §9 Worked example and maintenance). The clarification
  codes B1–B10 and N1–N6 are unchanged.

## 0.2.1 — 2026-11-11
- Summary file: attribute kinds (`[multivaluado]`, `[derivado]`) and confirmation sources
  (`usuario`, `declarado`, `esquema`, `convención`) are now translated for Spanish diagrams. A test
  run showed them still in English.

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
