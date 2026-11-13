# Mapping sources to the conceptual model

How to turn each kind of input into entities, attributes and relationships. Each row says whether
the result is **derived** (it may be recorded with `confirmed_by: "schema"` or `"stated"`) or needs a
**question** (it must be asked, see SKILL.md §3).

## 1. Natural-language domain description

| Wording in the description | Model element | Status |
|---|---|---|
| Nouns with their own identity and lifecycle ("customer", "order") | Entity | Derived. Ask if it is only a property ("address", "category") |
| Properties of a noun ("an order has a date") | Attribute | Derived |
| Verbs that link two nouns ("customers place orders") | Relationship named with that verb | Derived |
| **Minimum** wording about entity X: "every X must / always / each X has at least one / X cannot exist without" | `total: true` on **X's own end** (double line next to X) | Derived (`stated`) |
| **Minimum** wording "X may / can / optionally / zero or more" | `total: false` on X's end | Derived (`stated`) |
| **Maximum** wording "each X has / belongs to **exactly one / at most one / a single** Y" | `card: "1"` on **Y's end** (the label next to Y: one Y per X) | Derived (`stated`) |
| **Maximum** wording "each X has **many / several / one or more / a list of** Y" | `card: "N"` (or `"M"` in M:N) on **Y's end** | Derived (`stated`) |
| Worked reading: "Every project belongs to exactly one team" | Project end: `total: true` (minimum). Team end: `card: "1"` (maximum). Team's own participation and the Project-side maximum come from other statements, or are asked | — |
| Worked reading: "A team owns one or more projects" | Team end: `total: true` ("at least one"). Project end: `card: "N"` ("many") | — |
| Maximum stated in one direction only | — | **Question** (B2) for the other direction |
| "must have" alone ("every team must have members") | Minimum only (`total` on Team). It says nothing about the maximum | Derived for the minimum; the maximum is B2 |
| "unique / identified by / no two X share" | Key attribute | Derived (`stated`). Several unique attributes and no stated identifier → **question** (B9). The non-key ones become `Constraint: … is unique.` notes |
| Identifier made of several values ("a flight is identified by its number and date") | One composite key attribute (`kind: "key"` + `parts`) | Derived (`stated`) |
| "numbered within / line 1, 2, 3 of" | Weak entity + partial key | Derived (`stated`) |
| "calculated / total of / derived from" | Derived attribute | Derived |
| "one or more phone numbers / tags" (simple values) | Multivalued attribute **plus** a note for the minimum: `Constraint: A User has at least one phone number.` | Derived. Ask if the values have their own properties (then it is an entity) |
| Value limits on an attribute ("between 1 and 5 images", "at most 3 tags") | `Constraint:` note | Derived (`stated`) |
| Unclear whether a property holds one value or several | — | **Question** (B10). Never assume single-valued |
| Values with their own properties or history (e.g. price history with dates) | Entity, or a weak entity | **Question** if unclear |
| Limits, ranges, either/or, conditional rules | `Constraint:` / `Rule:` note | Derived only if stated. Never invented |

## 2. SQL DDL / migrations (any dialect)

| Schema pattern | Model element |
|---|---|
| Table with business meaning | Strong entity. Name = singular Title Case (`order_lines` → `Order Line`) |
| `UNIQUE NOT NULL` business column (email, sku, code, number) | **Key** (natural key preferred, `schema`). The surrogate `id` is omitted. If there are several such columns, ask which one identifies the entity (B9); the others become `Constraint: … is unique.` notes |
| Composite `UNIQUE NOT NULL` of business columns (no FK) | Composite key (`kind: "key"` + `parts`) |
| Only a surrogate `id` (serial/uuid), no natural key | Key = conceptual identifier `<Entity> ID` (`convention`) |
| PK = (FK to parent + discriminator such as `line_no`) | Weak entity. Partial key = discriminator. Identifying relationship with the parent |
| FK column `x_id` → `X` | Relationship (never an attribute). FK side = `N`, referenced side = `1` |
| FK `NOT NULL` | Total participation on the FK-holding side (`schema`) |
| FK nullable | Partial participation on the FK-holding side |
| FK with `UNIQUE` | 1:1 instead of 1:N |
| Referenced (parent) side participation | **Never derivable** from the schema. Partial, plus an open question if it matters |
| Junction table: 2 FKs forming the PK/unique, no own identity | M:N relationship. Extra columns become relationship attributes |
| Junction table referenced by other tables, or with its own lifecycle | Entity with two 1:N relationships. Ask for the name if unclear |
| Junction table allowing the same pair several times (history: no unique on the pair) | Entity (e.g. `Loan`), not an M:N relationship |
| Self-referencing FK (`manager_id → employees`) | Recursive relationship. Roles taken from the column (`manager` / `report`); ask if unclear |
| Value table `product_tags(product_id, tag)` | Multivalued attribute `Tags` of `Product` |
| Column groups (`address_street`, `address_city`) or embedded/value objects | Composite attribute |
| Generated/computed columns, view aggregates, totals kept by triggers | Derived attribute |
| `CHECK` / enum constraints with business meaning | `Constraint:` note (`schema`) |
| Polymorphic FK (`owner_type` + `owner_id`) | One relationship per target + exclusive-OR `Constraint:` note. **Question**: confirm the targets |
| Inheritance (single-table `type` column, class-table 1:1 PK=FK) | **Question.** Default: one entity with a `Type` attribute, plus a `Rule:` note listing the types. If subtypes have their own attributes or relationships: subtype entities linked by a 1:1 `Is a` relationship (total on the subtype side), plus a `Constraint:` note about disjoint/overlapping subtypes |
| Indexes, partitions, triggers, sequences, storage, `ON DELETE`, grants | Omitted |
| Technical columns (`created_at`, `updated_at`, `deleted_at`, `version`, `row_version`, sync flags, tenant id) | Omitted, and listed in the model's `omitted` field (printed in the summary). Include one only if the user confirms it has business meaning |
| Data types, lengths, defaults | Omitted |

