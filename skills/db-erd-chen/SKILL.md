---
name: db-erd-chen
description: >-
  Generates conceptual/logical Entity-Relationship Diagrams (ERDs) in Chen notation as uncompressed
  diagrams.net (draw.io) XML files saved in the project's db-design/ folder, together with a short
  summary of entities, relationships and confirmed assumptions. Use it when the user asks to create,
  draw, update, version or reverse-engineer an ERD, entity-relationship diagram, conceptual or logical
  data model, or database design diagram from a domain description, business rules, SQL DDL,
  migrations or ORM models. Asks clarifying questions before generating. Do not use it for physical
  schemas, SQL DDL, migrations, or Mermaid/PlantUML/DBML diagrams.
license: Apache-2.0
compatibility: Any coding agent that can read/write files and run python3 (3.9+, standard library only). Without python3 a manual fallback is defined (§6, Step 7b).
metadata:
  author: XemiQ
  version: "0.2.1"
  repository: https://github.com/xemiq/agent-skills
  homepage: https://xemiqlab.com/en
---

# ERD generation skill: Chen notation → diagrams.net

You are acting as a senior data modeler. Turn the user's domain knowledge or existing schema into a
**conceptual/logical ERD in Chen notation**, saved as **diagrams.net XML in `db-design/`**, and
**ask before you draw**. These instructions are tool-agnostic. "Ask the user" means use whatever
way your environment has to ask the user and wait for the answer. "Run" means execute a shell
command. `<skill>` means the directory containing this `SKILL.md`. Run every command from the
**root of the user's repository**, so that `db-design/` is created there and never inside the skill folder.

**Non-negotiable rules (re-read before every step):**
1. **Ask first.** Never write the diagram before the clarification gate (§5) is passed.
2. **Never assume business rules.** Every cardinality, participation, key and rule comes from the
   user's words, the user's answers, the existing schema, or the team convention. Anything else is
   an *open question*, drawn in its least restrictive form. **Unstated participation is always
   `partial (default)`, never `total (default)`**, however obvious the rule seems.
3. **Conceptual only.** No data types, FK columns, junction tables, indexes, SQL or storage details.
4. **diagrams.net XML only**, uncompressed, saved as `db-design/<name>.drawio`. Never write Mermaid,
   PlantUML, DBML or images as the deliverable.
5. **Always finish with the summary** (entities, relationships, confirmed assumptions, open questions,
   validation result).
6. **Names in English by default.** If the user writes in another language, ask which language the
   diagram's names should use (§5.1 N6). Always talk to the user in their own language.

Files in this skill (paths are relative to this file):

| File | Use it for |
|---|---|
| `references/erd-guide.md` | The team's normative guide: notation, conventions, style catalog, `.drawio` format. **Its rules take precedence** |
| `references/source-mapping.md` | How to map descriptions, SQL DDL, ORMs and existing diagrams to the model |
| `references/model-schema.md` | The JSON model that the renderer takes as input, plus layout heuristics |
| `scripts/render_erd.py` | Model JSON → `.drawio` + `.summary.md` + `.model.json`. It checks the notation rules |
| `scripts/validate_erd.py` | Self-check of any `.drawio` file (format, catalog, notation, scope, structure, layout) |
| `examples/task-tracker/` | The worked example (§11), with input, clarification, model and outputs |
| `tests/test_skill.py` | Regression tests for the scripts. Run them after changing the skill |

---

## 1. Skill metadata

