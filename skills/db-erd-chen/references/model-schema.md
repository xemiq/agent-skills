# ERD model file (input to `scripts/render_erd.py`)

The agent never hand-writes draw.io XML when Python 3 is available. It writes this JSON model,
and the renderer turns it into the `.drawio` file, the summary, and a normalized copy of the model.
The renderer rejects a model that breaks a notation rule, and lists every problem at once.

## Top level

| Field | Required | Meaning |
|---|---|---|
| `project` | yes | Project name, used in every page title (`<project> — Conceptual ERD`) |
| `language` | no | Language code of the diagram's names, e.g. `"es"`. Default `"en"`. `en` and `es` have translated titles, page names, legend, summary and note prefixes (`Restricción:` / `Regla:`). Other codes keep those texts in English and print a warning |
| `source` | no | One line describing the inputs (e.g. `"SQL migrations in db/migrations + answers to 5 questions"`) |
| `areas` | no | Subject areas. **2 or more areas → multi-page file** (`1 - Overview` + one page per area). 0–1 areas → a single page `1 - Conceptual ERD` |
| `entities` | yes | List of entities (see below) |
| `relationships` | yes (an empty list is only valid for a 1-entity model; otherwise the validator fails unless isolation is confirmed) | List of relationships |
| `specializations` | no | EER specializations / generalizations (purple `d`/`o` circles), see below |
| `notes` | no | Constraint / rule notes (pink notes) |
| `assumptions` | no | Confirmed assumptions and decisions, each with its confirmation source |
| `open_questions` | no | Unanswered questions. They are listed in the summary and are **never** drawn as rules |
| `omitted` | no | Source elements deliberately left out (technical columns, audit tables…), each `{"item": "orders.created_at", "reason": "technical audit column"}`. Printed in the summary |
| `layout` | no | Grid positions per page (strongly recommended, see below) |

Ids (`area.id`, `entity.id`, `relationship.id`) are lowercase letters and digits only (`orderline`),
because they become stable draw.io ids (`E_orderline`, `R_contains`). Never rename an id between
versions unless the concept itself changed. Stable ids keep git diffs meaningful.

## Entity

```json
{"id": "orderline", "name": "Order Line", "area": "sales", "weak": true,
 "attributes": [
   {"name": "Line #", "kind": "partial_key"},
   {"name": "Quantity"},
   {"name": "Delivery address", "kind": "composite", "parts": ["Street", "City", "Postal code"]}
 ]}
```

- `name`: singular noun, English, Title Case.
- `area`: required when the model has 2+ areas. This is the entity's **home page**.
- `weak`: `true` for weak entities. A weak entity needs exactly one `partial_key` and no `key`, and
  exactly one identifying relationship. A strong entity needs exactly one `key` and no `partial_key`.
- Attribute `kind`: `simple` (default) · `key` · `partial_key` · `multivalued` · `derived` ·
  `composite` (needs `parts`, a list of sub-attribute names, one level deep).
- A `key` or `partial_key` may also have `parts`. It is then drawn as a composite key: one underlined
  (or dashed-underlined) ellipse with its sub-attributes. Use this for natural keys made of several
  values (`{"name": "Flight ID", "kind": "key", "parts": ["Flight number", "Departure date"]}`).
- Attribute names are in Sentence case. Booleans start with `Is` / `Has` / `Must`. No data types and no
  references to other entities (`Customer ID` inside `Order` is a relationship, not an attribute).

## Relationship

```json
{"id": "places", "name": "Places",
 "ends": [{"entity": "customer", "card": "1", "total": false},
          {"entity": "order", "card": "N", "total": true}],
 "attributes": [],
 "pages": ["sales"]}
```

- `name`: verb or verb phrase that reads from the first end to the second (`Customer` *Places* `Order`).
- `ends`: 2 ends (binary, the default) or 3 ends (ternary, only when it cannot be split).
  - `card`: `"1"`, `"N"` or `"M"`, the cardinality **of that entity**, drawn next to it.
    Binary ratios must be 1:1 (`1`,`1`), 1:N (`1`,`N`) or M:N (`M`,`N`).
  - `total`: `true` = double line (mandatory participation). Use it **only** for confirmed rules.
    Default `false`.
  - `role`: required on every end of a recursive relationship (`"manager"` / `"report"`).
- `identifying: true` draws a double diamond. It must be binary, between two different entities. The
  dependent end is a weak entity with `total: true`, and the owner end has `card: "1"`. The owner may
  itself be weak (Building → Room → Seat). In multi-page models the relationship is always added to the
  weak entity's home page.