## 3. ORM models

Apply section 2, reading the ORM's declarations:

| ORM | Relationship / key declarations to read |
|---|---|
| Prisma | `@relation`, `@id`, `@@id` (composite → maybe weak), `@unique`, `@@unique`, optional `?` (nullable = partial), implicit M:N lists |
| Django | `ForeignKey(null=…)`, `OneToOneField`, `ManyToManyField(through=…)`, `unique=True`, `unique_together` / `UniqueConstraint`, `@property` (derived) |
| SQLAlchemy | `ForeignKey`, `relationship(secondary=…)`, `nullable=`, `unique=`, `UniqueConstraint`, `hybrid_property` (derived) |
| TypeORM / MikroORM | `@ManyToOne({nullable})`, `@OneToMany`, `@OneToOne` + `@JoinColumn`, `@ManyToMany` + `@JoinTable`, `@Unique`, `@PrimaryColumn` |
| Sequelize | `belongsTo`, `hasMany`, `hasOne`, `belongsToMany({through})`, `allowNull`, `unique` |
| Entity Framework | Navigation properties, `[Required]`, `HasOne/WithMany`, `IsRequired()`, `HasKey` (composite), owned types (composite attribute) |
| JPA / Hibernate | `@ManyToOne(optional=…)`, `@OneToMany`, `@ManyToMany` + `@JoinTable`, `@Embeddable` (composite), `@ElementCollection` (multivalued), `@IdClass` / `@EmbeddedId` |
| ActiveRecord (Rails) | `belongs_to (optional: true)`, `has_many`, `has_many :through`, `has_and_belongs_to_many`, validations (`presence`, `uniqueness`), `db/schema.rb` |
| GORM (Go) | struct tags `foreignKey`, `many2many`, `not null`, `uniqueIndex` |
| Mongoose / document stores | `ref` → relationship. Embedded sub-document arrays → weak entity or multivalued/composite attribute (**question** if they have their own identity) |

Validation rules in application code (e.g. `presence: true`) count as `schema` confirmation only when
they are enforced for every write path. If you are unsure, ask.

## 4. Existing ERD files

- `db-design/*.model.json` from a previous run of this skill is the **source of truth**. Load the
  latest version (highest `-vN`), apply the requested changes, and render a new version.
- A `.drawio` file without a model: decompress it if needed (`validate_erd.py --decompress`), read
  the entities, attributes and relationships back from the shapes, rebuild the model, then apply the
  changes.
- Images or PDFs of diagrams: read them only if you can view images. Otherwise ask for a text source.
  Treat what you read as a draft to confirm with the user.

## 5. Naming conversion

| Physical | Conceptual |
|---|---|
| `order_lines`, `OrderLines`, `tblOrderLine` | `Order Line` |
| `unit_price`, `unitPrice` | `Unit price` |
| `is_active`, `active` (boolean) | `Is active` |
| `qty`, `addr` (abbreviations) | `Quantity`, `Address` (expand when unambiguous, otherwise ask) |
| `customer_id` in `orders` | Relationship `Customer — Places — Order` (verb from the domain, or ask) |

Relationship verbs are not in the schema. Pick the plain domain verb (`Places`, `Contains`,
`Assigned to`). When no verb is evident, propose one in the clarification round so the user can
rename it.
