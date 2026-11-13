# Edge cases and exceptional runs

Read this file when a run leaves the normal path in SKILL.md: the user cannot or will not answer,
the source is unusual, or a script or the filesystem fails. The clarification codes (B1–B10, N1–N6)
are defined in SKILL.md §3.1.

## 1. When the user cannot or will not answer

- **Non-interactive run** (CI, batch, nobody can answer): do **not** write any file. Output the
  full draft (SKILL.md §3.2) and the questions as the final result, and stop.
- **The user explicitly says "don't ask, just generate"**:
  - If there are **blocking** points, do **not** generate. Reply with only the blocking questions,
    explaining why each one blocks, and stop.
  - If there are only non-blocking points, generate with the defaults from SKILL.md §3.1, and list
    every defaulted item under *Open questions*.
- **The user explicitly delegates a blocking decision** ("pick whatever, I accept it"). Only these
  classes can be delegated, each with a fixed default, recorded as an open question:
  B2 → many on the unknown side (M:N if both sides are unknown), partial participation;
  B7 roles → descriptive role names derived from the verb (e.g. `mentor` / `mentee`);
  B9 → the attribute the source names first among the candidate keys, or `<Entity> ID` if there is
  none; B10 → multivalued.
  B1, B3, B4, B5, B6, B8 and B11 cannot be delegated, because they change what exists in the model.
  Recommend an answer and ask for a yes/no.

A default the user never saw in a confirmed draft (for example in a "don't ask" run) is not
`user`-confirmed: list it in `open_questions`.

## 2. Situations and what to do

| Situation | What to do |
|---|---|
| No source, empty description, or "make me an ERD" with nothing else | Search the repository (read-only). If nothing is found, ask the SKILL.md §2 question and wait. Do not invent a sample domain |
| Very vague description ("an app for shops") | Propose a draft of candidate entities and ask for confirmation (SKILL.md §3). Draw nothing until it is confirmed |
| Several candidate sources (e.g. migrations and ORM disagree) | Treat it as a conflict (B8). Show the differences and ask which one is authoritative |
| Conflicting business rules (user vs schema, two documents) | Never pick one silently. Quote both and ask. If it is still unresolved, draw the least restrictive form and record an open question |
| Unsupported source (binary DB dump, proprietary model file, spreadsheet you cannot parse, image while you cannot view images) | Say what you cannot read and ask for a supported one: text description, SQL DDL (e.g. `pg_dump --schema-only`), ORM files, or an exported `.drawio` |
| Compressed `.drawio` input | `python3 <skill>/scripts/validate_erd.py --decompress in.drawio out.drawio`, then read it |
| NoSQL / document models | Referenced documents become relationships. Embedded arrays become weak entities or multivalued/composite attributes, asked as B3/B4 |
| Inheritance / subtypes | A specialization (SKILL.md §6) when the subtypes have their own attributes or relationships; see the inheritance rows of `references/source-mapping.md` §1–§3. Unclear → B11 |
| Polymorphic associations (`owner_type` + `owner_id`) | `references/source-mapping.md` §2 (polymorphic row). Always a question |
| Subtypes with several superclasses (shared subclass) or union types / categories | Not supported yet (each subclass has one superclass). Say so, and agree a workaround with the user: pick the main superclass and add a `Rule:` note, or keep separate entities with relationships |
| Huge schema (more than ~40 entities) | Agree a scope or split it into bounded contexts (one file per context), or use areas with ≤ 12 entities per detail page |
| Entity with no relationships | Ask (B5). If the user confirms it is standalone, validate with `--allow-isolated "<Name>"` and mention it in the summary |
| Renderer reports model errors | Fix the model and run `--check` again. These are notation violations (e.g. a weak entity without an identifying relationship). Do not bypass them |
| Validator layout errors persist after 5 attempts | Keep the best version, list the remaining layout issues in the summary, and suggest a manual nudge in diagrams.net (moving shapes keeps all connections) |
| `db-design/` cannot be created or written (permissions, read-only filesystem, path is a file) | Report the exact error. Ask for another folder inside the repository and wait; never pick one silently. If no file can be written at all, print the full XML in a fenced block, with instructions to save it as `db-design/conceptual-erd.drawio` |
| A file with the target name already exists | Never overwrite. The renderer picks the next `-vN`. If the user explicitly asks to replace a file, use `--out <path> --force` only for that file |
| `python3` not available | Follow `references/manual-fallback.md` and say so in the summary |
| User asks for Mermaid/PlantUML/SQL as well | Explain that this skill only outputs Chen diagrams.net XML. Deliver the ERD. Other formats are separate tasks outside this skill |
| User asks for physical details inside the ERD (types, FKs) | Explain the conceptual-only rule (guide §1). Offer to list such details in a separate physical design document if they want one |
