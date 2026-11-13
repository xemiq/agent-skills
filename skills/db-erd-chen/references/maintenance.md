# Extensibility & maintenance

How to extend and maintain the `db-erd-chen` skill. SKILL.md §9 points to this file.

- **Single source of truth for styles:** `scripts/erd_catalog.py`. If the team guide (§4.5) changes,
  update `references/erd-guide.md` and `erd_catalog.py` together, render the example again
  (`render_erd.py examples/task-tracker/model.json --out examples/task-tracker/db-design/conceptual-erd.drawio --force`),
  update the template in `references/manual-fallback.md` §2, and run `tests/test_skill.py`.
- **New notations** (Crow's foot, IDEF1X, UML class): add a catalog module per notation (e.g.
  `erd_catalog_crowsfoot.py`) and a `"notation"` field in the model. Keep the model notation-neutral,
  which it already is: entities, ends with card/total. Add a matching rule set to the validator. Chen
  stays the default.
- **EER features** (specialization/generalization, categories): add `"specializations"` to the model
  and an `isa` triangle style to the catalog. Until then they are modeled as described in
  `references/source-mapping.md` (the inheritance row).
- **Other export formats** (SVG/PNG/PDF): export from the `.drawio` with the diagrams.net desktop CLI
  (`drawio -x -f png …`) as an *additional* artifact. The `.drawio` file stays the deliverable.
  Mermaid/PlantUML exporters, if they are ever wanted, belong in a separate skill so this one keeps
  its single output contract.
- **New source types:** add a section to `references/source-mapping.md`, with its derived-vs-question
  classification.
- **Tests:** every bug fix adds a case to `tests/test_skill.py`. Run the tests before releasing a new version.
- **Versioning:** semantic versioning in the front matter. MAJOR = output contract changes (file
  layout, model schema breaking changes); MINOR = new capabilities or checks; PATCH = fixes. Record
  every change in `CHANGELOG.md`.
- **Agent-agnostic packaging:** this folder follows the common `SKILL.md` + front matter
  convention. Agents that use another mechanism (rules files, custom instructions) can reference or
  inline this file unchanged. Nothing in it depends on a vendor-specific tool name.
- **New diagram languages:** add an entry to `LANG` in `scripts/erd_catalog.py`, with every key
  that the `en` entry has (title, page names, legend, the `Constraint:`/`Rule:` prefixes, summary
  headings), plus a test in `tests/test_skill.py` (see `LanguageTests`). Any language code is accepted
  in the model. Languages without an entry fall back to English for the generated texts, and the
  renderer prints a warning.
