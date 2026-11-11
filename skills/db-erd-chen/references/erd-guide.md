# ERD Guide: Chen Notation and the `.drawio` Format

**Audience:** every developer and data modeler on the team.
**Applies to:** every project that documents its database design with an Entity-Relationship Diagram (ERD).

This guide defines **how ERDs must be built** across all team projects:
- which notation we use (Chen) and what each symbol means;
- the modeling conventions we follow;
- how all of it is represented in the `.drawio` file format (diagrams.net), so that any team member can create, read, review or generate a diagram the same way.

The examples use a generic order-management domain (`Customer`, `Order`, `Order Line`, `Product`, `Warehouse`, `Employee`). They only illustrate the rules and are not tied to any project.

---

## 1. Scope: conceptual/logical model, not physical

Our ERDs describe the **conceptual/logical model**: what the business needs to store and how things relate. They do not describe how a specific database engine implements it.

| Included | NOT included |
|---|---|
| Entities (business things: Order, Product, Customer…) | Tables or physical table names |
| Attributes at a conceptual level (`Unit price`, `Status`) | Data types (`decimal(14,4)`, `uuid`, `varchar(200)`) |
| Named relationships (verbs) | Foreign-key columns (`customer_id`, `order_id`) |
| Cardinality and participation | Indexes, physical `UNIQUE` constraints, `ON DELETE` rules |
| Business rules as notes | SQL DDL, triggers, partitions, storage details |
| Conceptual keys (natural keys whenever they exist) | Purely technical columns (surrogate ids when a natural key exists, sync flags, row versions) |

**Golden rule:** if an element exists only because of how the database is implemented, it does not appear as such in the ERD. That covers foreign keys, junction tables and indexes.
- A foreign key is drawn as a **relationship**.
- A junction table for a many-to-many association is drawn as an **M:N relationship**, with its own attributes if it has any.

---

## 2. Chen notation

### 2.1 Visual summary

| Symbol | Meaning | Example |
|---|---|---|
| Rectangle | (Strong) entity | `Customer`, `Order`, `Product` |
| Double rectangle | Weak entity | `Order Line` |
| Diamond | Relationship | `Places`, `Includes`, `Stores` |
| Double diamond | Identifying relationship (between a weak entity and its owner) | `Contains` (Order → Order Line) |
| Ellipse | Simple attribute | `Name`, `Quantity` |
| Ellipse with **underlined** text | Key attribute (identifier) | `SKU` (Product), `Email` (Customer) |
| Ellipse with **dashed-underlined** text | Partial key of a weak entity | `Line #` (Order Line) |
| Double ellipse | Multivalued attribute | `Phone numbers`, `Tags` |
| Ellipse with dashed border | Derived (calculated) attribute | `Order total`, `Age` |
| Ellipse with child ellipses | Composite attribute | `Address` → `Street`, `City`, `Postal code` |
| Single line | Partial (optional) participation | An Order *may* have no Employee assigned |
| Double line | Total (mandatory) participation | Every Order Line *must* belong to an Order |
| `1`, `N`, `M` on the line | Cardinality ratio | `1:N`, `M:N` |
| Pink note | Constraint or business rule that the symbols cannot express | "Every Invoice belongs to exactly one Order or one Subscription" |
| Grey dashed rectangle | Reference entity: fully defined (with attributes) on another page | `Customer` shown on the Orders page |

### 2.2 Entities

- A **strong entity** (rectangle) has its own identity through a key attribute. Examples: `Customer`, `Product`, `Order`.
- A **weak entity** (double rectangle) cannot be identified on its own and exists only while its owner exists. It is identified by its **owner's key plus a partial key**.
  - Example: `Order Line` depends on `Order` and is identified by the order plus `Line #`.
- A weak entity always connects to its owner through an **identifying relationship** (double diamond), with **total participation** (double line) on the weak side.

**Naming:** a singular noun, in English, in *Title Case* (`Order Line`, not `order_lines` or `OrderLines`).

### 2.3 Attributes

| Type | When to use it | How to draw it |
|---|---|---|
| Simple | Atomic value | Plain ellipse |
| Key | Uniquely identifies the entity. Prefer a **natural key** (`SKU`, `Email`, `Invoice number`). If none exists, use a conceptual identifier (`Order ID`) | Underlined text |
| Partial key | Identifies a weak entity *within* its owner | Dashed underline |
| Multivalued | Can hold several values for the same instance | Double ellipse |
| Derived | Calculated from other data, never captured directly | Dashed border |
| Composite | Groups sub-attributes that belong together | Parent ellipse connected to smaller child ellipses |