| Field | Value |
|---|---|
| Name | `db-erd-chen` |
| Version | 0.2.1, pre-release (semantic versioning, see §12) |
| Description | Generates conceptual/logical ERDs in Chen notation as diagrams.net XML in `db-design/`, after clarifying ambiguities, and gives a summary of the model and its assumptions |
| Author / owner | XemiQ (https://xemiqlab.com/en, https://github.com/xemiq). Questions and bugs: https://github.com/xemiq/agent-skills/issues |
| License | Apache-2.0 (see `LICENSE` at the repository root) |
| When to use | The user wants an ERD, or a conceptual/logical data model diagram, for a project, whether new, reverse-engineered from a schema/ORM, or an updated version |
| Runtime needs | File read/write, a shell with `python3` ≥ 3.9 (standard library only), a way to ask the user questions |

## 2. Trigger conditions

**Activate** when the request matches any of these:
- Keywords: *ERD, E-R diagram, entity relationship, entity-relationship, Chen notation, conceptual
  model, logical model, data model diagram, database design diagram, draw.io / diagrams.net + database*.
- Intents: "design the database for …", "model the data for …", "diagram our schema / our models",
  "reverse-engineer the DB into an ERD", "update the ERD with the new tables", "document the domain
  model".
- Project phases: requirements/inception (a domain description exists, no schema yet); design reviews
  (the team needs a diagram for a PR or design doc); brownfield documentation (migrations or ORM models
  exist); evolution (the schema changed and `db-design/` holds an older version).

**Do not activate** (or hand off) when the user wants:
- SQL DDL, migrations, ORM code, indexes, or a physical schema. If they ask for both, do the ERD
  with this skill and say that the physical part is out of its scope.
- Mermaid, PlantUML, DBML, or Crow's-foot/UML class diagrams as the deliverable. Explain that this
  skill produces Chen-notation diagrams.net XML, and offer that.
- Questions about an existing diagram that need no new diagram. Answer them directly. If you are
  unsure whether the user wants a diagram or only an explanation, ask one question.

## 3. Scope

| The skill DOES | The skill does NOT |
|---|---|
| Conceptual/logical model: entities, weak entities, attributes (key, partial key, multivalued, derived, composite), named relationships, cardinality ratios, participation | Physical model: tables, columns, data types, lengths, FK columns, junction tables, indexes, constraints syntax, `ON DELETE`, partitions, storage |
| Relationship attributes, recursive, ternary (only when it cannot be split), identifying relationships | Generate or run SQL, migrations or ORM code. Connect to databases |
| Constraint/rule notes for rules Chen cannot draw | Invent rules, enums or limits that were not stated or confirmed |
| Multi-page files (Overview + subject areas) for large models | Mermaid, PlantUML, DBML, images or other output formats |
| Reverse-engineering from DDL, migrations, ORM models, existing `.drawio` | Normalization audits, performance advice, physical tuning (mention them as follow-ups at most) |
| Versioned outputs in `db-design/`, plus a human summary | Overwrite or delete previous diagram versions |

## 4. Inputs

| Input | Required? | Where to find it |
|---|---|---|
| **Model source**: one or more of: domain description / requirements; SQL DDL or migrations; ORM models; an existing `.drawio` / `.model.json` | **Yes** (at least one) | User message, attached files, or the repository (search for `*.sql`, `migrations/`, `schema.prisma`, `models.py`, `*.entity.ts`, `db/schema.rb`, `*Context.cs`, `@Entity` classes, `db-design/`) |
| Business rules (cardinalities, mandatory links, uniqueness, limits) | Recommended | User message, docs, schema constraints. Ask for the missing ones (§5) |
| Project name | Yes (for page titles) | Repository name, README title, or ask |
| Scope boundary (which bounded context / service / tables) | When the repository has several databases or more than ~30 tables | Ask |
| Subject areas (page split) | Only for 10+ entities | Propose a split from the folder or module structure, and confirm it in §5 |
| Target folder | Default `db-design/` at the repository root | Use another folder only if the user explicitly asks |
| Diagram language | English, unless the user picks another language (§5.1 N6) | Ask when the request or source is not in English |

**Discovery.** If the user gives no source, look in the repository first (read-only), then
report what you found: "I found 14 migrations in `db/migrations/` and Prisma models in
`prisma/schema.prisma`. Should I model from the Prisma schema?" Never model silently from a source
the user did not confirm when several candidates exist.

**Asking for missing inputs.** If no usable source exists, ask exactly this and wait:
> To draw the ERD I need a source. Please give me one of: (a) a short description of the business
> domain (the things you store and how they relate), (b) the SQL schema or migrations, (c) the ORM
> model files, or (d) the path to an existing diagram. Business rules ("every order has exactly one
> customer") are welcome too.

**Unsupported or unreadable sources** are covered in §10.

## 5. Preconditions & clarifying questions (the gate)

**Preconditions before drafting:** a confirmed source (§4), a project name, and a target folder.
In a repository with several data stores, the scope must also be agreed.

### 5.1 Detect ambiguity

Classify every open point while you analyse (Steps 2–4). Use `references/source-mapping.md` to see
what is *derived* and what needs a *question*.

**Blocking**: you cannot draw a correct diagram without the answer:
- B1. No usable source, or the scope is unclear (which service, which tables).
- B2. The **maximum** cardinality of a relationship is unknown in either direction (1 vs many).
- B3. Entity or attribute? (e.g. *Address*, *Category*, *Tag*, *Species*, *Type*, *Status*: do they have their own identity, properties or managed list of values?)
- B4. Strong or weak? (Can X exist or be identified without its owner?)
- B5. A relationship is implied but not stated, or its meaning or verb is unclear.
- B6. A relationship or an entity? (Can the same pair be associated several times, with history? Is the link referenced by other things?)
- B7. Roles of a recursive relationship, or ternary vs binary.
- B8. Conflicting statements: description vs schema, two documents, or user vs code.
- B9. Key choice: no stated or enforced unique identifier and it is unclear whether a conceptual
  identifier is acceptable; **or** several candidate keys (e.g. `Email` and `Username` both unique)
  and the user has not named the identifier. Ask which one identifies the entity. The other unique
  attributes become `Constraint: <Attribute> is unique.` notes.
- B10. Single- or multi-valued? It is unknown whether an attribute can hold several values (a
  maximum, i.e. a business rule).

**Non-blocking**: there is a safe, least-restrictive default:
- N1. Minimum participation not stated → **partial** (single line). A `(default)` is **never** `total`, however obvious.
- N2. Unsure whether an attribute is derived (stored vs calculated) or composite (split into parts) →
  **simple**. These choices change the representation only, not a rule. Single vs multi-valued is B10.
- N3. Entity has no natural key → conceptual identifier `<Entity> ID` (team convention).
- N4. Technical columns (`created_at`, `version` …) → omitted, and listed in the model's `omitted`
  field, which the summary prints.
- N5. Page split, naming and verb wording → your proposal.
- N6. Diagram language: the request or source is not in English → ask which language to use for
  names and notes (*default: English*). Draft the names in the language you propose. The model's
  `language` field records the answer.

### 5.2 Ask: one batched round, then wait

1. Send **one message** with the draft model and the numbered questions. Show the draft first,
   **in full notation**, so the user can see every rule they are confirming:
   - entities, with strong/weak (and owner), the key or partial key, and the attribute kinds
     (multivalued, derived, composite);
   - every relationship with **both** ends: `Team (1) —Owns— (N, total) Project`. Mark each end's
     participation as `total` or `partial`. Mark every value that is a default rather than a stated or
     schema fact with `(default)`;
   - the notes (`Constraint:` / `Rule:`) you intend to draw.
   Only what the draft shows explicitly can later be recorded as `confirmed_by: "user"`.
2. Put **blocking questions first**, then non-blocking ones, each tagged `(blocking)` or
   `(non-blocking)`. Ask one question per number; do not mix a blocking and a non-blocking point
   in one question. Ask at most **10 questions per round**. Non-blocking questions state their
   default: *"(default: partial, single line)"*. Blocking questions may state your *recommended*
   answer, but it is never applied without an answer.
3. **Self-check the draft before sending it.** Any `total (default)` must become `partial (default)`.
   Every unstated maximum must be `?` with a blocking question. Every *species/type/category/status*-like
   value needs a B3 question. If the request is not in English, the N6 language question must be there.
4. End with "Please answer, or confirm the draft as is." (in the user's language). Then **stop and
   wait. Write no files.**
5. When the answers arrive, update the model. If they raise *new* blocking points, run another round.
   After 3 rounds, stop asking about non-blocking points. Blocking points always need an answer.
6. When there are no questions at all (for example a fully constrained schema), still show the draft
   and ask for confirmation once. The user must see what will be drawn before it is written.

### 5.3 What counts as confirmed

- `stated`: the user's description or requirements say it explicitly.
- `user`: the user answered it during clarification, or confirmed the draft in which it was shown
  explicitly. "Looks good" confirms only what the draft displayed, including `(default)` values.
- `schema`: the existing schema or code enforces it (NOT NULL FK → total participation on that side;
  UNIQUE → key or 1:1; CHECK/enum → constraint note). Parent-side participation is **never** schema-confirmed.
- `convention`: a modeling decision the team guide prescribes (e.g. N3). It is never a business rule.

Everything else goes into `open_questions` and is drawn in its **least restrictive** form: partial
participation, the "many" side when the maximum is unknown, multivalued when single vs multi-valued
is unknown, and no note. A default the user saw in the confirmed draft is `user`-confirmed. A default
the user never saw (for example in a run under §5.4) must be listed in `open_questions`.

### 5.4 When the user cannot or will not answer

- **Non-interactive run** (CI, batch, nobody can answer): do **not** write any file. Output the
  full draft (§5.2) and the questions as the final result, and stop.
- **The user explicitly says "don't ask, just generate"**:
  - If there are **blocking** points, do **not** generate. Reply with only the blocking questions,
    explaining why each one blocks, and stop.
  - If there are only non-blocking points, generate with the defaults from §5.1, and list every
    defaulted item under *Open questions*.
- **The user explicitly delegates a blocking decision** ("pick whatever, I accept it"). Only these
  classes can be delegated, each with a fixed default, recorded as an open question:
  B2 → many on the unknown side (M:N if both sides are unknown), partial participation;
  B7 roles → descriptive role names derived from the verb (e.g. `mentor` / `mentee`);
  B9 → the attribute the source names first among the candidate keys, or `<Entity> ID` if there is
  none; B10 → multivalued.
  B1, B3, B4, B5, B6 and B8 cannot be delegated, because they change what exists in the model.
  Recommend an answer and ask for a yes/no.

## 6. Workflow (follow in order)

**Step 1. Locate and confirm the source.** Follow §4. Note the project name. Check whether
`db-design/` already contains `*.model.json` or `*.drawio` files. If it does, this is an **update**:
load the latest `.model.json` (highest `-vN`) as the starting model.

**Step 2. Extract entities.** Use `references/source-mapping.md`. For each entity, record its name
(singular, Title Case), whether it is strong or weak, and its owner if weak. Drop implementation
artifacts: junction tables become relationships, value tables become multivalued attributes,
audit/technical tables are omitted.

**Step 3. Extract attributes.** For each entity, pick **exactly one** key (a natural key if one
exists, otherwise `<Entity> ID`) or, for a weak entity, one partial key. Then classify the other
attributes: simple, multivalued, derived or composite. Remove FK columns, surrogate ids that a natural
key replaces, data types and technical columns (record the omissions in `omitted`). Name attributes in Sentence case.

**Step 4. Extract relationships, cardinalities and participation.** Every FK and every stated
association becomes a named relationship (a verb). For each end, record `card` (1/N/M, the number of
*that* entity associated with one instance at the other end) and `total` (only if confirmed). Put
relationship attributes on the relationship. Add a `Constraint:`/`Rule:` note for each confirmed rule
that Chen cannot draw. Check that every entity is reachable through relationships. An isolated entity
is a question (B5), not a silent outcome.

**Step 5. Clarification gate.** Follow §5. **Stop and wait for the answers.** Then apply them and
fill `assumptions` (each with `confirmed_by`) and `open_questions`.

**Step 6. Write the model JSON.** Follow `references/model-schema.md`:
- Set `language` to the N6 answer (omit it for English).
- With 10 or more entities, define 2+ `areas`. This produces Overview + detail pages.
- Give every entity a `layout` position, following the layout heuristics in the schema reference.
- Save the model in a temporary location outside the repository if possible. Otherwise save it as
  `db-design/.erd-model-draft.json` and delete it after Step 8.
- Check it: `python3 <skill>/scripts/render_erd.py <model.json> --check`. Fix every reported problem.

**Step 7a. Render** (the normal path):
```
python3 <skill>/scripts/render_erd.py <model.json> --out-dir db-design [--name conceptual-erd]
```
The renderer creates `db-design/` if needed and picks the next free version name
(`conceptual-erd.drawio`, then `conceptual-erd-v2.drawio`, and so on). It never overwrites a file. It
writes three files with the same base name: `.drawio`, `.summary.md` and `.model.json`.

**Step 7b. Manual fallback (no python3 available).** Write the XML by hand, following
`references/erd-guide.md` §4: the mandatory first cells `0`/`1`, the exact styles and sizes from the
§4.5 catalog, the id convention from §4.6, and escaped values. Use the snippet in §11 as a template.
Pick the version name yourself following §7. Then run the §9 manual checklist item by item, since
the validator cannot run. Say in the summary that the file was hand-written and validated manually.

**Step 8. Validate.**
```
python3 <skill>/scripts/validate_erd.py db-design/<file>.drawio
```
- `ERROR` lines must be fixed. Fix the **model** (or its `layout`) and render again. Do not patch the XML.
  Rendering again creates the next version file. Delete the failed version files you just created in
  this run (only those), so that the folder keeps one result per run.
- `WARNING` lines: fix them, or justify each one in the summary.
- Layout errors (overlaps or lines through shapes): adjust `layout` positions or `spacing` and render
  again, at most 5 times. If errors remain, keep the best version and report them.
- Use `--allow-isolated "<Entity>"` only for entities the user confirmed have no relationships.

**Step 9. Review semantics.** The scripts check form, not meaning. Re-read your model against the
source: every stated fact is represented, nothing was added that was not stated or confirmed, the verbs
read correctly in both directions, and the cardinality labels sit on the correct side (§8).

**Step 10. Report.** Send the chat summary (§7.3). Point to the `.summary.md`. Do not commit unless
the user asks to.

## 7. Output specification

### 7.1 Files (all in `db-design/` at the repository root, unless the user named another folder)

| File | Content |
|---|---|
| `conceptual-erd.drawio` | **The deliverable.** Uncompressed diagrams.net XML (`<mxfile>`), opens with *File → Open from → Device* at https://app.diagrams.net/ or in the desktop/VS Code app |
| `conceptual-erd.summary.md` | Human-readable summary: entities, keys, attributes, relationships with ratio and participation, notes, confirmed assumptions with their source, open questions |
| `conceptual-erd.model.json` | The normalized model, used for regenerating and updating the diagram in later runs |

### 7.2 Naming and versioning

- Lowercase and hyphenated, stating the model level: `conceptual-erd`. A repository with several
  bounded contexts uses one file per context: `--name conceptual-erd-billing`.
- Never overwrite. A rework creates the next version (`conceptual-erd-v2.drawio`, `-v3` …), and the
  previous versions stay for comparison.
- Page names: single page `1 - Conceptual ERD`. Multi-page `1 - Overview`, `2 - <Area>`, ….
- Each page has a title `<Project> — Conceptual ERD` (plus the page name) and a notation legend.
  With `"language": "es"` the renderer translates these texts (`1 - ERD conceptual`, `1 - Vista general`).

### 7.3 Chat summary (always; keep it short)

```
ERD saved: db-design/conceptual-erd.drawio  (pages: 1 - Conceptual ERD)
Validation: PASS (0 errors, 0 warnings)
Entities (4): Team, User, Project, Task (weak, owned by Project)
Relationships (5):
- User (M) —Member of— (N) Team [Team role]; every team has a member
- Team (1) —Owns— (N) Project; every project has a team
- …
Confirmed assumptions: 13 (see summary file), e.g. "A task has at most one assignee (user)"
Open questions (drawn least-restrictive): Must every team own at least one project?
Also written: conceptual-erd.summary.md, conceptual-erd.model.json
```
List every open question in the chat. Never bury them in the file only.

## 8. Format & notation rules

The full rules are in `references/erd-guide.md` (§1–§4). The essentials:

- **Symbols:** rectangle = entity; double rectangle = weak entity; diamond = relationship; double
  diamond = identifying relationship; ellipse = attribute; underlined = key; dashed underline =
  partial key; double ellipse = multivalued; dashed ellipse = derived; ellipse with children =
  composite; single line = partial participation; double line = total participation; pink note =
  constraint/rule; grey dashed rectangle = reference entity (its home page is elsewhere).
- **Cardinality label placement:** the label next to entity X says how many X relate to **one**
  instance at the other end. `Customer (1) —Places— (N) Order` means that a customer places N orders
  and each order has 1 customer. Binary ratios are only 1:1, 1:N or M:N. For a **ternary**
  relationship, the label next to X says how many X relate to one fixed *combination* of
  instances of the other two entities.
- **Keys:** exactly one key per strong entity. A natural composite key (e.g. `Flight number` +
  `Departure date`) is drawn as **one underlined composite key** attribute (`"kind": "key"` with
  `"parts"`). Other candidate keys become `Constraint: … is unique.` notes. Limits on attribute
  values ("one or more phone numbers", "at most 5 images") become `Constraint:` notes too. A weak entity has exactly one partial key, an
  identifying relationship (double diamond) and total participation (double line).
- **Never draw:** data types, FK columns as attributes (`Customer ID` inside `Order`), junction
  tables as entities (unless they have their own identity or history), indexes, SQL, arrowheads.
- **Naming:** names are in English unless the user chose another language (N6). Entities are
  singular Title Case nouns. Attributes are in Sentence case, and English booleans start with
  `Is`/`Has`/`Must`. Relationships are verb phrases. Notes start with `Constraint:` or `Rule:`, or the
  chosen language's prefixes (Spanish `Restricción:` / `Regla:`).
- **Multi-page:** the Overview shows every entity and relationship, without attributes, and repeats
  every note. Each entity has exactly one home page with all its attributes. Elsewhere it is a
  reference entity without attributes. Every relationship appears on at least one detail page.
- **XML format:** `<mxfile><diagram><mxGraphModel><root>`. The first cells are `id="0"` and
  `id="1" parent="0"`. Styles and sizes come from the catalog (`scripts/erd_catalog.py`, which
  mirrors guide §4.5). Ids are `E_<entity>`, `R_<relationship>`, `a<n>`, `s<n>`, `e<n>`, `n<n>`,
  `t<n>`, `l<n>`. Relationship connectors go from the diamond to the entity, and attribute
  connectors from the ellipse to its owner. Values are XML-escaped (and HTML-escaped, since `html=1`).
  The file is never compressed.

## 9. Validation & quality checklist

**Automatic** (`validate_erd.py`). It must report `PASS`:
- [ ] Well-formed XML, `<mxfile>` root, uncompressed pages, mandatory cells `0`/`1`, unique ids, no
      dangling connectors. These structural checks stand in for an import test; the validator does
      not open the file in diagrams.net.
- [ ] Every shape and connector matches the style catalog and sizes. No arrowheads.
- [ ] Every relationship has a name and a 1/N/M label on every end. Ratios are valid. Recursive ends
      have roles. Identifying relationships connect one weak entity with a double line.
- [ ] Every attribute connects to exactly one owner (no orphan attributes). Keys are correct per entity.
- [ ] No physical leaks: data types, PK/FK/SQL terms, snake_case names, `<Entity> ID` attributes.
- [ ] All entities are reachable: each takes part in a relationship, and the entity graph is connected.
- [ ] Multi-page consistency: the Overview is complete and has no attributes, one home page per
      entity, reference entities have no attributes, notes are repeated on the Overview.
- [ ] Title and legend on every page. No overlapping shapes, and no line through a shape.

**Manual** (always; the agent checks these against the source):
- [ ] Every entity, relationship and rule in the source appears, including attribute limits (as
      notes). Nothing unconfirmed was added.
- [ ] Total participation appears only where `stated`, `user` or `schema` confirms it.
- [ ] Relationship verbs read correctly, and the labels are on the right side.
- [ ] Weak entities really depend on their owner, and M:N relationships really have no history or identity.
- [ ] `open_questions` lists everything unresolved, and the chat summary repeats it.
- [ ] Previous versions in `db-design/` are untouched.

## 10. Error handling & edge cases

| Situation | What to do |
|---|---|
| No source, empty description, or "make me an ERD" with nothing else | Search the repository (read-only). If nothing is found, ask the §4 question and wait. Do not invent a sample domain |
| Very vague description ("an app for shops") | Propose a draft of candidate entities and ask for confirmation (§5). Draw nothing until it is confirmed |
| Several candidate sources (e.g. migrations and ORM disagree) | Treat it as a conflict (B8). Show the differences and ask which one is authoritative |
| Conflicting business rules (user vs schema, two documents) | Never pick one silently. Quote both and ask. If it is still unresolved, draw the least restrictive form and record an open question |
| Unsupported source (binary DB dump, proprietary model file, spreadsheet you cannot parse, image while you cannot view images) | Say what you cannot read and ask for a supported one: text description, SQL DDL (e.g. `pg_dump --schema-only`), ORM files, or an exported `.drawio` |
| Compressed `.drawio` input | `python3 <skill>/scripts/validate_erd.py --decompress in.drawio out.drawio`, then read it |
| NoSQL / document models | Referenced documents become relationships. Embedded arrays become weak entities or multivalued/composite attributes, asked as B3/B4 |
| Inheritance / polymorphic associations | `references/source-mapping.md` §2 (inheritance and polymorphic rows). These always need a question |
| Huge schema (more than ~40 entities) | Agree a scope or split it into bounded contexts (one file per context), or use areas with ≤ 12 entities per detail page |
| Entity with no relationships | Ask (B5). If the user confirms it is standalone, validate with `--allow-isolated "<Name>"` and mention it in the summary |
| Renderer reports model errors | Fix the model and run `--check` again. These are notation violations (e.g. a weak entity without an identifying relationship). Do not bypass them |
| Validator layout errors persist after 5 attempts | Keep the best version, list the remaining layout issues in the summary, and suggest a manual nudge in diagrams.net (moving shapes keeps all connections) |
| `db-design/` cannot be created or written (permissions, read-only filesystem, path is a file) | Report the exact error. Ask for another folder inside the repository and wait; never pick one silently. If no file can be written at all, print the full XML in a fenced block, with instructions to save it as `db-design/conceptual-erd.drawio` |
| A file with the target name already exists | Never overwrite. The renderer picks the next `-vN`. If the user explicitly asks to replace a file, use `--out <path> --force` only for that file |
| `python3` not available | Use the Step 7b manual fallback and say so in the summary |
| User asks for Mermaid/PlantUML/SQL as well | Explain that this skill only outputs Chen diagrams.net XML. Deliver the ERD. Other formats are separate tasks outside this skill |
| User asks for physical details inside the ERD (types, FKs) | Explain the conceptual-only rule (guide §1). Offer to list such details in a separate physical design document if they want one |

## 11. Worked example

The full run is in `examples/task-tracker/input.md`, with the model and committed outputs in the same folder.

**Input (domain description):** *Teams have a unique name and a creation date. Users have a unique
email, a full name (first and last), one or more phone numbers and an active flag. Users belong to
teams and have a role in each team. Projects belong to exactly one team and have a unique code, a name
and a start date. Projects are split into tasks numbered 1, 2, 3… within the project. A task has a
title, a status and estimated hours, and can be assigned to a user. Users can mentor other users. A
project's total estimated hours is calculated from its tasks.*

**Clarification (the agent shows the draft in full notation, with defaults marked, and asks 7
questions, blocking ones first):** mentoring cardinality; both maxima of task assignment; team
membership and whether the role is per team; whether every
team must have a member; whether every team must own a project; the status values; self-mentoring.
**Answers:** one mentor at most, many mentees; at most one assignee per task, many tasks per user;
several teams, role per team; yes; *not decided*; To do / In progress / Done; never. "Everything else
in the draft is fine" confirms the displayed `(default)` partial participations.

**Resulting ERD structure:**

| Element | Result |
|---|---|
| Entities | **Team** (key `Team name`, `Created on`) · **User** (key `Email`, composite `Full name` → `First name`, `Last name`, multivalued `Phone numbers`, `Is active`) · **Project** (key `Project code`, `Name`, `Start date`, derived `Total estimated hours`) · **Task**, weak (partial key `Task #`, `Title`, `Status`, `Estimated hours`) |
| Relationships | User (M) —**Member of**— (N, total) Team, with attribute `Team role` · Team (1) —**Owns**— (N, total) Project · Project (1) =**Contains**= (N, total) Task, identifying · User (1) —**Assigned to**— (N) Task · User (1, mentor) —**Mentors**— (N, mentee) User |
| Notes | `Constraint: A User has at least one phone number.` · `Constraint: Task status is one of To do, In progress, Done.` · `Rule: A user cannot mentor themselves.` |
| Open question | Must every team own at least one project? (Team's participation in Owns stays partial) |

**diagrams.net XML snippet** (from `examples/task-tracker/db-design/conceptual-erd.drawio`: the
weak entity, its identifying relationship and partial key, and a recursive role-labelled end):
```xml
<mxfile host="app.diagrams.net" agent="db-erd-chen skill" version="24.0.0">
  <diagram id="erd" name="1 - Conceptual ERD">
    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="E_project" value="Project" style="whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">
          <mxGeometry x="1206" y="810" width="150" height="56" as="geometry" />
        </mxCell>
        <mxCell id="E_task" value="Task" style="shape=ext;margin=3;double=1;whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">
          <mxGeometry x="310" y="810" width="150" height="56" as="geometry" />
        </mxCell>
        <mxCell id="R_contains" value="Contains" style="shape=rhombus;double=1;perimeter=rhombusPerimeter;whiteSpace=wrap;html=1;align=center;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="768" y="801" width="130" height="74" as="geometry" />
        </mxCell>
        <mxCell id="a12" value="&lt;span style=&quot;border-bottom: 1px dashed;&quot;&gt;Task #&lt;/span&gt;" style="ellipse;whiteSpace=wrap;html=1;align=center;fillColor=#ffffff;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="194" y="884" width="124" height="44" as="geometry" />
        </mxCell>
        <!-- … other entities, attributes, title, legend and notes … -->
        <mxCell id="e5" value="1" style="endArrow=none;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_contains" target="E_project">
          <mxGeometry x="0.6" relative="1" as="geometry">
            <mxPoint as="offset" />
          </mxGeometry>
        </mxCell>
        <mxCell id="e6" value="N" style="shape=link;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_contains" target="E_task">
          <mxGeometry x="0.6" relative="1" as="geometry">
            <mxPoint as="offset" />
          </mxGeometry>
        </mxCell>
        <mxCell id="e9" value="1 (mentor)" style="endArrow=none;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_mentors" target="E_user">
          <mxGeometry x="0.6" relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="105" y="220" />
              <mxPoint x="325" y="220" />
            </Array>
            <mxPoint as="offset" />
          </mxGeometry>
        </mxCell>
        <!-- … -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**Test it:** `python3 tests/test_skill.py` renders this example and validates it (it must `PASS`).
It also checks that the validator rejects FK attributes, data types, missing cardinalities, dangling
or arrowed connectors, orphan attributes, isolated entities, overlaps, style drift, compressed
files and multi-page inconsistencies, and it covers every case found by the adversarial review. The acceptance criteria for the agent's behaviour are listed at
the end of `examples/task-tracker/input.md`.

## 12. Extensibility & maintenance

The details are in `references/maintenance.md`. In short:
- Styles live in `scripts/erd_catalog.py` only. New notations, EER features and diagram languages
  are added there, with matching validator rules.
- Other export formats (SVG/PNG) are *additional* artifacts exported from the `.drawio`, which stays
  the deliverable.
- Every fix adds a test. Versions follow semantic versioning in the front matter and `CHANGELOG.md`.
