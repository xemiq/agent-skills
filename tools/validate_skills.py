#!/usr/bin/env python3
"""Repository-wide checks for every skill in skills/ (run locally and in CI).

Usage (from the repository root):
  python3 tools/validate_skills.py            # spec + repo policy checks, then each skill's tests
  python3 tools/validate_skills.py --no-tests # checks only

Checks, following the Agent Skills specification (https://agentskills.io/specification)
plus this repository's policy:
  - skills/<name>/SKILL.md exists, with YAML front matter between '---' lines
  - name: 1-64 chars, lowercase letters/digits/hyphens, no leading/trailing/double hyphen,
    equal to the folder name, unique in the repository
  - description: 1-1024 chars; compatibility: <= 500 chars; metadata: string -> string map
  - only spec fields at the top level (name, description, license, compatibility, metadata, allowed-tools)
  - repo policy: license 'Apache-2.0'; metadata.author 'XemiQ'; metadata.version is semver and is
    listed in the skill's CHANGELOG.md; metadata.repository set; SKILL.md <= 500 lines
  - .claude-plugin/marketplace.json lists exactly the skills that exist
  - each skill's tests/test_skill.py passes (if present)
Requires PyYAML (pip install pyyaml).
"""
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
REPO_URL = "https://github.com/xemiq/agent-skills"


def front_matter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)), text


def check_skill(folder, errors):
    path = os.path.join(SKILLS, folder, "SKILL.md")
    where = f"skills/{folder}"
    if not os.path.isfile(path):
        errors.append(f"{where}: missing SKILL.md")
        return None
    fm, text = front_matter(path)
    if not isinstance(fm, dict):
        errors.append(f"{where}/SKILL.md: missing or invalid YAML front matter")
        return None
    extra = set(fm) - SPEC_FIELDS
    if extra:
        errors.append(f"{where}: front matter fields not in the spec: {sorted(extra)} (put them under metadata)")
    name = fm.get("name")
    if not isinstance(name, str) or not (1 <= len(name) <= 64) or not NAME_RE.match(name):
        errors.append(f"{where}: name {name!r} must be 1-64 chars of a-z, 0-9 and single hyphens")
    elif name != folder:
        errors.append(f"{where}: name {name!r} must equal the folder name")
    desc = fm.get("description")
    if not isinstance(desc, str) or not (1 <= len(desc.strip()) <= 1024):
        errors.append(f"{where}: description must be 1-1024 characters")
    comp = fm.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or len(comp) > 500):
        errors.append(f"{where}: compatibility must be a string of at most 500 characters")
    if fm.get("license") != "Apache-2.0":
        errors.append(f"{where}: license must be 'Apache-2.0' (repository policy)")
    meta = fm.get("metadata")
    if not isinstance(meta, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in meta.items()):
        errors.append(f"{where}: metadata must be a map of strings to strings (quote versions: \"0.1.0\")")
        meta = {}
    if meta.get("author") != "XemiQ":
        errors.append(f"{where}: metadata.author must be 'XemiQ'")
    if meta.get("repository") != REPO_URL:
        errors.append(f"{where}: metadata.repository must be {REPO_URL}")
    version = meta.get("version", "")
    if not SEMVER_RE.match(version):
        errors.append(f"{where}: metadata.version {version!r} must be MAJOR.MINOR.PATCH")
    changelog = os.path.join(SKILLS, folder, "CHANGELOG.md")
    if not os.path.isfile(changelog):
        errors.append(f"{where}: missing CHANGELOG.md")
    elif version and f"## {version}" not in open(changelog, encoding="utf-8").read():
        errors.append(f"{where}: CHANGELOG.md has no '## {version}' entry")
    lines = len(text.splitlines())
    if lines > 500:
        errors.append(f"{where}: SKILL.md has {lines} lines; keep it under 500 (move detail to references/)")
    return name


def check_marketplace(names, errors):
    path = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as ex:
        errors.append(f".claude-plugin/marketplace.json: {ex}")
        return
    listed = []
    for plugin in data.get("plugins", []):
        for s in plugin.get("skills", []):
            listed.append(os.path.basename(os.path.normpath(s)))
            if not os.path.isfile(os.path.join(ROOT, s, "SKILL.md")):
                errors.append(f"marketplace.json: plugin {plugin.get('name')!r} lists missing skill {s!r}")
    for n in names:
        if n not in listed:
            errors.append(f"marketplace.json: skill {n!r} is not listed in any plugin")
    dupes = {x for x in listed if listed.count(x) > 1}
    if dupes:
        errors.append(f"marketplace.json: skills listed more than once: {sorted(dupes)}")


def run_tests(folder, errors):
    test = os.path.join(SKILLS, folder, "tests", "test_skill.py")
    if not os.path.isfile(test):
        print(f"  {folder}: no tests/test_skill.py (skipped)")
        return
    r = subprocess.run([sys.executable, test], capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    print(f"  {folder}: {last}")
    if r.returncode != 0:
        errors.append(f"skills/{folder}: tests failed\n{r.stdout}\n{r.stderr}")


def main():
    errors = []
    if not os.path.isdir(SKILLS):
        sys.exit("skills/ folder not found")
    folders = sorted(d for d in os.listdir(SKILLS)
                     if os.path.isdir(os.path.join(SKILLS, d)) and not d.startswith("."))
    names = [n for n in (check_skill(d, errors) for d in folders) if n]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        errors.append(f"duplicate skill names: {sorted(dupes)}")
    check_marketplace(names, errors)
    print(f"Checked {len(folders)} skill(s): {', '.join(folders)}")
    if "--no-tests" not in sys.argv:
        for d in folders:
            run_tests(d, errors)
    for e in errors:
        print(f"ERROR {e}")
    print("PASS" if not errors else f"FAIL: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
