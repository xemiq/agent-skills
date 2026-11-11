# Worked example: Task Tracker

This is the full run behind SKILL.md §11. Use it as a demonstration and as an acceptance test. An
agent given the same description and the same answers must produce an equivalent model (same
entities, keys, relationships, cardinalities and participation).

## 1. User request

> Create the ERD for our task tracker. Here is the domain:
>
> Teams have a name, unique across the company, and we record the date each team was created.
> Users have an email (unique), a full name (first and last name), one or more phone numbers, and a
> flag saying whether they are active. Users belong to teams and have a role in each team.
> Projects belong to exactly one team. A project has a code, unique across the company, a name and a
> start date. Each project is split into tasks numbered 1, 2, 3… within the project. A task has a
> title, a status and estimated hours. A task can be assigned to a user. Users can mentor other
> users. A project's total estimated hours is calculated from its tasks.

## 2. Analysis (Steps 1–4 of the workflow)

| Candidate | Decision | Basis |
|---|---|---|
| Team | Strong entity, key `Team name` | stated ("unique across the company") |
| User | Strong entity, key `Email` | stated |
| Project | Strong entity, key `Project code` | stated |
| Task | Weak entity of Project, partial key `Task #` | stated ("numbered … within the project") |
| Full name | Composite (`First name`, `Last name`) | stated |
| Phone numbers | Multivalued + `Constraint:` note for the minimum | stated ("one or more") |
| Total estimated hours | Derived | stated ("calculated") |
| Team – Project | `Owns`, 1:N, Project total | stated ("belong to exactly one team") |
| Project – Task | `Contains`, identifying, 1:N, Task total | stated |
| User – Team | `Member of`, maxima not stated, role placement ambiguous | **ask** (B2, B6) |
| User – Task | `Assigned to`, both maxima unclear | **ask** (B2) |
| User – User | `Mentors`, cardinality unknown | **ask** |
| Status | Simple attribute, values unknown | **ask** (possible constraint) |

## 3. Clarification round (Step 5). The agent stops and waits.

> Before I generate the ERD, please check this draft and answer 7 questions. Values marked
> *(default)* are my assumptions, not facts from your description.
>
> **Draft model**
> - **Team**: key `Team name`; `Created on`
> - **User**: key `Email`; composite `Full name` (`First name`, `Last name`); multivalued `Phone numbers`; `Is active`
> - **Project**: key `Project code`; `Name`; `Start date`; derived `Total estimated hours`
> - **Task**: weak, owned by Project; partial key `Task #`; `Title`; `Status`; `Estimated hours`
> - User (?, partial *(default)*) —**Member of**— (?, partial *(default)*) Team, attribute `Team role`?
> - Team (1, partial *(default)*) —**Owns**— (N, total) Project
> - Project (1, partial *(default)*) =**Contains**= (N, total) Task, identifying
> - User (?, partial *(default)*) —**Assigned to**— (?, partial *(default)*) Task
> - User (?, mentor, partial *(default)*) —**Mentors**— (?, mentee, partial *(default)*) User
> - Note: `Constraint: A User has at least one phone number.`
>
> 1. **(blocking)** Mentors: how many mentors can a user have, and how many mentees can a mentor have?
> 2. **(blocking)** Assigned to: how many users can one task be assigned to at the same time, and how many tasks can one user have?
> 3. **(blocking)** Member of: can a user belong to several teams, and does a user have one role per team
>    or one role overall? *(recommended: several teams, role per team, as an attribute of Member of)*
> 4. **(non-blocking)** Must every team have at least one member? *(default: no, partial)*
> 5. **(non-blocking)** Must every team own at least one project? *(default: no, partial)*
> 6. **(non-blocking)** What values can a task's status take? *(default: no constraint note)*
> 7. **(non-blocking)** Can a user be their own mentor? *(default: no rule drawn)*
>
> Please answer, or correct anything in the draft.

## 4. User answers

> 1. One mentor at most; a mentor can have many mentees.
> 2. One user at most per task; a user can have many tasks.
> 3. Several teams, and the role is per team.
> 4. Yes, every team has at least one member.
> 5. Not decided yet.
> 6. To do, In progress, Done.
> 7. No, never.
> Everything else in the draft is fine.

## 5. Result (Steps 6–10)

- Model: [model.json](model.json). Answer 5 stays in `open_questions` and is drawn as partial
  participation, because the user explicitly left it undecided. The other `(default)` values were
  shown in the draft and confirmed ("everything else is fine"), so they are recorded with
  `confirmed_by: "user"`. Every decision is in `assumptions` with its source.
- Command (run from the repository root): `python3 <skill>/scripts/render_erd.py model.json --out-dir db-design`.
  The committed copy was produced with `--out-dir examples/task-tracker/db-design`.
- Output (committed under [db-design/](db-design/)):
  - [conceptual-erd.drawio](db-design/conceptual-erd.drawio): 1 page, 4 entities, 5 relationships, 15 attributes (+2 sub-attributes), 3 notes
  - [conceptual-erd.summary.md](db-design/conceptual-erd.summary.md)
  - [conceptual-erd.model.json](db-design/conceptual-erd.model.json)
- Validation: `python3 <skill>/scripts/validate_erd.py db-design/conceptual-erd.drawio` reports `PASS: 0 error(s), 0 warning(s)`.

### Acceptance criteria (for testing the skill)

1. The agent asks before writing any file. The draft shows both ends of every relationship, with
   defaults marked, and the questions cover at least the blocking items 1–3.
2. The agent writes no file until the answers arrive.
3. `Project` participation in `Owns` is total (stated). `Team` participation in `Owns` is partial,
   and its question is listed as open (answer 5).
4. `Task` is weak, with `Task #` as its partial key and `Contains` as a double diamond.
5. `Team role` hangs from the `Member of` diamond, not from an entity.
6. No data types, no `User ID` / `Project ID` attributes inside other entities.
7. The validator passes, and the chat reply includes the summary (entities, relationships, confirmed
   assumptions, open questions).
