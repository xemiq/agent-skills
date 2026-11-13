#!/usr/bin/env python3
"""render_erd.py - render a conceptual ERD model (JSON) into an uncompressed diagrams.net
(.drawio) file in Chen notation, using the mandatory style catalog.

Usage:
  python3 render_erd.py MODEL.json --out-dir db-design [--name conceptual-erd]
  python3 render_erd.py MODEL.json --out db-design/conceptual-erd-v2.drawio [--force]
  python3 render_erd.py MODEL.json --check          # validate the model only, write nothing

With --out-dir the next free version name is chosen automatically
(conceptual-erd.drawio, then conceptual-erd-v2.drawio, -v3 ...). Existing files are never
overwritten unless --out and --force are both given.

Writes three files with the same base name:
  <base>.drawio        the diagram (the deliverable)
  <base>.summary.md    human-readable summary (entities, relationships, rules, assumptions)
  <base>.model.json    normalized copy of the input model (lets the diagram be regenerated)

The model format is documented in references/model-schema.md. Standard library only.
Exit codes: 0 ok (warnings may be printed), 1 invalid model, 2 file-system error.
"""
import argparse
import html
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import erd_catalog as C  # noqa: E402

ATTR_KINDS = {"simple", "key", "partial_key", "multivalued", "derived", "composite"}
CARDS = {"1", "N", "M"}
CONFIRMATION_SOURCES = {"user", "schema", "stated", "convention"}
ID_RE = re.compile(r"^[a-z][a-z0-9]*$")

SIZE = {
    "entity": (150, 56), "relationship": (130, 74), "attribute": (124, 44),
    "sub_attribute": (104, 34), "note": (300, 90), "specialization": (40, 40),
}
DETAIL_SPACING = (560, 440)
OVERVIEW_SPACING = (380, 300)


class ModelError(Exception):
    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = problems


# --------------------------------------------------------------------------- model checks
def _is_str(x):
    return isinstance(x, str) and x.strip() != ""


def _is_pair(x):
    return (isinstance(x, list) and len(x) == 2 and
            all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x))