- A ternary relationship cannot repeat an entity. Model that case as binary relationships.
- `attributes`: relationship attributes (`simple`, `multivalued`, `derived`, `composite`). No keys.
- `pages` (multi-page only): the detail pages where the relationship is drawn. Default: the home page
  of the first end. Each listed page must be the home page of one of its entities. The relationship
  always appears on the Overview too.

## Specialization (EER)

```json
{"id": "personrole", "superclass": "person", "subclasses": ["student", "employee"],
 "disjoint": false, "total": true, "defining_attribute": "Person type"}
```

- `superclass`, `subclasses`: entity ids. A specialization needs at least one subclass.
- `disjoint`: `true` draws `d` (an instance is in at most one subclass); `false` (default) draws `o`
  (overlapping). Use `true` **only** for a confirmed rule.
- `total`: `true` draws a double line from the superclass to the circle (every superclass instance is in
  at least one subclass). Default `false`. Use it **only** for a confirmed rule.
- `defining_attribute` (optional): for an attribute-defined specialization, the name of an attribute of
  the superclass (its own or inherited). It is written on the superclass line.
- A subclass entity has **no `key` or `partial_key`** (it inherits the superclass key) and is never
  `weak`. Give it only its specific attributes. Its relationships are ordinary relationships.
- Each entity is a subclass in **at most one** specialization (no multiple inheritance), and hierarchies
  cannot loop. A superclass may have several specializations, and a subclass may be specialized again.
- `pages` (multi-page only): optional. The specialization is always drawn on the Overview and on the
  home page of the superclass and of every subclass; members from other areas appear as reference
  entities.
- Specialization links make entities reachable: a subclass needs no relationship of its own.

## Notes, assumptions, open questions

```json
"notes": [{"text": "Constraint: Every Invoice belongs to exactly one Order or one Subscription.",
           "pages": ["sales"]}],
"assumptions": [{"text": "Every order has exactly one customer.", "confirmed_by": "schema"}],
"open_questions": ["Must every customer have at least one order? Drawn as partial participation."]
```

- Note text starts with `Constraint:` (integrity constraint) or `Rule:` (business rule), or with the
  `language`'s equivalents (Spanish: `Restricción:` / `Regla:`). In
  multi-page models `pages` lists the areas where the rule matters. The Overview repeats every note
  automatically.
- `confirmed_by` must be one of:
  - `stated`: written in the user's description or requirements;
  - `user`: answered by the user during clarification;
  - `schema`: enforced by the existing schema or code (NOT NULL, UNIQUE, CHECK, FK);
  - `convention`: a modeling decision required by the team guide, not a business rule (e.g. "Order
    has no natural key, so the conceptual identifier `Order ID` is used").

  Anything else is not confirmed: put it in `open_questions` and draw the least restrictive form.

## Layout

```json
"layout": {
  "main":     {"positions": {"user": [0, 0], "team": [1.6, 0]}},
  "overview": {"positions": {...}, "spacing": [380, 300]},
  "sales":    {"positions": {...}, "diamonds": {"places": [0.5, 0.2]}, "circles": {"partyrole": [1, 0.5]},
               "columns": 3}
}
```

- Page keys: `main` for a single-page model; `overview` plus the area ids for a multi-page model.
- `positions`: entity id → `[column, row]` grid coordinates (decimals allowed). Detail-page cells are
  560×440 px and Overview cells 380×300 px; override them with `spacing: [x, y]`.
- `diamonds`: relationship id → `[column, row]` to move a diamond off its default spot (the midpoint of
  its entities). Use it to route around an entity instead of passing through it.
- `circles`: specialization id → `[column, row]` to move a specialization circle. By default it sits
  halfway between the superclass and the centre of its subclasses.
- Entities without a position are placed automatically on a square grid, and the renderer prints a
  warning when it does that.
- Attributes are fanned automatically, in the free directions around their entity or diamond.

### Layout heuristics (do this before the first render)

1. Put the most connected entity in the centre, and its neighbours in adjacent cells (orthogonal or
   diagonal). Entities linked by a relationship should be **adjacent**, so that no line has to cross
   a cell.
2. Keep a weak entity next to its owner. Put subclasses in the row below their superclass, side by side.
3. Leave an empty neighbouring cell next to any entity that has a recursive relationship, or 5 or more
   attributes.
4. Two relationships between the same pair are offset automatically. Do not stack them by hand.
5. If the validator reports an overlap or a line through a shape, move one entity by 0.5–1 cell, or
   widen `spacing`, and render again. Repeat at most 5 times, then report the remaining layout issue
   to the user and do not hide it.