**Rules:**
- Every **strong** entity has **exactly one** underlined key attribute. When the natural key is made of several values (e.g. `Flight number` + `Departure date`), draw it as one underlined composite attribute. Other unique attributes are written as `Constraint: … is unique.` notes.
- Every **weak** entity has **exactly one** partial key (dashed underline) and **no** underlined key: its full identity is the owner's key plus the partial key.
- Attributes are named in English, in *Sentence case* (`Unit price`, `Is active`). Booleans start with `Is`, `Has` or `Must`.
- No data types, lengths or precision.
- A reference to another entity (e.g. `Customer ID` inside `Order`) is **never** drawn as an attribute. It is a **relationship**.

### 2.4 Relationship attributes

A relationship, usually an M:N one, can have attributes of its own that belong to neither entity:

- `Order` —**Includes** (`Quantity`, `Unit price`)— `Product`
- `Product` —**Stored in** (`Quantity on hand`)— `Warehouse`

Draw them as ellipses connected to the **diamond**, not to the entities.

### 2.5 Relationships

- Name a relationship with a **verb or verb phrase** in English that reads from one entity to the other (`Customer` *Places* `Order`, `Warehouse` *Stores* `Product`).
- **Degree:** relationships are normally binary.
  - A **recursive** relationship (an entity related to itself) is valid. Label the role on each line, e.g. `1 (manager)` / `N (report)` for `Employee` *Manages* `Employee`.
  - Use a ternary relationship only when the association genuinely cannot be split into binary ones.
- If two entities have two different relationships, draw **two diamonds** (e.g. `Employee` *Creates* `Order` and `Employee` *Approves* `Order`).

### 2.6 Cardinality ratio

The label sits on each line, **next to the entity it refers to**. It states how many instances of *that* entity can be associated with **one** instance of the entity at the other end.

| Type | Labels | Reading | Example |
|---|---|---|---|
| 1:1 | `1` — `1` | One to one | `Order` *Billed by* `Invoice` |
| 1:N | `1` — `N` | One to many | `Customer` *Places* `Order` |
| M:N | `M` — `N` | Many to many | `Order` *Includes* `Product` |

Example: in `Customer (1) — Places — (N) Order`, a customer places N orders and each order is placed by 1 customer.

### 2.7 Participation (optional vs mandatory)

Participation combines with cardinality through the **line type**:

- **Double line = total participation:** every instance of that entity **must** take part in the relationship.
- **Single line = partial participation:** taking part is optional.

Example `Customer — Places — Order`:
- Single line on the `Customer` side: a customer *may* have no orders yet.
- Double line on the `Order` side, if the business confirms that every order must have a customer.

> **Team rule:** mark total participation only when the rule is **confirmed**, either by the business or because the existing schema enforces it. When in doubt, draw it as partial and record the open question.

### 2.8 Constraints Chen cannot express: notes

Some rules cannot be drawn with the basic symbols. Document them in a **pink note** on the relevant page. Typical cases:

- **Exclusive OR:** "Every Invoice belongs to exactly ONE Order or ONE Subscription."
- **Conditional rules:** "If the Product is serial-tracked, every sold unit must be recorded on the Order Line."
- **Composite uniqueness:** "A Serial number is unique within its Manufacturer."
- **Ranges and limits:** "A Product has between 1 and 5 images."

Wording: start with `Constraint: …` for integrity constraints and `Rule: …` for business rules. Write them in English, like the rest of the diagram.

---

## 3. Organizing the diagram file

### 3.1 Multiple pages

A single `.drawio` file holds several pages (tabs):

| Page | Content |
|---|---|
| `1 - Overview` | **All** entities and **all** relationships, **without attributes**. It is the map of the whole model |
| `2 … N` | One page per subject area (e.g. Security, Catalog, Inventory, Sales), with attributes |

Consistency rules:
1. **Every entity has exactly one "home" page**, where it is drawn with all of its attributes.
2. On any other page it is drawn as a **reference entity**: grey, dashed border, italic text, **no attributes**.
3. **Every relationship** appears on the Overview and on **at least one** detail page.
4. Constraint notes go on the page where the rule matters. The Overview repeats all of them.
5. Every page has a **title** (`<Project name> — Conceptual ERD`, plus the page name) and a **legend** of the notation.

