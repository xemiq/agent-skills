# Task Tracker — Conceptual ERD summary

- Diagram: `conceptual-erd.drawio` (diagrams.net XML, uncompressed)
- Pages: 1 - Conceptual ERD
- Source: Domain description (examples/task-tracker/input.md) plus answers to 7 clarifying questions

## Entities (4)

| Entity | Type | Key | Attributes | Home page |
|---|---|---|---|---|
| Team | Strong | Team name | Created on | 1 - Conceptual ERD |
| User | Strong | Email | Full name (First name, Last name), Phone numbers [multivalued], Is active | 1 - Conceptual ERD |
| Project | Strong | Project code | Name, Start date, Total estimated hours [derived] | 1 - Conceptual ERD |
| Task | Weak | Task # (partial key) | Title, Status, Estimated hours | 1 - Conceptual ERD |

## Relationships (5)

| Relationship | Ends (cardinality, participation) | Ratio | Attributes |
|---|---|---|---|
| Member of | User (M, partial) — Team (N, total) | M:N | Team role |
| Owns | Team (1, partial) — Project (N, total) | 1:N | — |
| Contains (identifying) | Project (1, partial) — Task (N, total) | 1:N | — |
| Assigned to | User (1, partial) — Task (N, partial) | 1:N | — |
| Mentors | User as mentor (1, partial) — User as mentee (N, partial) | 1:N (recursive) | — |

## Constraints and business rules

- Constraint: A User has at least one phone number.
- Constraint: Task status is one of To do, In progress, Done.
- Rule: A user cannot mentor themselves.

## Confirmed assumptions and decisions

- Team name is unique across the company and identifies a Team. (confirmed by: stated)
- Every project belongs to exactly one team (total participation of Project in Owns). (confirmed by: stated)
- Tasks are numbered within their project, so Task is a weak entity of Project with partial key Task #. (confirmed by: stated)
- Every team has at least one member (total participation of Team in Member of). (confirmed by: user)
- A task is assigned to at most one user; unassigned tasks are allowed. (confirmed by: user)
- A user can have many tasks assigned. (confirmed by: user)
- A user can belong to several teams. (confirmed by: user)
- Partial participation, shown as (default) in the confirmed draft: User in Member of, Project in Contains, User and Task in Assigned to, both ends of Mentors. (confirmed by: user)
- A user has at most one mentor and may mentor many users. (confirmed by: user)
- The role is held per team membership, so Team role is an attribute of Member of. (confirmed by: user)
- Task status values are To do, In progress, Done. (confirmed by: user)
- A user cannot mentor themselves. (confirmed by: user)
- Created on (Team) and Is active (User) are business data requested in the description, not technical audit columns. (confirmed by: stated)

## Open questions (not modeled as rules; drawn in the least restrictive form)

- Must every team own at least one project? Drawn as partial participation until confirmed.

## Omitted from the conceptual model

- Nothing.