def check_types(m):
    """Structural type checks, run before anything else so malformed input never crashes."""
    p = []
    if not isinstance(m, dict):
        return ["model root must be a JSON object"]

    def lst(obj, key, where, required=False):
        v = obj.get(key)
        if v is None:
            if required:
                p.append(f"{where}: '{key}' is required and must be a list")
            return []
        if not isinstance(v, list):
            p.append(f"{where}: '{key}' must be a list")
            return []
        return v

    def dicts(items, where):
        ok = []
        for i, it in enumerate(items):
            if isinstance(it, dict):
                ok.append(it)
            else:
                p.append(f"{where}[{i}] must be a JSON object, got {type(it).__name__}")
        return ok

    if not _is_str(m.get("project")):
        p.append("'project' (project name used in page titles) is required and must be a non-empty string")
    lang = m.get("language")
    if lang is not None and not (isinstance(lang, str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", lang)):
        p.append("'language' must be a language code such as 'en', 'es' or 'pt-BR'")
    for key in ("source",):
        if key in m and m[key] is not None and not isinstance(m[key], str):
            p.append(f"'{key}' must be a string")
    for a in dicts(lst(m, "areas", "model"), "areas"):
        for k in ("id", "name"):
            if not _is_str(a.get(k)):
                p.append(f"area {a.get('id')!r}: '{k}' must be a non-empty string")

    def check_attrs(attrs, where):
        for a in dicts(attrs, f"{where} attributes"):
            if not _is_str(a.get("name")):
                p.append(f"{where}: every attribute needs a non-empty string 'name'")
            if "kind" in a and not isinstance(a["kind"], str):
                p.append(f"{where} attribute {a.get('name')!r}: 'kind' must be a string")
            if "parts" in a and not (isinstance(a["parts"], list) and a["parts"] and
                                     all(_is_str(x) for x in a["parts"])):
                p.append(f"{where} attribute {a.get('name')!r}: 'parts' must be a non-empty list of names")

    for e in dicts(lst(m, "entities", "model", required=True), "entities"):
        where = f"entity {e.get('id')!r}"
        for k in ("id", "name"):
            if not _is_str(e.get(k)):
                p.append(f"{where}: '{k}' must be a non-empty string")
        if "weak" in e and not isinstance(e["weak"], bool):
            p.append(f"{where}: 'weak' must be true or false")
        if "area" in e and e["area"] is not None and not isinstance(e["area"], str):
            p.append(f"{where}: 'area' must be a string")
        check_attrs(lst(e, "attributes", where), where)
    for r in dicts(lst(m, "relationships", "model"), "relationships"):
        where = f"relationship {r.get('id')!r}"
        for k in ("id", "name"):
            if not _is_str(r.get(k)):
                p.append(f"{where}: '{k}' must be a non-empty string")
        if "identifying" in r and not isinstance(r["identifying"], bool):
            p.append(f"{where}: 'identifying' must be true or false")
        for end in dicts(lst(r, "ends", where, required=True), f"{where} ends"):
            if not isinstance(end.get("entity"), str):
                p.append(f"{where}: every end needs an 'entity' id string")
            if not isinstance(end.get("card"), str):
                p.append(f"{where}: every end needs a 'card' string ('1', 'N' or 'M')")
            if "total" in end and not isinstance(end["total"], bool):
                p.append(f"{where}: 'total' must be true or false")
            if "role" in end and end["role"] is not None and not isinstance(end["role"], str):
                p.append(f"{where}: 'role' must be a string")
        check_attrs(lst(r, "attributes", where), where)
        if "pages" in r and not (isinstance(r["pages"], list) and all(isinstance(x, str) for x in r["pages"])):
            p.append(f"{where}: 'pages' must be a list of area ids")
    for s in dicts(lst(m, "specializations", "model"), "specializations"):
        where = f"specialization {s.get('id')!r}"
        for k in ("id", "superclass"):
            if not _is_str(s.get(k)):
                p.append(f"{where}: '{k}' must be a non-empty string")
        subs = s.get("subclasses")
        if not (isinstance(subs, list) and subs and all(_is_str(x) for x in subs)):
            p.append(f"{where}: 'subclasses' must be a non-empty list of entity ids")
        for k in ("disjoint", "total"):
            if k in s and not isinstance(s[k], bool):
                p.append(f"{where}: '{k}' must be true or false")
        if s.get("defining_attribute") is not None and not _is_str(s["defining_attribute"]):
            p.append(f"{where}: 'defining_attribute' must be a non-empty string")
        if "pages" in s and not (isinstance(s["pages"], list) and all(isinstance(x, str) for x in s["pages"])):
            p.append(f"{where}: 'pages' must be a list of area ids")
    for n in dicts(lst(m, "notes", "model"), "notes"):
        if not isinstance(n.get("text"), str):
            p.append("every note needs a 'text' string")
        if "pages" in n and not (isinstance(n["pages"], list) and all(isinstance(x, str) for x in n["pages"])):
            p.append("note 'pages' must be a list of area ids")
    for a in dicts(lst(m, "assumptions", "model"), "assumptions"):
        if not isinstance(a.get("text"), str):
            p.append("every assumption needs a 'text' string")
    for key in ("open_questions",):
        if not all(isinstance(x, str) for x in lst(m, key, "model")):
            p.append(f"'{key}' must be a list of strings")
    for o in dicts(lst(m, "omitted", "model"), "omitted"):
        if not _is_str(o.get("item")) or not isinstance(o.get("reason", ""), str):
            p.append("every 'omitted' entry needs an 'item' string and a 'reason' string")
    lay = m.get("layout")
    if lay is not None:
        if not isinstance(lay, dict):
            p.append("'layout' must be an object keyed by page")
        else:
            for pg, v in lay.items():
                if not isinstance(v, dict):
                    p.append(f"layout {pg!r} must be an object")
                    continue
                for key in ("positions", "diamonds", "circles"):
                    sub = v.get(key)
                    if sub is None:
                        continue
                    if not isinstance(sub, dict) or not all(_is_pair(x) for x in sub.values()):
                        p.append(f"layout {pg!r}: '{key}' must map ids to [column, row] number pairs")
                if "spacing" in v and not (_is_pair(v["spacing"]) and min(v["spacing"]) > 0):
                    p.append(f"layout {pg!r}: 'spacing' must be [x, y] positive numbers")
                if "columns" in v and not (isinstance(v["columns"], int) and not isinstance(v["columns"], bool)
                                           and v["columns"] > 0):
                    p.append(f"layout {pg!r}: 'columns' must be a positive integer")
    return p


def normalize_model(m):
    """Validate the model and fill defaults. Raises ModelError listing every problem."""
    p = check_types(m)
    if p:
        raise ModelError(p)
    for key, default in (("areas", []), ("relationships", []), ("notes", []), ("assumptions", []),
                         ("open_questions", []), ("omitted", []), ("layout", {}), ("source", ""),
                         ("language", "en")):
        if m.get(key) is None:
            m[key] = default
    if not m.get("specializations"):
        m.pop("specializations", None)  # optional (v0.3.0); absent keeps older models byte-identical
    areas, entities, rels, notes = m["areas"], m["entities"], m["relationships"], m["notes"]
    specs = m.get("specializations", [])
    subclass_ids = {sub for s in specs for sub in s["subclasses"]}  # subclasses inherit the key
    if not entities:
        p.append("'entities' must contain at least one entity")

    area_ids = [a["id"] for a in areas]
    for a in areas:
        if not ID_RE.match(a["id"]):
            p.append(f"area id {a['id']!r} must match {ID_RE.pattern}")
    if len(set(area_ids)) != len(area_ids):
        p.append("area ids must be unique")
    if "overview" in area_ids:
        p.append("'overview' is reserved and cannot be used as an area id")
    multi = len(areas) >= 2

    ent_by_id = {}
    names = set()
    for e in entities:
        eid = e["id"]
        if not ID_RE.match(eid):
            p.append(f"entity id {eid!r} must match {ID_RE.pattern} (lowercase letters/digits)")
        if eid in ent_by_id:
            p.append(f"duplicate entity id {eid!r}")
        ent_by_id[eid] = e
        name = e["name"].strip()
        if name.lower() in names:
            p.append(f"duplicate entity name {name!r} (names are compared case-insensitively)")
        names.add(name.lower())
        e.setdefault("weak", False)
        if e.get("attributes") is None:
            e["attributes"] = []
        if multi:
            if e.get("area") not in area_ids:
                p.append(f"entity {eid!r}: 'area' must be one of {area_ids} (multi-page model)")
        else:
            e["area"] = area_ids[0] if area_ids else None
        keys = partial = 0
        anames = set()
        for a in e["attributes"]:
            a.setdefault("kind", "simple")
            if a["kind"] not in ATTR_KINDS:
                p.append(f"entity {eid!r} attribute {a['name']!r}: kind must be one of {sorted(ATTR_KINDS)}")
            an = a["name"].strip()
            if an.lower() in anames:
                p.append(f"entity {eid!r}: duplicate attribute {an!r}")
            anames.add(an.lower())
            keys += a["kind"] == "key"
            partial += a["kind"] == "partial_key"
            if a["kind"] == "composite" and not a.get("parts"):
                p.append(f"entity {eid!r} composite {an!r} needs a non-empty 'parts' list of names")
            elif "parts" in a and a["kind"] not in ("composite", "key", "partial_key"):
                p.append(f"entity {eid!r} attribute {an!r}: 'parts' only allowed for composite, key or partial_key")
        if eid in subclass_ids:
            if e["weak"]:
                p.append(f"entity {eid!r} is a subclass and cannot be weak; it inherits its identity "
                         "from its superclass")
            elif keys or partial:
                p.append(f"subclass {eid!r} must have no 'key' or 'partial_key' attribute; it inherits the "
                         "key of its superclass")
        elif e["weak"]:
            if partial != 1 or keys != 0:
                p.append(f"weak entity {eid!r} needs exactly one 'partial_key' attribute and no 'key' "
                         f"(found {partial} partial, {keys} key)")
        else:
            if keys != 1 or partial != 0:
                p.append(f"entity {eid!r} needs exactly one 'key' attribute and no 'partial_key' "
                         f"(found {keys} key, {partial} partial)")
    for a in areas:
        if multi and not any(e.get("area") == a["id"] for e in entities):
            p.append(f"area {a['id']!r} has no entities; remove it or move entities into it")

    rel_ids = set()
    ident_count = {eid: 0 for eid, e in ent_by_id.items() if e.get("weak")}
    for r in rels:
        rid = r["id"]
        if not ID_RE.match(rid):
            p.append(f"relationship id {rid!r} must match {ID_RE.pattern}")
        if rid in rel_ids:
            p.append(f"duplicate relationship id {rid!r}")
        rel_ids.add(rid)
        r.setdefault("identifying", False)
        if r.get("attributes") is None:
            r["attributes"] = []
        ends = r["ends"]
        if len(ends) < 2:
            p.append(f"relationship {rid!r} needs at least 2 'ends'")
            continue
        if len(ends) > 3:
            p.append(f"relationship {rid!r}: degree > 3 is not supported; split it")
        for end in ends:
            end.setdefault("total", False)
            if end["entity"] not in ent_by_id:
                p.append(f"relationship {rid!r}: unknown entity {end['entity']!r}")
            if end["card"] not in CARDS:
                p.append(f"relationship {rid!r}: card must be '1', 'N' or 'M' (got {end['card']!r})")
        cards = sorted(e_["card"] for e_ in ends)
        if len(ends) == 2 and cards not in (["1", "1"], ["1", "N"], ["M", "N"]):
            p.append(f"relationship {rid!r}: binary cardinality must be 1:1, 1:N or M:N "
                     f"(use 'M' and 'N' for many-to-many), got {cards}")
        ent_list = [e_["entity"] for e_ in ends]
        if len(set(ent_list)) < len(ent_list):
            if len(ends) > 2:
                p.append(f"relationship {rid!r}: a ternary relationship cannot repeat an entity; "
                         "model it as separate binary relationships")
            if any(not _is_str(e_.get("role")) for e_ in ends):
                p.append(f"recursive relationship {rid!r}: every end needs a 'role'")
        dependent = None
        if r["identifying"]:
            # dependent end = weak entity with total participation whose other end has card '1'
            cands = [e_ for e_ in ends if ent_by_id.get(e_["entity"], {}).get("weak") and e_["total"]
                     and len(ends) == 2 and [o for o in ends if o is not e_][0]["card"] == "1"]
            if len(ends) != 2 or len(set(ent_list)) != 2:
                p.append(f"identifying relationship {rid!r} must be binary between two different entities")
            elif len(cands) != 1:
                p.append(f"identifying relationship {rid!r} needs exactly one dependent end: a weak entity "
                         "with total=true, whose owner (the other end) has card '1'")
            else:
                dependent = cands[0]
                ident_count[dependent["entity"]] += 1
        for a in r["attributes"]:
            a.setdefault("kind", "simple")
            if a["kind"] not in {"simple", "multivalued", "derived", "composite"}:
                p.append(f"relationship {rid!r} attribute {a['name']!r}: kind must be simple, "
                         "multivalued, derived or composite")
            if a["kind"] == "composite" and not a.get("parts"):
                p.append(f"relationship {rid!r} composite {a['name']!r} needs 'parts'")
            elif "parts" in a and a["kind"] != "composite":
                p.append(f"relationship {rid!r} attribute {a['name']!r}: 'parts' only allowed for composite")
        if multi:
            known = [e_ for e_ in ends if e_["entity"] in ent_by_id]
            homes = {ent_by_id[e_["entity"]].get("area") for e_ in known}
            if r.get("pages") is None:
                r["pages"] = [ent_by_id[known[0]["entity"]].get("area")] if known else []
            if dependent is not None and dependent["entity"] in ent_by_id:
                weak_home = ent_by_id[dependent["entity"]].get("area")
                if weak_home not in r["pages"]:
                    r["pages"].append(weak_home)  # the weak entity's home page must show its identifying relationship
            for pg in r["pages"]:
                if pg not in homes:
                    p.append(f"relationship {rid!r}: page {pg!r} must be the home area of one of its entities "
                             f"({sorted(h for h in homes if h)})")
            if not r["pages"]:
                p.append(f"relationship {rid!r}: 'pages' must list at least one area")
    for eid, n in ident_count.items():
        if n != 1:
            p.append(f"weak entity {eid!r} must be the dependent end of exactly one identifying relationship "
                     f"(found {n})")

    spec_ids, parent_of = set(), {}
    for s in specs:
        sid, sup = s["id"], s["superclass"]
        if not ID_RE.match(sid):
            p.append(f"specialization id {sid!r} must match {ID_RE.pattern}")
        if sid in spec_ids:
            p.append(f"duplicate specialization id {sid!r}")
        spec_ids.add(sid)
        s.setdefault("disjoint", False)
        s.setdefault("total", False)
        if sup not in ent_by_id:
            p.append(f"specialization {sid!r}: unknown superclass {sup!r}")
        if len(set(s["subclasses"])) != len(s["subclasses"]):
            p.append(f"specialization {sid!r}: a subclass is listed twice")
        for sub in s["subclasses"]:
            if sub not in ent_by_id:
                p.append(f"specialization {sid!r}: unknown subclass {sub!r}")
            elif sub == sup:
                p.append(f"specialization {sid!r}: {sub!r} cannot be a subclass of itself")
            elif sub in parent_of:
                p.append(f"entity {sub!r} is a subclass in more than one specialization; each subclass has "
                         "exactly one superclass (multiple inheritance is not supported)")
            else:
                parent_of[sub] = sup
    for start in parent_of:  # a hierarchy must not loop back on itself
        seen, cur = {start}, parent_of[start]
        while cur in parent_of and cur not in seen:
            seen.add(cur)
            cur = parent_of[cur]
        if cur in seen:
            p.append(f"specialization hierarchy is cyclic around {start!r}")
            break
    for s in specs:
        da = s.get("defining_attribute")
        if da is not None and s["superclass"] in ent_by_id:
            names_up, cur, guard = set(), s["superclass"], 0
            while cur in ent_by_id and guard < 50:  # the superclass's own and inherited attributes
                names_up |= {a["name"].strip().lower() for a in ent_by_id[cur]["attributes"]}
                cur, guard = parent_of.get(cur), guard + 1
            if da.strip().lower() not in names_up:
                p.append(f"specialization {s['id']!r}: defining attribute {da!r} must be an attribute of "
                         f"superclass {s['superclass']!r}")
        if multi:
            members = [x for x in [s["superclass"]] + s["subclasses"] if x in ent_by_id]
            homes = [ent_by_id[x].get("area") for x in members]
            pages = list(s.get("pages") or [])
            for pg in pages:
                if pg not in homes:
                    p.append(f"specialization {s['id']!r}: page {pg!r} must be the home area of one of its "
                             f"entities ({sorted(h for h in set(homes) if h)})")
            for h in homes:  # every member's home page shows the specialization (subclasses need it there)
                if h and h not in pages:
                    pages.append(h)
            s["pages"] = pages

    L, _ = C.lang_strings(m["language"])
    prefixes = sorted({"Constraint:", "Rule:", L["constraint"], L["rule"]})
    for n in notes:
        t = n["text"].strip()
        if not any(t.startswith(x) for x in prefixes):
            p.append(f"note {t[:40]!r}... must start with one of {prefixes}")
        if multi:
            pgs = n.get("pages") or []
            if not pgs or any(pg not in area_ids for pg in pgs):
                p.append(f"note {t[:40]!r}...: 'pages' must list area ids where the rule matters")
    for a in m["assumptions"]:
        if not a["text"].strip():
            p.append("every assumption needs 'text'")
        if a.get("confirmed_by") not in CONFIRMATION_SOURCES:
            p.append(f"assumption {a['text'][:50]!r}: 'confirmed_by' must be one of "
                     f"{sorted(CONFIRMATION_SOURCES)}; unconfirmed items belong in 'open_questions'")
    valid_pages = set(area_ids) | {"overview"} if multi else {"main"}
    for pg, lay in m["layout"].items():
        if pg not in valid_pages:
            p.append(f"layout key {pg!r} must be one of {sorted(valid_pages)}")
            continue
        for eid in (lay.get("positions") or {}):
            if eid not in ent_by_id:
                p.append(f"layout {pg!r}: unknown entity {eid!r}")
        for rid in (lay.get("diamonds") or {}):
            if rid not in rel_ids:
                p.append(f"layout {pg!r}: unknown relationship {rid!r}")
        for sid in (lay.get("circles") or {}):
            if sid not in spec_ids:
                p.append(f"layout {pg!r}: unknown specialization {sid!r}")
    if p:
        raise ModelError(p)
    return m


# --------------------------------------------------------------------------- geometry helpers
def overlaps(a, b, pad=8):
    return not (a[0] + a[2] + pad <= b[0] or b[0] + b[2] + pad <= a[0] or
                a[1] + a[3] + pad <= b[1] or b[1] + b[3] + pad <= a[1])


def segment_hits_box(seg, b, steps=60):
    (x1, y1), (x2, y2) = seg
    for k in range(steps + 1):
        x, y = x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps
        if b[0] <= x <= b[0] + b[2] and b[1] <= y <= b[1] + b[3]:
            return True
    return False


def box(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, w, h)


class Page:
    def __init__(self, pid, name):
        self.pid, self.name = pid, name
        self.cells = []          # (kind, attrs dict, geometry dict)
        self.boxes = []          # occupied rectangles (x, y, w, h)
        self.segments = []       # straight connector segments already placed
        self.counters = {"a": 0, "s": 0, "e": 0, "n": 0, "t": 0, "l": 0}

    def next_id(self, prefix):
        self.counters[prefix] += 1
        return f"{prefix}{self.counters[prefix]}"

    def vertex(self, cid, value, style, x, y, w, h, register=True):
        self.cells.append(("v", {"id": cid, "value": value, "style": style}, (x, y, w, h)))
        if register:
            self.boxes.append((x, y, w, h))
        return cid

    def edge(self, source, target, style, value=None, label_x=None, points=None):
        cid = self.next_id("e")
        self.cells.append(("e", {"id": cid, "value": value, "style": style, "source": source,
                                 "target": target}, (label_x, points or [])))
        return cid

    def collisions(self, rects, segs=()):
        """Count overlaps of candidate rects/segments with each other and with the page."""
        n = 0
        for i, r in enumerate(rects):
            n += sum(overlaps(r, b) for b in self.boxes)
            n += sum(overlaps(r, o) for o in rects[i + 1:])
            n += sum(segment_hits_box(sg, shrink(r, 6)) for sg in self.segments)
        for sg, own in segs:
            n += sum(segment_hits_box(sg, shrink(b, 4)) for b in self.boxes if b not in own)
            n += sum(segment_hits_box(sg, shrink(r, 4)) for r in rects if r not in own)
        return n


def shrink(b, d):
    return (b[0] + d, b[1] + d, b[2] - 2 * d, b[3] - 2 * d)


def legend_height(width, legend_html=C.LEGEND_HTML, line_px=14, char_px=5.6, padding=24):
    """Height that fits the legend text (fontSize 11, spacing 8), estimating wrapped lines."""
    usable = width - 16
    lines = 0
    for raw in legend_html.split("<br>"):
        text = re.sub(r"<[^>]+>", "", raw)
        lines += max(1, math.ceil(len(text) * char_px / usable))
    return lines * line_px + padding


def esc(text):
    return html.escape(str(text), quote=False)


def attr_style_value(a):
    k, name = a["kind"], esc(a["name"])
    if k == "key":
        return C.KEY_ATTRIBUTE, name
    if k == "partial_key":
        return C.ATTRIBUTE, C.PARTIAL_KEY_TEMPLATE.format(name)
    if k == "multivalued":
        return C.MULTIVALUED, name
    if k == "derived":
        return C.DERIVED, name
    return C.ATTRIBUTE, name


def fan_angles(occupied, n, rotate=0.0):
    """Spread n angles over the free gaps between occupied directions (radians),
    proportionally to gap size, keeping a margin from every relationship line."""
    if n == 0:
        return []
    if not occupied:
        start = -math.pi / 2 + rotate
        return [start + 2 * math.pi * (i + 0.5) / n for i in range(n)]
    occ = sorted({round(a % (2 * math.pi), 6) for a in occupied})
    gaps = []
    for i, a in enumerate(occ):
        b = occ[(i + 1) % len(occ)] + (2 * math.pi if i == len(occ) - 1 else 0)
        g = b - a
        margin = min(math.radians(22), g * 0.2)
        if g - 2 * margin > math.radians(10):
            gaps.append((a + margin, g - 2 * margin))
    if not gaps:
        gaps = [(occ[0] + 0.3, 2 * math.pi - 0.6)]
    total = sum(g for _, g in gaps)
    # largest-remainder allocation of n slots over gaps
    raw = [n * g / total for _, g in gaps]
    alloc = [int(x) for x in raw]
    for i in sorted(range(len(gaps)), key=lambda i: raw[i] - alloc[i], reverse=True)[:n - sum(alloc)]:
        alloc[i] += 1
    out = []
    for (start, g), k in zip(gaps, alloc):
        shift = rotate * g / max(k, 1) * 0.5
        out += [start + g * (i + 0.5) / k + shift for i in range(k)]
    return out


def place_attribute_group(page, owner_id, cx, cy, ow, oh, attrs, occupied):
    """Place the attributes (and composite children) of one entity or diamond radially,
    trying several rotations/radii and keeping the candidate with the fewest collisions."""
    aw, ah = SIZE["attribute"]
    sw, sh = SIZE["sub_attribute"]
    owner_box = box(cx, cy, ow, oh)
    # key / partial key placed in the middle of the fan for readability
    order = sorted(attrs, key=lambda a: 0 if a["kind"] in ("key", "partial_key") else 1)
    if order and order[0]["kind"] in ("key", "partial_key") and len(order) > 2:
        key, rest = order[0], order[1:]
        mid = len(rest) // 2
        order = rest[:mid] + [key] + rest[mid:]

    def layout(scale, two_rings, rotate):
        angles = fan_angles(occupied, len(order), rotate)
        rects, segs = [], []
        for i, (a, th) in enumerate(zip(order, angles)):
            ring = 1.0 if (not two_rings or i % 2 == 0) else 1.7
            rx = (ow / 2 + aw / 2 + 45) * scale * ring
            ry = (oh / 2 + ah / 2 + 45) * scale * ring
            x, y = cx + rx * math.cos(th), cy + ry * math.sin(th)
            r_ = box(x, y, aw, ah)
            rects.append(r_)
            segs.append((((x, y), (cx, cy)), [r_, owner_box]))
            if a.get("parts"):
                ux, uy = math.cos(th), math.sin(th)
                px, py = -uy, ux
                k = len(a["parts"])
                step = abs(px) * (sw + 14) + abs(py) * (sh + 12)
                dist = abs(ux) * (aw / 2 + sw / 2 + 40) + abs(uy) * (ah / 2 + sh / 2 + 40)
                for j in range(k):
                    off = (j - (k - 1) / 2) * step
                    sx_, sy_ = x + ux * dist + px * off, y + uy * dist + py * off
                    c_ = box(sx_, sy_, sw, sh)
                    rects.append(c_)
                    segs.append((((sx_, sy_), (x, y)), [c_, r_]))
        return rects, segs

    best = None
    for two in (False, True):
        for scale in (1.0, 1.15, 1.3, 1.5, 1.75, 2.0):
            for rotate in (0.0, 0.5, -0.5, 1.0):
                rects, segs = layout(scale, two, rotate)
                c = page.collisions(rects, segs)
                if best is None or c < best[0]:
                    best = (c, rects, segs)
                if c == 0:
                    break
            if best[0] == 0:
                break
        if best[0] == 0:
            break
    collisions, rects, segs = best
    idx = 0
    for a in order:
        style, value = attr_style_value(a)
        x, y, w, h = rects[idx]
        aid = page.vertex(page.next_id("a"), value, style, x, y, w, h)
        page.edge(aid, owner_id, C.ATTR_EDGE)
        page.segments.append(segs[idx][0])
        idx += 1
        if a.get("parts"):
            for part in a["parts"]:
                x, y, w, h = rects[idx]
                sid = page.vertex(page.next_id("s"), esc(part), C.SUB_ATTRIBUTE, x, y, w, h)
                page.edge(sid, aid, C.ATTR_EDGE)
                page.segments.append(segs[idx][0])
                idx += 1
    return collisions


# --------------------------------------------------------------------------- page rendering
def place_specializations(page, specs, centre, occupied, lay, sx, sy):
    """Draw each specialization circle between its superclass and its subclasses, plus its connectors.
    Returns the number of collisions that could not be avoided."""
    ew, eh = SIZE["entity"]
    cw = ch = SIZE["specialization"][0]
    collisions = 0
    for s in specs:
        sid, sup, subs = s["id"], s["superclass"], s["subclasses"]
        (ax, ay) = centre[sup]
        tx = sum(centre[x][0] for x in subs) / len(subs)
        ty = sum(centre[x][1] for x in subs) / len(subs)
        members = {box(*centre[x], ew, eh) for x in [sup] + subs}
        if sid in (lay.get("circles") or {}):
            gx, gy = lay["circles"][sid]
            cx, cy = gx * sx, gy * sy
        else:
            vx, vy = tx - ax, ty - ay
            ln = math.hypot(vx, vy) or 1
            px, py = -vy / ln, vx / ln
            best = None
            for frac in (0.5, 0.4, 0.6, 0.3, 0.7):
                for k in (0, 1, -1, 2, -2):
                    x_ = ax + vx * frac + px * k * (cw + 40)
                    y_ = ay + vy * frac + py * k * (ch + 40)
                    b = box(x_, y_, cw, ch)
                    cost = sum(overlaps(b, o) for o in page.boxes)
                    cost += sum(segment_hits_box(((x_, y_), centre[x]), shrink(o, 2))
                                for x in [sup] + subs for o in page.boxes if o not in members)
                    cost += sum(segment_hits_box(sg, shrink(b, 2)) for sg in page.segments)
                    if best is None or cost < best[0]:
                        best = (cost, x_, y_)
                    if cost == 0:
                        break
                if best[0] == 0:
                    break
            collisions += best[0]
            _, cx, cy = best
        page.vertex(f"G_{sid}", "d" if s["disjoint"] else "o", C.SPECIALIZATION, *box(cx, cy, cw, ch))
        label = esc(s["defining_attribute"]) if s.get("defining_attribute") else None
        page.edge(f"E_{sup}", f"G_{sid}", C.ISA_TOTAL_EDGE if s["total"] else C.ISA_EDGE, value=label)
        occupied[sup].append(math.atan2(cy - ay, cx - ax))
        page.segments.append(((ax, ay), (cx, cy)))
        for sub in subs:
            page.edge(f"G_{sid}", f"E_{sub}", C.ISA_EDGE)
            bx, by = centre[sub]
            occupied[sub].append(math.atan2(cy - by, cx - bx))
            page.segments.append(((cx, cy), (bx, by)))
    return collisions


def render_page(m, page, ent_ids, ref_ids, rels, notes, with_attributes, lay, spacing, warnings, specs=()):
    ents = {e["id"]: e for e in m["entities"]}
    sx, sy = lay.get("spacing", spacing)
    positions = dict(lay.get("positions") or {})
    on_page = list(ent_ids) + [r for r in ref_ids if r not in ent_ids]
    missing = [e for e in on_page if e not in positions]
    if len(missing) > 1:  # breadth-first order from the most connected entity keeps neighbours adjacent
        nbr = {e: [] for e in on_page}
        for r in rels:
            ids_ = [x["entity"] for x in r["ends"]]
            for a_ in ids_:
                nbr[a_] += [b_ for b_ in ids_ if b_ != a_]
        for s in specs:
            for sub in s["subclasses"]:
                nbr[s["superclass"]].append(sub)
                nbr[sub].append(s["superclass"])
        order, seen = [], set()
        for start in sorted(missing, key=lambda e: (-len(nbr[e]), on_page.index(e))):
            if start in seen:
                continue
            queue = [start]
            seen.add(start)
            while queue:
                cur = queue.pop(0)
                order.append(cur)
                for x in sorted(set(nbr[cur]), key=lambda e: (-len(nbr[e]), on_page.index(e))):
                    if x not in seen and x in missing:
                        seen.add(x)
                        queue.append(x)
        missing = order
    if missing:
        cols = lay.get("columns") or max(1, math.ceil(math.sqrt(len(on_page))))
        taken = {tuple(v) for k, v in positions.items() if k in on_page}
        slot = 0
        for eid in missing:
            while (slot % cols, slot // cols) in taken:
                slot += 1
            positions[eid] = [slot % cols, slot // cols]
            slot += 1
        warnings.append(f"page {page.name!r}: auto-placed {', '.join(missing)} on a grid; "
                        "give explicit layout positions if the validator reports overlaps/crossings")
    centre = {eid: (positions[eid][0] * sx, positions[eid][1] * sy) for eid in on_page}

    ew, eh = SIZE["entity"]
    for eid in on_page:
        e = ents[eid]
        is_ref = eid in ref_ids and eid not in ent_ids
        if e["weak"]:
            style = C.REF_WEAK_ENTITY if is_ref else C.WEAK_ENTITY
        else:
            style = C.REF_ENTITY if is_ref else C.ENTITY
        x, y, w, h = box(*centre[eid], ew, eh)
        page.vertex(f"E_{eid}", esc(e["name"]), style, x, y, w, h)

    # diamonds
    rw, rh = SIZE["relationship"]
    groups = {}
    for r in rels:
        groups.setdefault(frozenset(e_["entity"] for e_ in r["ends"]), []).append(r)
    occupied = {eid: [] for eid in on_page}
    dpos, rel_edges = {}, {}
    diamond_collisions = 0
    segments = page.segments  # relationship lines already drawn
    ordered = sorted(groups.items(), key=lambda kv: len(kv[0]) == 1)  # recursive groups last
    for key, grp in ordered:
        for i, r in enumerate(grp):
            ends = [e_["entity"] for e_ in r["ends"]]
            recursive = len(set(ends)) == 1
            side = None
            if r["id"] in (lay.get("diamonds") or {}):
                gx, gy = lay["diamonds"][r["id"]]
                dx, dy = gx * sx, gy * sy
                if recursive:
                    cx, cy = centre[ends[0]]
                    side = "h" if abs(dx - cx) >= abs(dy - cy) else "v"
            elif recursive:
                cx, cy = centre[ends[0]]
                spread = (i - (len(grp) - 1) / 2)
                cands = [("h", cx - sx / 2, cy + spread * (rh + 30)), ("h", cx + sx / 2, cy + spread * (rh + 30)),
                         ("v", cx + spread * (rw + 30), cy - sy / 2), ("v", cx + spread * (rw + 30), cy + sy / 2)]
                side, dx, dy = cands[0]
                for sd, x_, y_ in cands:
                    b = box(x_, y_, rw + 40, rh + 40)
                    if any(overlaps(b, o, 0) for o in page.boxes):
                        continue
                    if any(segment_hits_box(s_, b) for s_ in segments):
                        continue
                    side, dx, dy = sd, x_, y_
                    break
            else:
                pts = [centre[x] for x in ends]
                mx = sum(p_[0] for p_ in pts) / len(pts)
                my = sum(p_[1] for p_ in pts) / len(pts)
                a_, b_ = centre[ends[0]], centre[ends[1]]
                vx, vy = b_[0] - a_[0], b_[1] - a_[1]
                ln = math.hypot(vx, vy) or 1
                px, py = -vy / ln, vx / ln          # unit perpendicular to the first two ends
                step = abs(px) * (rw + 30) + abs(py) * (rh + 30)
                base = (i - (len(grp) - 1) / 2) * step  # parallel relationships fan out sideways
                end_boxes = {box(*centre[x], ew, eh) for x in ends}
                best_d = None
                for k in (0, 1, -1, 2, -2, 3, -3):
                    off = base + k * step * (len(grp) if len(grp) > 1 else 1)
                    x_, y_ = mx + px * off, my + py * off
                    b = box(x_, y_, rw, rh)
                    cost = sum(overlaps(b, o) for o in page.boxes)
                    cost += sum(segment_hits_box(((x_, y_), centre[x]), shrink(o, 2))
                                for x in ends for o in page.boxes if o not in end_boxes)
                    cost += sum(segment_hits_box(sg, shrink(b, 2)) for sg in segments)
                    if best_d is None or cost < best_d[0]:
                        best_d = (cost, x_, y_)
                    if cost == 0:
                        break
                _, dx, dy = best_d
                diamond_collisions += best_d[0]
            dpos[r["id"]] = (dx, dy)
            style = C.ID_RELATIONSHIP if r["identifying"] else C.RELATIONSHIP
            page.vertex(f"R_{r['id']}", esc(r["name"]), style, *box(dx, dy, rw, rh))
            edges = []
            for j, end in enumerate(r["ends"]):
                eid = end["entity"]
                cx, cy = centre[eid]
                pts = []
                if recursive:
                    sign = -1 if j == 0 else 1
                    if side == "h":
                        sd = 1 if dx >= cx else -1
                        yoff = (eh / 2 + 18) * sign
                        pts = [(dx, cy + yoff), (cx + sd * (ew / 2 - 15), cy + yoff)]
                        occupied[eid].append(math.atan2(yoff, sd * (ew / 2 - 15)))
                    else:
                        sd = 1 if dy >= cy else -1
                        xoff = (ew / 2 + 30) * sign
                        pts = [(cx + xoff, dy), (cx + xoff, cy + sd * (eh / 2 - 8))]
                        occupied[eid].append(math.atan2(sd * (eh / 2 - 8), xoff))
                    loop = list(zip([(dx, dy)] + pts, pts + [(cx, cy)]))
                    for (x1, y1), (x2, y2) in loop[:-1]:  # the loop rim is not free for attributes
                        for k in range(11):
                            px_, py_ = x1 + (x2 - x1) * k / 10, y1 + (y2 - y1) * k / 10
                            occupied[eid].append(math.atan2(py_ - cy, px_ - cx))
                    segments += loop
                else:
                    occupied[eid].append(math.atan2(dy - cy, dx - cx))
                    segments.append(((dx, dy), (cx, cy)))
                label = end["card"] + (f" ({end['role']})" if end.get("role") else "")
                edges.append((eid, end, label, pts))
            rel_edges[r["id"]] = edges

    for r in rels:
        for eid, end, label, pts in rel_edges[r["id"]]:
            page.edge(f"R_{r['id']}", f"E_{eid}", C.TOTAL_EDGE if end["total"] else C.PARTIAL_EDGE,
                      value=esc(label), label_x=0.6, points=pts)

    collisions = diamond_collisions
    if specs:
        collisions += place_specializations(page, specs, centre, occupied, lay, sx, sy)
    if with_attributes:
        for eid in ent_ids:
            e = ents[eid]
            if e["attributes"]:
                collisions += place_attribute_group(page, f"E_{eid}", *centre[eid], ew, eh,
                                                    e["attributes"], occupied[eid])
        for r in rels:
            if not r["attributes"]:
                continue
            dx, dy = dpos[r["id"]]
            occ = []
            for eid, _, _, pts in rel_edges[r["id"]]:
                tx, ty = pts[0] if pts else centre[eid]
                occ.append(math.atan2(ty - dy, tx - dx))
            collisions += place_attribute_group(page, f"R_{r['id']}", dx, dy, rw, rh,
                                                r["attributes"], occ)
    if collisions:
        warnings.append(f"page {page.name!r}: {collisions} shape overlap(s) could not be avoided "
                        "automatically; adjust layout positions/spacing and re-render")

    # frame: title, legend, notes around the bounding box
    xs = [b[0] for b in page.boxes] + [b[0] + b[2] for b in page.boxes]
    ys = [b[1] for b in page.boxes] + [b[1] + b[3] for b in page.boxes]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    L, _ = C.lang_strings(m.get("language"))
    title = (f"<b><span style=\"font-size: 16px;\">{esc(m['project'])} — {L['title']}</span></b>"
             f"<br>{L['page_label']}: {esc(page.name)}")
    page.vertex(page.next_id("t"), title, C.TEXT, minx, miny - 110, 520, 50)
    lw = 340
    legend = L["legend"] + (L["legend_isa"] if specs else "")
    page.vertex(page.next_id("l"), legend, C.LEGEND, maxx + 80, miny, lw, legend_height(lw, legend))
    nw, nh = SIZE["note"]
    for i, n in enumerate(notes):
        col, row = i % 3, i // 3
        page.vertex(page.next_id("n"), esc(n["text"]), C.NOTE,
                    minx + col * (nw + 30), maxy + 70 + row * (nh + 30), nw, nh)

    # shift so the drawing starts near (40, 40)
    allx = [c[2][0] for c in page.cells if c[0] == "v"]
    ally = [c[2][1] for c in page.cells if c[0] == "v"]
    ox, oy = 40 - min(allx), 40 - min(ally)
    shifted = []
    for kind, attrs, geo in page.cells:
        if kind == "v":
            x, y, w, h = geo
            geo = (round(x + ox), round(y + oy), w, h)
        else:
            lx, pts = geo
            geo = (lx, [(round(px + ox), round(py + oy)) for px, py in pts])
        shifted.append((kind, attrs, geo))
    page.cells = shifted


def page_xml(page, parent):
    d = ET.SubElement(parent, "diagram", id=page.pid, name=page.name)
    gm = ET.SubElement(d, "mxGraphModel", dx="1600", dy="1000", grid="1", gridSize="10",
                       guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="0",
                       pageScale="1", math="0", shadow="0")
    root = ET.SubElement(gm, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    # vertices first, then edges (edges render on top of nothing important; keeps diffs stable)
    for kind, attrs, geo in [c for c in page.cells if c[0] == "v"] + [c for c in page.cells if c[0] == "e"]:
        if kind == "v":
            c = ET.SubElement(root, "mxCell", id=attrs["id"], value=attrs["value"],
                              style=attrs["style"], vertex="1", parent="1")
            x, y, w, h = geo
            ET.SubElement(c, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h),
                          **{"as": "geometry"})
        else:
            a = {"id": attrs["id"]}
            if attrs["value"] is not None:
                a["value"] = attrs["value"]
            a.update(style=attrs["style"], edge="1", parent="1", source=attrs["source"],
                     target=attrs["target"])
            c = ET.SubElement(root, "mxCell", **a)
            lx, pts = geo
            g = ET.SubElement(c, "mxGeometry", **({"x": str(lx)} if lx is not None else {}),
                              relative="1", **{"as": "geometry"})
            if pts:
                arr = ET.SubElement(g, "Array", **{"as": "points"})
                for px, py in pts:
                    ET.SubElement(arr, "mxPoint", x=str(px), y=str(py))
            if lx is not None or pts:
                ET.SubElement(g, "mxPoint", **{"as": "offset"})


def build(m):
    warnings = []
    L, supported = C.lang_strings(m.get("language"))
    if not supported:
        warnings.append(f"language {m.get('language')!r} has no translation for titles, legend and summary; "
                        "they are rendered in English (add it to erd_catalog.LANG)")
    areas = m["areas"]
    multi = len(areas) >= 2
    pages = []
    if len(m["entities"]) >= 10 and not multi:
        warnings.append("model has 10+ entities on a single page; consider defining 2+ 'areas' "
                        "to get an Overview plus one page per subject area")
    if not multi:
        pg = Page("erd", L["single_page"])
        ids = [e["id"] for e in m["entities"]]
        render_page(m, pg, ids, [], m["relationships"], m["notes"], True,
                    m["layout"].get("main", {}), DETAIL_SPACING, warnings, m.get("specializations", []))
        pages.append(pg)
    else:
        ov = Page("overview", L["overview"])
        render_page(m, ov, [e["id"] for e in m["entities"]], [], m["relationships"], m["notes"],
                    False, m["layout"].get("overview", {}), OVERVIEW_SPACING, warnings, m.get("specializations", []))
        pages.append(ov)
        for i, a in enumerate(areas, start=2):
            pg = Page(a["id"], f"{i} - {a['name']}")
            home = [e["id"] for e in m["entities"] if e["area"] == a["id"]]
            rels = [r for r in m["relationships"] if a["id"] in r["pages"]]
            specs = [s for s in m.get("specializations", []) if a["id"] in s["pages"]]
            refs = []
            members = [e_["entity"] for r in rels for e_ in r["ends"]]
            members += [x for s in specs for x in [s["superclass"]] + s["subclasses"]]
            for x in members:
                if x not in home and x not in refs:
                    refs.append(x)
            notes = [n for n in m["notes"] if a["id"] in n["pages"]]
            render_page(m, pg, home, refs, rels, notes, True, m["layout"].get(a["id"], {}),
                        DETAIL_SPACING, warnings, specs)
            pages.append(pg)
    mx = ET.Element("mxfile", host="app.diagrams.net", agent="db-erd-chen skill",
                    version="24.0.0")
    for pg in pages:
        page_xml(pg, mx)
    ET.indent(mx, space="  ")
    return ET.tostring(mx, encoding="unicode") + "\n", pages, warnings


# --------------------------------------------------------------------------- summary
def md(text):
    """Escape text for a Markdown table cell / list item."""
    return html.escape(str(text), quote=False).replace("|", "\\|")


def summary_md(m, drawio_name, pages):
    L, _ = C.lang_strings(m.get("language"))
    ents = {e["id"]: e for e in m["entities"]}
    area_name = {a["id"]: a["name"] for a in m["areas"]}
    specs = m.get("specializations", [])
    parent = {sub: sp["superclass"] for sp in specs for sub in sp["subclasses"]}
    out = [f"# {md(m['project'])} — {L['summary']}", "",
           f"- {L['diagram']}: `{drawio_name}` ({L['uncompressed']})",
           f"- {L['pages']}: {', '.join(p.name for p in pages)}"]
    if m.get("source"):
        out.append(f"- {L['source']}: {md(m['source'])}")
    out += ["", f"## {L['entities']} ({len(m['entities'])})", "",
            L["ent_header"], "|---|---|---|---|---|"]
    for e in m["entities"]:
        key = next((a["name"] + (f" ({', '.join(a['parts'])})" if a.get("parts") else "")
                    for a in e["attributes"] if a["kind"] in ("key", "partial_key")), "")
        kind = L["weak"] if e["weak"] else L["strong"]
        attrs = []
        for a in e["attributes"]:
            if a["kind"] in ("key", "partial_key"):
                continue
            label = a["name"]
            if a["kind"] == "composite":
                label += f" ({', '.join(a['parts'])})"
            elif a["kind"] != "simple":
                label += f" [{L['kinds'].get(a['kind'], a['kind'])}]"
            attrs.append(label)
        key_label = f"{key} ({L['partial_key']})" if e["weak"] else key
        if e["id"] in parent:
            kind = L["subclass_of"].format(ents[parent[e["id"]]]["name"])
            key_label = L["inherited"].format(ents[parent[e["id"]]]["name"])
        home = area_name.get(e.get("area"), pages[0].name) if len(m["areas"]) >= 2 else pages[0].name
        out.append(f"| {md(e['name'])} | {kind} | {md(key_label)} | {md(', '.join(attrs)) or '—'} | {md(home)} |")
    out += ["", f"## {L['relationships']} ({len(m['relationships'])})", "",
            L["rel_header"], "|---|---|---|---|"]
    for r in m["relationships"]:
        ends = []
        for e_ in r["ends"]:
            role = f" {L['as']} {e_['role']}" if e_.get("role") else ""
            part = L["total"] if e_["total"] else L["partial"]
            ends.append(f"{ents[e_['entity']]['name']}{role} ({e_['card']}, {part})")
        ratio = ":".join(e_["card"] for e_ in r["ends"])
        if len(r["ends"]) == 3:
            ratio += f" ({L['ternary']})"
        elif len({e_["entity"] for e_ in r["ends"]}) == 1:
            ratio += f" ({L['recursive']})"
        name = r["name"] + (f" ({L['identifying']})" if r["identifying"] else "")
        attrs = ", ".join(a["name"] for a in r["attributes"]) or "—"
        out.append(f"| {md(name)} | {md(' — '.join(ends))} | {ratio} | {md(attrs)} |")
    if specs:
        out += ["", f"## {L['specializations']} ({len(specs)})", "", L["isa_header"], "|---|---|---|---|---|"]
        for sp in specs:
            subs = ", ".join(ents[x]["name"] for x in sp["subclasses"])
            dis = L["disjoint"] if sp["disjoint"] else L["overlapping"]
            comp = L["total"] if sp["total"] else L["partial"]
            out.append(f"| {md(ents[sp['superclass']]['name'])} | {md(subs)} | {dis} | {comp} | "
                       f"{md(sp.get('defining_attribute') or '—')} |")
    out += ["", f"## {L['rules']}", ""]
    out += [f"- {md(n['text'])}" for n in m["notes"]] or [f"- {L['none_rules']}"]
    out += ["", f"## {L['assumptions']}", ""]
    out += [f"- {md(a['text'])} ({L['confirmed_by']}: {L['sources'].get(a['confirmed_by'], a['confirmed_by'])})"
            for a in m["assumptions"]] or [f"- {L['none']}"]
    out += ["", f"## {L['open']}", ""]
    out += [f"- {md(q)}" for q in m["open_questions"]] or [f"- {L['none']}"]
    out += ["", f"## {L['omitted']}", ""]
    out += [f"- {md(o['item'])}: {md(o.get('reason', ''))}" for o in m["omitted"]] or [f"- {L['nothing']}"]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- CLI
def next_version_path(out_dir, name):
    """Highest existing version + 1 (gaps are never reused), so -vN order = creation order."""
    rx = re.compile(r"^" + re.escape(name) + r"(?:-v(\d+))?\.(?:drawio|summary\.md|model\.json)$")
    highest = 0
    for f in os.listdir(out_dir):
        mm = rx.match(f)
        if mm:
            highest = max(highest, int(mm.group(1) or 1))
    n = highest + 1
    base = name if n == 1 else f"{name}-v{n}"
    return os.path.join(out_dir, base + ".drawio")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--out-dir", help="target folder (normally db-design); picks the next free version name")
    g.add_argument("--out", help="explicit .drawio output path")
    g.add_argument("--check", action="store_true", help="validate the model only")
    ap.add_argument("--name", default="conceptual-erd", help="base name used with --out-dir")
    ap.add_argument("--force", action="store_true", help="allow overwriting with --out")
    args = ap.parse_args(argv)

    try:
        with open(args.model, encoding="utf-8-sig") as f:
            model = json.load(f)
    except UnicodeDecodeError as ex:
        print(f"ERROR: model file is not UTF-8 text: {ex}", file=sys.stderr)
        return 1
    except OSError as ex:
        print(f"ERROR: cannot read model: {ex}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as ex:
        print(f"ERROR: model is not valid JSON: {ex}", file=sys.stderr)
        return 1
    try:
        model = normalize_model(model)
    except ModelError as ex:
        print("ERROR: invalid model:", file=sys.stderr)
        for prob in ex.problems:
            print(f"  - {prob}", file=sys.stderr)
        return 1
    try:
        xml, pages, warnings = build(model)
    except Exception as ex:  # never show a traceback to the agent; report and fail cleanly
        print(f"ERROR: internal renderer error ({type(ex).__name__}: {ex}). The model passed validation; "
              "please report this with the model file.", file=sys.stderr)
        return 1
    if len(model["entities"]) > 1 and not model["relationships"] and not model.get("specializations"):
        warnings.append("model has several entities but no relationships; every entity must be reachable "
                        "(the validator will fail unless isolation is confirmed with --allow-isolated)")
    if args.check:
        for w in warnings:
            print(f"WARNING: {w}")
        print("Model OK.")
        return 0
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", args.name):
        print("ERROR: --name must be lowercase and hyphenated (e.g. conceptual-erd)", file=sys.stderr)
        return 1
    try:
        if args.out:
            out = args.out
            if not out.endswith(".drawio"):
                print("ERROR: --out must end with .drawio", file=sys.stderr)
                return 1
            base = out[:-len(".drawio")]
            targets = [out, base + ".summary.md", base + ".model.json"]
            if not args.force and any(os.path.exists(t) for t in targets):
                print(f"ERROR: {', '.join(t for t in targets if os.path.exists(t))} already exists; "
                      "use --out-dir to create a new version, or --force to overwrite", file=sys.stderr)
                return 2
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        else:
            out_dir = args.out_dir or "db-design"
            os.makedirs(out_dir, exist_ok=True)
            out = next_version_path(out_dir, args.name)
            base = out[:-len(".drawio")]
        with open(out, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + xml)
        with open(base + ".summary.md", "w", encoding="utf-8") as f:
            f.write(summary_md(model, os.path.basename(out), pages))
        with open(base + ".model.json", "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as ex:
        print(f"ERROR: cannot write output: {ex}", file=sys.stderr)
        return 2
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"Wrote {out}")
    print(f"Wrote {base}.summary.md")
    print(f"Wrote {base}.model.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