Small models (fewer than ~10 entities) may use a single page with attributes. Rule 5 still applies.

### 3.2 Layout

- Place entities on a grid and put each relationship diamond between the two entities it connects.
- Fan attributes **radially** around their entity, on the side without relationship lines, so that no attribute line crosses another ellipse.
- Composite attributes spread their children outward, in the same direction as the fan.
- Never let a line pass through an entity. When no straight path exists, use **waypoints**.
- Minimize line crossings. Some unavoidable crossings are acceptable on the Overview.

### 3.3 Files and versions

- Store diagrams in a `db-design/` folder at the root of each project repository.
- File names are lowercase and hyphenated, and state the model level and version: `conceptual-erd.drawio`, `conceptual-erd-v2.drawio`.
- When a design is reworked, create a **new version file** and keep the previous one, so reviewers can compare.
- Commit `.drawio` files **uncompressed** (see §4.1) so diffs are readable.

---

## 4. The `.drawio` file format

### 4.1 What it is

A `.drawio` file is an **XML** document that diagrams.net (https://app.diagrams.net/, also available as a desktop app and a VS Code extension) opens directly.
- **Opening a file:** use *File → Open from → Device*, or drag the file in.
- **Always save uncompressed**, so the file is readable, diffable in git and can be generated by scripts. In diagrams.net, turn off *File → Properties → Compressed*.

### 4.2 Overall structure

```xml
<mxfile host="app.diagrams.net" agent="generated" version="24.0.0">
  <diagram id="page1" name="1 - Overview">
    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1"
                  connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- every shape (vertex) and connector (edge) goes here -->
      </root>
    </mxGraphModel>
  </diagram>
  <diagram id="page2" name="2 - Sales">
    ...
  </diagram>
</mxfile>
```

| Element | Purpose |
|---|---|
| `<mxfile>` | File root |
| `<diagram>` | One page. `name` is the tab label. `id` is unique within the file |
| `<mxGraphModel>` | Canvas settings. `page="0"` gives an infinite canvas with no paper sheet |
| `<root>` | Contains every cell |
| `<mxCell id="0"/>` and `<mxCell id="1" parent="0"/>` | Root cell and default layer. **Mandatory**, and always the first two cells |

### 4.3 Shapes (vertices)

```xml
<mxCell id="E_order" value="Order" style="whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">
  <mxGeometry x="800" y="500" width="150" height="56" as="geometry"/>
</mxCell>
```

- Set `vertex="1"` and `parent="1"`.
- `value` is the visible text. It may contain HTML when `html=1`. The characters `<`, `>`, `&` and `"` **must be escaped** (`&lt;`, `&gt;`, `&amp;`, `&quot;`).
- In `mxGeometry`, `x`/`y` is the top-left corner and `width`/`height` is the size.

### 4.4 Connectors (edges)

```xml
<mxCell id="e12" value="N" style="shape=link;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_contains" target="E_orderline">
  <mxGeometry x="0.6" relative="1" as="geometry">
    <mxPoint as="offset"/>
  </mxGeometry>
</mxCell>
```

- Set `edge="1"`, with `source` and `target` pointing to existing `id`s. A dangling connector does not follow the shapes when they move.
- **Direction convention:**
  - a relationship connector goes **from the diamond (source) to the entity (target)**;
  - an attribute connector goes **from the ellipse (source) to the entity or diamond (target)**.
- The relationship connector's `value` is the cardinality (`1`, `N`, `M`).
- `mxGeometry x` (with `relative="1"`) positions the label along the line, from `-1` (source) to `1` (target). Use `x="0.6"` so the cardinality sits **next to the entity**.
- **Waypoints** route a line around obstacles:

```xml
<mxGeometry relative="1" as="geometry">
  <Array as="points">
    <mxPoint x="775" y="1900"/>
  </Array>
  <mxPoint as="offset"/>
</mxGeometry>
```

### 4.5 Style catalog (mandatory)

To keep diagrams consistent across projects, use **exactly** these styles and sizes:

| Element | Size (w×h) | `style` |
|---|---|---|
| Entity | 150×56 | `whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;` |
| Weak entity | 150×56 | `shape=ext;margin=3;double=1;whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;` |
| Reference entity | 150×56 | entity (or weak entity) style **+** `dashed=1;fillColor=#f5f5f5;strokeColor=#999999;fontColor=#666666;fontStyle=3;` |
| Relationship | 130×74 | `shape=rhombus;perimeter=rhombusPerimeter;whiteSpace=wrap;html=1;align=center;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;` |
| Identifying relationship | 130×74 | `shape=rhombus;double=1;perimeter=rhombusPerimeter;whiteSpace=wrap;html=1;align=center;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;` |
| Attribute | 124×44 | `ellipse;whiteSpace=wrap;html=1;align=center;fillColor=#ffffff;strokeColor=#666666;fontSize=11;` |
| Key attribute | 124×44 | attribute style **+** `fontStyle=4;` (underline) |
| Partial key | 124×44 | attribute style; `value` = `<span style="border-bottom: 1px dashed;">Line #</span>` (escaped) |
| Multivalued attribute | 124×44 | `ellipse;shape=doubleEllipse;margin=3;whiteSpace=wrap;html=1;align=center;fillColor=#ffffff;strokeColor=#666666;fontSize=11;` |
| Derived attribute | 124×44 | attribute style **+** `dashed=1;` |
| Sub-attribute (of a composite) | 104×34 | `ellipse;whiteSpace=wrap;html=1;align=center;fillColor=#f8f8f8;strokeColor=#999999;fontSize=10;` |
| Attribute connector | — | `endArrow=none;html=1;rounded=0;strokeColor=#888888;` |
| Partial-participation connector | — | `endArrow=none;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;` |
| Total-participation connector (double line) | — | `shape=link;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;` |
| Constraint note | 300×90 | `shape=note;whiteSpace=wrap;html=1;size=14;align=left;spacingLeft=6;spacingRight=6;fillColor=#f8cecc;strokeColor=#b85450;fontSize=11;` |
| Title / legend | free | `text;html=1;align=left;verticalAlign=top;fontSize=11;whiteSpace=wrap;` (the legend adds `strokeColor=#999999;fillColor=#fafafa;spacing=8;`) |

Color code: blue for entities, yellow for relationships, white for attributes, pink for rules, grey for references.

### 4.6 Id convention

| Prefix | Used for | Example |
|---|---|---|
| `E_<entity>` | Entities | `E_order`, `E_orderline` |
| `R_<relationship>` | Relationship diamonds | `R_places`, `R_contains` |
| `a<n>` | Attributes | `a15` |
| `s<n>` | Sub-attributes of composites | `s22` |
| `e<n>` | Connectors | `e40` |
| `n<n>`, `t<n>`, `l<n>` | Notes, title, legend | `n80` |

Ids must be **unique within each page**. Stable ids (`E_`, `R_`) keep git diffs meaningful between versions of a diagram.

### 4.7 Minimal complete example

A single page with `Order (1) —Contains— (N) Order Line`, the key of `Order` and the partial key of `Order Line`:

```xml
<mxfile host="app.diagrams.net" agent="generated" version="24.0.0">
  <diagram id="example" name="Example">
    <mxGraphModel grid="1" gridSize="10" page="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- Strong entity -->
        <mxCell id="E_order" value="Order" style="whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">
          <mxGeometry x="100" y="100" width="150" height="56" as="geometry"/>
        </mxCell>
        <!-- Weak entity -->
        <mxCell id="E_orderline" value="Order Line" style="shape=ext;margin=3;double=1;whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">
          <mxGeometry x="100" y="400" width="150" height="56" as="geometry"/>
        </mxCell>
        <!-- Identifying relationship -->
        <mxCell id="R_contains" value="Contains" style="shape=rhombus;double=1;perimeter=rhombusPerimeter;whiteSpace=wrap;html=1;align=center;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="110" y="241" width="130" height="74" as="geometry"/>
        </mxCell>
        <!-- Order side: cardinality 1, partial participation -->
        <mxCell id="e1" value="1" style="endArrow=none;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_contains" target="E_order">
          <mxGeometry x="0.6" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry>
        </mxCell>
        <!-- Order Line side: cardinality N, total participation (double line) -->
        <mxCell id="e2" value="N" style="shape=link;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_contains" target="E_orderline">
          <mxGeometry x="0.6" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry>
        </mxCell>
        <!-- Key attribute of Order -->
        <mxCell id="a1" value="Order ID" style="ellipse;whiteSpace=wrap;html=1;align=center;fillColor=#ffffff;strokeColor=#666666;fontSize=11;fontStyle=4;" vertex="1" parent="1">
          <mxGeometry x="330" y="40" width="124" height="44" as="geometry"/>
        </mxCell>
        <mxCell id="e3" style="endArrow=none;html=1;rounded=0;strokeColor=#888888;" edge="1" parent="1" source="a1" target="E_order">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <!-- Partial key of Order Line -->
        <mxCell id="a2" value="&lt;span style=&quot;border-bottom: 1px dashed;&quot;&gt;Line #&lt;/span&gt;" style="ellipse;whiteSpace=wrap;html=1;align=center;fillColor=#ffffff;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="330" y="470" width="124" height="44" as="geometry"/>
        </mxCell>
        <mxCell id="e4" style="endArrow=none;html=1;rounded=0;strokeColor=#888888;" edge="1" parent="1" source="a2" target="E_orderline">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### 4.8 Common mistakes

| Mistake | Consequence | How to avoid it |
|---|---|---|
| Missing the `id="0"` / `id="1"` cells | The file does not open, or opens empty | Always declare them first |
| `source`/`target` pointing to a non-existent id | Dangling connector that does not follow shapes | Validate references before committing (see §5) |
| Unescaped `&`, `<` or `"` in `value` | Invalid XML | Always escape attribute values |
| Duplicate ids on a page | Shapes disappear or overwrite each other | Follow the id convention in §4.6 |
| Drawing foreign keys as attributes | The model becomes physical | Draw them as relationships |
| Attributes on reference entities | Duplication and inconsistencies between pages | Attributes only on the entity's home page |
| Arrowheads on connectors | Not Chen notation | Always `endArrow=none` (or `shape=link`) |
| Compressed (base64) content | Unreadable and not diffable in git | Save uncompressed |

---

## 5. Review checklist

Use this list when creating a diagram and when reviewing someone else's.

**Notation and modeling**
- [ ] Only conceptual elements: no data types, foreign keys, indexes or SQL.
- [ ] Every strong entity has exactly one underlined key attribute; every weak entity has none (it uses a partial key instead).
- [ ] Every weak entity has a partial key, an identifying relationship (double diamond) and total participation.
- [ ] Every relationship has a name (verb) and a cardinality on each end.
- [ ] Total participation (double line) is used only for confirmed rules.
- [ ] Attributes of M:N relationships hang from the diamond.
- [ ] Rules that cannot be drawn are written as `Constraint:` / `Rule:` notes.
- [ ] Open questions and assumptions are listed in the pull request or design doc that accompanies the diagram.

**Organization**
- [ ] The `1 - Overview` page holds every entity and relationship, without attributes (multi-page models).
- [ ] Every entity has exactly one home page with all its attributes.
- [ ] Reference entities use the grey dashed style and have no attributes.
- [ ] Every page has a title and a legend.

**`.drawio` format**
- [ ] The XML is valid and opens in https://app.diagrams.net/ without warnings.
- [ ] Every connector has an existing `source` and `target`.
- [ ] Styles and sizes match the catalog in §4.5.
- [ ] The file is saved uncompressed in the project's `db-design/` folder, named per §3.3.

Quick reference check (Python, no dependencies):

```python
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
for page in root:
    cells = page.findall('.//mxCell')
    ids = [c.get('id') for c in cells]
    dupes = {i for i in ids if ids.count(i) > 1}
    dangling = [c.get('id') for c in cells
                if c.get('edge') and (c.get('source') not in ids or c.get('target') not in ids)]
    print(f"{page.get('name')}: {len(cells)} cells, duplicate ids: {sorted(dupes)}, dangling edges: {dangling}")
```

Run it with `python3 check_drawio.py db-design/conceptual-erd.drawio`.

---

## 6. Glossary

| Term | Definition |
|---|---|
| Entity | A business object with its own existence and identity |
| Weak entity | An entity whose identity depends on another (its owner) |
| Attribute | A property describing an entity or a relationship |
| Key | The attribute(s) that uniquely identify an instance |
| Partial key | The attribute that identifies a weak entity within its owner |
| Relationship | A meaningful association between entities |
| Identifying relationship | The relationship that gives a weak entity its identity |
| Cardinality ratio | The maximum number of associated instances (1, N, M) |
| Total / partial participation | Whether taking part in a relationship is mandatory or optional for each instance |
| Conceptual model | A technology-independent representation of the business data |
| Physical model | The concrete implementation: tables, columns, types, indexes (outside the scope of these ERDs) |
