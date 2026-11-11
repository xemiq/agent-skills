# XemiQ Agent Skills

Reusable skills for AI coding agents, made by [XemiQ](https://xemiqlab.com/en) ([GitHub](https://github.com/xemiq)).

A skill is a folder with a `SKILL.md` file plus the references, scripts and examples it needs, so
that an agent can do one kind of task reliably and the same way every time. These skills follow
the open [Agent Skills specification](https://agentskills.io/specification). They work with any
agent that supports `SKILL.md` skills (Claude Code, Antigravity, Cursor, Codex and others), and
they don't depend on any vendor-specific tool.

[![validate-skills](https://github.com/xemiq/agent-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/xemiq/agent-skills/actions/workflows/validate.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## Skills

| Skill | Area | What it does | Version |
|---|---|---|---|
| [`db-erd-chen`](skills/db-erd-chen/) | Database design | Generates conceptual Entity-Relationship Diagrams in Chen notation as diagrams.net (draw.io) files, from a domain description, SQL DDL or ORM models. It asks clarifying questions first, never assumes business rules, validates its output, and writes a summary of the model and its assumptions | 0.1.1 (pre-release) |

## Install

With the [skills CLI](https://skills.sh) (works with most agents):

```bash
# list the skills in this repository
npx skills add xemiq/agent-skills --list

# install one skill into the current project
npx skills add xemiq/agent-skills --skill db-erd-chen

# pin a release
npx skills add xemiq/agent-skills@v0.1.1 --skill db-erd-chen
```

As a Claude Code plugin marketplace:

```text
/plugin marketplace add xemiq/agent-skills
/plugin install db-design@xemiq-agent-skills
```

Manually: copy `skills/<skill-name>/` into your agent's skills folder (for example
`.claude/skills/` or `.agents/skills/`). Each skill is self-contained.

## Using a skill

Ask your agent in plain language, e.g. *"Create the ERD for this project from the Prisma schema"*.
The agent loads the matching skill from its description and follows its `SKILL.md`. Each skill
folder documents its inputs, outputs, and a worked example (see
[`db-erd-chen/examples/`](skills/db-erd-chen/examples/)).

## Repository layout

```
skills/<skill-name>/      one folder per skill (name = folder name, Agent Skills spec)
  SKILL.md                instructions + front matter (name, description, license, metadata)
  CHANGELOG.md            per-skill semantic versioning
  references/ scripts/ examples/ tests/
tools/validate_skills.py  repository checks (spec, policy, tests); also run by CI
.claude-plugin/           Claude Code plugin marketplace manifest
.github/workflows/        CI
```

Skill names start with a prefix for their area (`db-` for database design), so related skills stay
grouped in listings and names never collide.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Questions and bug
reports go to [GitHub Issues](https://github.com/xemiq/agent-skills/issues).

## Acknowledgements

Built with the help of AI coding agents. Every skill is reviewed, tested and validated by the XemiQ team.

## License

[Apache License 2.0](LICENSE). Copyright 2026 [XemiQ](https://xemiqlab.com/en). See [NOTICE](NOTICE).
