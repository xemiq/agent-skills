# Changelog: db-erd-chen

Semantic versioning: MAJOR = output contract or breaking model-schema change; MINOR = new
capabilities or checks; PATCH = fixes.

## 0.4.0 — 2026-11-12
- New: SVG previews. Next to every `.drawio`, the renderer writes `<base>.svg`, or one `<base>.p<N>.svg`
  per page for multi-page files (p1 = Overview). GitHub, GitLab and Markdown show these inline, so a
  diagram can be reviewed in a pull request without opening diagrams.net. `--no-svg` skips them.
- New: `--drawio-svg` also writes `<base>.drawio.svg`, the first page as an image with the whole
  diagram embedded, so diagrams.net can open and edit it. It is opt-in because it is not diffable and
  duplicates the `.drawio`.
- New script `scripts/export_svg.py`: draws the previews from the `.drawio` file itself (shapes,
  double lines, labels, waypoints, notes, legend, specializations), so it also refreshes them after a
  manual edit in diagrams.net. Standard library only. A failed preview is a warning: the `.drawio` is
  always kept.
- Versioning and `--out --force` now include the preview files, so a leftover preview never gets
  overwritten or reused.
- Worked example: committed `conceptual-erd.svg` preview, plus a test that keeps it current. Its
  `conceptual-erd.model.json` was regenerated: it lacked the `"language": "en"` field that the renderer
  has written since 0.2.0.
- SKILL.md rule 4: the deliverable is still the `.drawio`, and the previews are generated extras.
  Guide §3.3: commit the previews and never edit them by hand.
- README: shows the example's preview, with the version and pin example updated.

## 0.3.0 — 2026-11-12
- New: EER specialization / generalization, in the Elmasri–Navathe style. A purple circle labelled `d`
  (disjoint) or `o` (overlapping) sits between the superclass and its subclasses. A double superclass
  line means a total specialization, and an optional defining attribute is written on that line.
  Multi-level hierarchies and several specializations per superclass are supported. Each subclass has
  exactly one superclass. Multiple inheritance and union types (categories) are not supported yet.
- Model: new optional `specializations` list and `layout.<page>.circles`. Subclasses have no key (they
  inherit it) and cannot be weak. The renderer rejects multiple inheritance, cycles, unknown entities and
  a defining attribute that the superclass does not have. Models without specializations render
  byte-identically to 0.2.2.
- Renderer: places the circle between the superclass and its subclasses, avoiding shapes and lines.
  Specialization links count for reachability. Multi-page files show each specialization on the
  Overview and on the home page of every member. The legend gets four extra lines, only on pages that
  show a specialization. The summary has a Specializations section, and subclasses show "Subclass of X"
  with the key "inherited from X". Spanish is translated.
- Validator: new `eer` checks: `d`/`o` labels, one superclass line, single unlabelled subclass lines,
  no key or weak subclass, one superclass per subclass, and Overview vs detail page consistency.
- Clarification: new blocking class B11 (specialization or type attribute, which cannot be delegated)
  and non-blocking N7 (unstated disjointness/completeness → overlapping and partial, never `d` or
  total by default). The draft shows each specialization with its constraints.
- Guide: new §2.10 "Specialization and generalization (EER)", plus symbols, style catalog rows, the
  `G_` id prefix, checklist and glossary entries. Source mapping: wording, single-table, class-table
  and concrete-table inheritance, and ORM inheritance declarations. The old "1:1 `Is a` relationship"
  workaround is replaced.
- README: version and pin example updated (they still said 0.2.1).

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
