# Contributing to XemiQ Agent Skills

Thank you for helping. This guide covers how skills are organised, how to add or change one, and
how releases work.

## Ground rules

- **One skill per folder:** `skills/<skill-name>/`. The folder name and the `name` field of its
  `SKILL.md` are identical.
- **Self-contained:** someone may install a single skill on its own. It must not reference files
  outside its own folder. If two skills need the same reference, each keeps its own copy.
- **Agent-agnostic:** instructions say "ask the user", "run", "read the file". Never use one
  vendor's tool names. Scripts use only the Python 3.9+ standard library, unless a dependency is
  unavoidable and documented in `compatibility`.
- **Deterministic and safe:** skills never overwrite user files silently. They ask before acting on
  ambiguous input and validate their own output.

## Naming

`<area>-<capability>[-<variant>]`, using lowercase letters, digits and single hyphens, at most 64
characters.

| Area prefix | Scope | Example |
|---|---|---|
| `db-` | Database design and modeling | `db-erd-chen` |

Propose a new prefix in an issue before adding the first skill of a new area.

## Skill folder template

```
skills/<skill-name>/
├── SKILL.md          required; under 500 lines
├── CHANGELOG.md      required; one "## X.Y.Z — YYYY-MM-DD" section per release
├── references/       detailed docs the agent reads on demand
├── scripts/          deterministic helpers (stdlib Python preferred)
├── examples/         at least one worked example: input → output
└── tests/
    └── test_skill.py run by CI; must exit 0
```

Front matter (only spec fields at the top level; everything else goes under `metadata`, as strings):

```yaml
---
name: <skill-name>
description: >-
  What the skill does and when to use it (keywords, intents). At most 1024 characters.
license: Apache-2.0
compatibility: What the agent needs (tools, runtimes). At most 500 characters.
metadata:
  author: XemiQ
  version: "0.1.0"
  repository: https://github.com/xemiq/agent-skills
---
```

A good skill covers: trigger conditions, scope (does / does not), inputs, clarifying questions, a
step-by-step workflow, the output specification, notation or format rules, a validation checklist,
error handling, a worked example, and extensibility notes. Keep in `SKILL.md` what the agent needs
on every run, and move what it needs only in some runs (rare edge cases, fallbacks, maintenance)
to `references/`, with a line in `SKILL.md` saying when to read each file. Metadata belongs in the
front matter, not in a section. `skills/db-erd-chen/SKILL.md` is the reference implementation.

## Workflow

1. Open an issue that describes the skill or change.
2. Create a branch: `feat/<skill-name>-<topic>` or `fix/<skill-name>-<topic>`.
3. Make the change, then run the checks from the repository root:
   ```bash
   python3 -m pip install pyyaml
   python3 tools/validate_skills.py
   ```
4. Bump `metadata.version` and add a CHANGELOG entry (see Versioning).
5. Open a pull request. CI must be green, and one maintainer must approve.

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/), with the skill name as the scope:

```
feat(db-erd-chen): support ternary relationship attributes
fix(db-erd-chen): avoid diamond overlap on vertical pairs
docs(repo): add install instructions for Cursor
```

## Versioning and releases

- Each skill uses semantic versioning in `metadata.version`. New skills start at `0.1.0`. While a
  skill is `0.x`, it is a pre-release: breaking changes bump MINOR (`0.1.0` → `0.2.0`), and fixes
  bump PATCH. Release `1.0.0` once the skill has been used on real projects and its input/output
  contract is stable. From `1.0.0` on:
  - MAJOR: the output contract or input format changes incompatibly;
  - MINOR: new capabilities or checks;
  - PATCH: fixes.
- Repository releases are git tags `vX.Y.Z` on `main`, with GitHub release notes that list the skill
  versions they contain. Users can pin a tag with `npx skills add xemiq/agent-skills@vX.Y.Z --skill <name>`.
- When adding a skill, also add it to the table in `README.md` and to a plugin in
  `.claude-plugin/marketplace.json`. The validator fails if a skill is missing from the manifest.

## License

By contributing, you agree that your contributions are licensed under the Apache License 2.0.
