#!/usr/bin/env python3
"""validate_erd.py - self-check a Chen-notation ERD saved as a diagrams.net (.drawio) file.

Usage:
  python3 validate_erd.py db-design/conceptual-erd.drawio [--allow-isolated "Audit Log" ...] [--json]
  python3 validate_erd.py --decompress compressed.drawio uncompressed.drawio

Checks (ERROR = must fix, WARNING = review and justify):
  format     well-formed XML, <mxfile>/<diagram>/<mxGraphModel>, uncompressed, cells 0/1 first,
             unique ids per page, every edge has an existing source and target, no arrowheads
  catalog    every shape/connector matches the mandatory style catalog and sizes
  notation   every relationship has a verb name and a cardinality (1/N/M) on every end,
             binary ratios are 1:1, 1:N or M:N, recursive ends carry roles, identifying
             relationships connect a weak entity with a double line, every attribute is
             connected to exactly one owner (no orphans), keys: exactly one per entity
  scope      no data types, FK/PK/index/SQL terms, snake_case names, or "<Entity> ID" attributes
  structure  every entity takes part in a relationship and the entity graph is connected;
             multi-page: Overview with all entities/relationships/notes and no attributes,
             exactly one home page per entity, reference entities without attributes,
             every relationship on at least one detail page; every page has a title and legend
  layout     no overlapping shapes, no connector passing through a shape
Exit codes: 0 no errors, 1 errors found, 2 file unreadable / not XML.
Standard library only.
"""
import argparse
import base64
import html
import json
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import erd_catalog as C  # noqa: E402

TAG_RE = re.compile(r"<[^>]+>")
TYPE_WORDS = (r"varchar|nvarchar|char|nchar|text|string|int|integer|bigint|smallint|tinyint|decimal|numeric|"
              r"float|double|real|number|money|bool|boolean|bit|date|datetime2?|timestamp|timestamptz|time|uuid|"
              r"guid|json|jsonb|blob|clob|bytea|binary|varbinary|serial|bigserial")
PHYSICAL_RES = [
    # type with a length/precision: varchar(200), decimal(14,4), char (3)
    (re.compile(r"\b(" + TYPE_WORDS + r")\s*\(\s*\d+\s*(,\s*\d+\s*)?\)", re.I), "data type"),
    # type in brackets or after a colon at the end: "Price (decimal)", "Status: text"
    (re.compile(r"(\(\s*(" + TYPE_WORDS + r")\s*\)|:\s*(" + TYPE_WORDS + r"))\s*$", re.I), "data type annotation"),
    # trailing bare type word on a multi-word label: "Name String", "Created at timestamp"
    (re.compile(r"\s(varchar|nvarchar|string|integer|int|bigint|boolean|bool|timestamp|timestamptz|"
                r"datetime|uuid|jsonb|decimal)\s*$", re.I), "data type"),
    # unambiguous physical type words anywhere
    (re.compile(r"\b(varchar|nvarchar|bigint|smallint|tinyint|jsonb|bytea|timestamptz|bigserial)\b", re.I), "data type"),
    (re.compile(r"\b(PK|FK|NOT NULL|NULLABLE|AUTO_INCREMENT|ON DELETE|ON UPDATE|CREATE TABLE)\b"), "physical/SQL term"),
    (re.compile(r"\b(primary key|foreign key|references|fk|pk)\b", re.I), "physical/SQL term"),
    (re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b"), "snake_case (physical) name"),
    (re.compile(r"^[a-z]+[A-Z][A-Za-z0-9]*$"), "camelCase (physical) name"),
]
FK_RE = re.compile(r"^(.+?)[ _]?(ID|Id|id)$")


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, page, msg):
        self.errors.append(f"[{page}] {msg}")

    def warn(self, page, msg):
        self.warnings.append(f"[{page}] {msg}")


def plain(value):
    text = TAG_RE.sub(" ", (value or "").replace("<br>", "\n"))
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def decompress_diagram(text):
    data = base64.b64decode(text)
    raw = zlib.decompress(data, -15).decode("utf-8")
    return urllib.parse.unquote(raw)


def classify_vertex(st, value):
    if "text" in st:
        return "legend" if st.get("strokeColor") == "#999999" and st.get("fillColor") == "#fafafa" else "title"
    if st.get("shape") == "note":
        return "note"
    if st.get("shape") == "rhombus" or "rhombus" in st:
        return "id_relationship" if st.get("double") == "1" else "relationship"
    if "ellipse" in st or st.get("shape") in ("ellipse", "doubleEllipse"):
        if st.get("shape") == "doubleEllipse":
            return "multivalued"
        if st.get("fontSize") == "10":
            return "sub_attribute"
        if st.get("fontStyle") == "4":
            return "key_attribute"
        if st.get("dashed") == "1":
            return "derived"
        if "border-bottom" in (value or "") and "dashed" in (value or ""):
            return "partial_key"
        return "attribute"
    if st.get("fillColor") == "#f5f5f5" and st.get("dashed") == "1":
        return "ref_weak_entity" if st.get("double") == "1" else "ref_entity"
    if st.get("shape") == "ext" and st.get("double") == "1":
        return "weak_entity"
    if st.get("fillColor") == "#dae8fc":
        return "entity"
    return None


def classify_edge(st):
    if st.get("shape") == "link":
        return "total_edge"
    if st.get("strokeColor") == "#888888":
        return "attr_edge"
    return "partial_edge"


def check_style(rep, page, cid, kind, style, catalog_style):
    actual, expected = C.parse_style(style), C.parse_style(catalog_style)
    diff = [k for k, v in expected.items() if k not in actual or actual[k] != v]
    if diff:
        rep.err(page, f"{cid} ({kind}): style differs from catalog in {diff}")
    extra = [k for k in actual if k not in expected]
    if extra:
        rep.warn(page, f"{cid} ({kind}): extra style keys {extra} (not in catalog)")


ENTITY_KINDS = {"entity", "weak_entity", "ref_entity", "ref_weak_entity"}
REL_KINDS = {"relationship", "id_relationship"}
ATTR_KINDS = {"attribute", "key_attribute", "partial_key", "multivalued", "derived"}


def inside(kind, g, x, y, shrink=2.0):
    gx, gy, w, h = g
    cx, cy = gx + w / 2, gy + h / 2
    hw, hh = w / 2 - shrink, h / 2 - shrink
    if hw <= 0 or hh <= 0:
        return False
    dx, dy = abs(x - cx) / hw, abs(y - cy) / hh
    if kind in REL_KINDS:
        return dx + dy < 1
    if kind in ATTR_KINDS or kind == "sub_attribute":
        return dx * dx + dy * dy < 1
    return dx < 1 and dy < 1


def check_layout(rep, pname, verts, edges):
    shapes = [(cid, v) for cid, v in verts.items() if v["geo"] is not None]
    for i, (a, va) in enumerate(shapes):
        ax, ay, aw, ah = va["geo"]
        for b, vb in shapes[i + 1:]:
            bx, by, bw, bh = vb["geo"]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                msg = f"shapes {a} ({plain(va['value'])[:30]!r}) and {b} ({plain(vb['value'])[:30]!r}) overlap"
                if {va["kind"], vb["kind"]} & {"title", "legend", "note"}:
                    rep.warn(pname, msg)
                else:
                    rep.err(pname, msg)
    for eid, e in edges.items():
        s, t = verts.get(e["source"]), verts.get(e["target"])
        if not s or not t or s["geo"] is None or t["geo"] is None:
            continue
        def ctr(g):
            return (g[0] + g[2] / 2, g[1] + g[3] / 2)
        pts = [ctr(s["geo"])] + e["points"] + [ctr(t["geo"])]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = max(2, int(max(abs(x2 - x1), abs(y2 - y1)) / 4))
            lo_x, hi_x, lo_y, hi_y = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
            for cid, v in shapes:
                if cid in (e["source"], e["target"]) or v["kind"] in ("title",):
                    continue
                gx, gy, w, h = v["geo"]
                if gx > hi_x or gx + w < lo_x or gy > hi_y or gy + h < lo_y:
                    continue
                if any(inside(v["kind"], v["geo"], x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n)
                       for k in range(n + 1)):
                    msg = (f"connector {eid} ({e['source']} -> {e['target']}) passes through "
                           f"{cid} ({plain(v['value'])[:30]!r}); move shapes or add waypoints")
                    (rep.warn if v["kind"] in ("legend", "note") else rep.err)(pname, msg)
                    break


def analyse_page(rep, diagram, is_overview, all_entity_names):
    pname = diagram.get("name") or diagram.get("id") or "?"
    gm = diagram.find("mxGraphModel")
    if gm is None:
        if (diagram.text or "").strip():
            rep.err(pname, "page content is compressed; save uncompressed "
                           "(File > Properties > Compressed off) or run --decompress")
        else:
            rep.err(pname, "page has no <mxGraphModel>")
        return None
    root = gm.find("root")
    cells = root.findall("mxCell") if root is not None else []
    # draw.io may wrap cells in <object>/<UserObject>; treat them as cells with the wrapper's id/label
    for wrapper in (root.findall("object") + root.findall("UserObject")) if root is not None else []:
        inner = wrapper.find("mxCell")
        if inner is not None:
            inner.set("id", wrapper.get("id", ""))
            inner.set("value", wrapper.get("label", ""))
            cells.append(inner)
    if len(cells) < 2 or cells[0].get("id") != "0" or cells[1].get("id") != "1" or cells[1].get("parent") != "0":
        rep.err(pname, 'the first two cells must be <mxCell id="0"/> and <mxCell id="1" parent="0"/>')
    ids = [c.get("id") for c in cells]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        rep.err(pname, f"duplicate ids {dupes}")
    idset = set(ids)
    verts, edges = {}, {}
    edge_ids = {c.get("id") for c in cells if c.get("edge") == "1"}
    offsets = {}       # absolute top-left of container cells (groups), for child coordinates
    edge_labels = {}   # labels added in diagrams.net as child cells of an edge
    for c in cells:
        cid = c.get("id")
        if cid in ("0", "1"):
            continue
        st = C.parse_style(c.get("style"))
        geo = c.find("mxGeometry")
        parent = c.get("parent")
        if c.get("vertex") == "1" and ("edgeLabel" in st or parent in edge_ids):
            edge_labels[parent] = (edge_labels.get(parent, "") + " " + plain(c.get("value"))).strip()
            continue
        if c.get("vertex") == "1" and ("group" in st or c.get("connectable") == "0" and not c.get("value")):
            try:
                ox, oy = offsets.get(parent, (0.0, 0.0))
                offsets[cid] = (ox + float(geo.get("x", 0)), oy + float(geo.get("y", 0))) if geo is not None else (ox, oy)
            except ValueError:
                rep.err(pname, f"{cid}: non-numeric geometry")
            continue
        if c.get("vertex") == "1":
            kind = classify_vertex(st, c.get("value"))
            g = None
            if geo is not None:
                try:
                    g = tuple(float(geo.get(k, 0)) for k in ("x", "y", "width", "height"))
                    ox, oy = offsets.get(parent, (0.0, 0.0))
                    g = (g[0] + ox, g[1] + oy, g[2], g[3])
                except ValueError:
                    rep.err(pname, f"{cid}: non-numeric geometry")
            verts[cid] = {"kind": kind, "value": c.get("value") or "", "geo": g, "style": c.get("style")}
            if kind is None:
                rep.err(pname, f"{cid} ({plain(c.get('value'))[:30]!r}): shape does not match any catalog element")
                continue
            cat_style, w, h = C.VERTEX_CATALOG[kind]
            check_style(rep, pname, cid, kind, c.get("style"), cat_style)
            if w is not None and g is not None and (g[2], g[3]) != (w, h):
                rep.err(pname, f"{cid} ({kind}): size {g[2]:g}x{g[3]:g} must be {w}x{h}")
        elif c.get("edge") == "1":
            kind = classify_edge(st)
            check_style(rep, pname, cid, kind, c.get("style"), C.EDGE_CATALOG[kind])
            if st.get("endArrow", "none") != "none" or st.get("startArrow", "none") != "none":
                rep.err(pname, f"{cid}: connectors must not have arrowheads (Chen notation)")
            src, tgt = c.get("source"), c.get("target")
            if src not in idset or tgt not in idset:
                rep.err(pname, f"edge {cid} is dangling (source={src!r}, target={tgt!r})")
            pts = []
            if geo is not None:
                arr = geo.find("Array")
                if arr is not None:
                    try:
                        pts = [(float(p.get("x", 0)), float(p.get("y", 0))) for p in arr.findall("mxPoint")]
                    except ValueError:
                        rep.err(pname, f"{cid}: non-numeric waypoint")
            edges[cid] = {"kind": kind, "source": src, "target": tgt, "value": c.get("value") or "",
                          "points": pts}
    for eid, lab in edge_labels.items():
        if eid in edges and not plain(edges[eid]["value"]):
            edges[eid]["value"] = lab
    for eid, e in edges.items():
        if e["source"] not in verts or e["target"] not in verts:
            continue
        sk, tk = verts[e["source"]]["kind"], verts[e["target"]]["kind"]
        if e["kind"] == "attr_edge":
            ok = (sk in ATTR_KINDS and (tk in ENTITY_KINDS or tk in REL_KINDS)) or \
                 (sk == "sub_attribute" and tk in ATTR_KINDS)
            if not ok:
                rep.err(pname, f"attribute connector {eid} must go from an attribute ellipse to its entity/diamond "
                               f"(or from a sub-attribute to its composite); got {sk} -> {tk}")
        else:
            if not (sk in REL_KINDS and tk in ENTITY_KINDS):
                rep.err(pname, f"relationship connector {eid} must go from a diamond (source) to an entity "
                               f"(target); got {sk} -> {tk}")

    name_of = {cid: plain(v["value"]) for cid, v in verts.items()}
    entities = {cid: v for cid, v in verts.items() if v["kind"] in ENTITY_KINDS}
    rels = {cid: v for cid, v in verts.items() if v["kind"] in REL_KINDS}
    for cid, v in list(entities.items()) + list(rels.items()) + \
            [(c, v) for c, v in verts.items() if v["kind"] in ATTR_KINDS | {"sub_attribute"}]:
        if not name_of[cid]:
            rep.err(pname, f"{cid} ({v['kind']}) has no label")
    ent_names = {}
    for cid in entities:
        n = name_of[cid].lower()
        if n in ent_names:
            rep.err(pname, f"entity {name_of[cid]!r} is drawn twice on this page ({ent_names[n]}, {cid})")
        ent_names[n] = cid

    # attributes: exactly one owner connector each
    owners = {cid: [] for cid, v in verts.items() if v["kind"] in ATTR_KINDS | {"sub_attribute"}}
    for e in edges.values():
        if e["kind"] == "attr_edge" and e["source"] in owners:
            owners[e["source"]].append(e["target"])
    for cid, tl in owners.items():
        if len(tl) != 1:
            rep.err(pname, f"attribute {cid} ({name_of[cid]!r}) must connect to exactly one owner (has {len(tl)}); "
                           "orphan or shared attribute")
    attrs_of = {cid: [] for cid in list(entities) + list(rels)}
    for a, tl in owners.items():
        if len(tl) == 1 and tl[0] in attrs_of:
            attrs_of[tl[0]].append(a)
    composite_children = {}
    for a, tl in owners.items():
        if verts[a]["kind"] == "sub_attribute" and len(tl) == 1:
            composite_children.setdefault(tl[0], []).append(a)
    for a in owners:
        if verts[a]["kind"] in ATTR_KINDS and composite_children.get(a) and len(composite_children[a]) < 2:
            rep.warn(pname, f"composite {name_of[a]!r} has a single sub-attribute; is it really composite?")

    # relationships
    rel_ends = {cid: [] for cid in rels}
    for eid, e in edges.items():
        if e["kind"] != "attr_edge" and e["source"] in rel_ends and e["target"] in entities:
            rel_ends[e["source"]].append((eid, e))
    rel_sigs = []
    identified = set()
    adjacency = {cid: set() for cid in entities}
    for rid, ends in rel_ends.items():
        rname = name_of[rid]
        if len(ends) < 2:
            rep.err(pname, f"relationship {rid} ({rname!r}) must connect at least 2 entity ends (has {len(ends)})")
            continue
        cards, roles_missing, sig_ends, card_of = [], False, [], {}
        targets = [e["target"] for _, e in ends]
        recursive = len(set(targets)) < len(targets)
        for eid, e in ends:
            lab = plain(e["value"])
            mm = re.match(r"^(1|N|M)(\s*\((.+)\))?$", lab)
            if not mm:
                rep.err(pname, f"connector {eid} of {rname!r} needs a cardinality label 1, N or M "
                               f"(optionally '1 (role)'); got {lab!r}")
                continue
            cards.append(mm.group(1))
            card_of[eid] = mm.group(1)
            sig_ends.append((name_of[e["target"]].lower(), mm.group(1), (mm.group(3) or "").strip().lower(),
                             e["kind"] == "total_edge"))
            if recursive and not mm.group(3):
                roles_missing = True
        if roles_missing:
            rep.err(pname, f"recursive relationship {rname!r}: label every end with a role, e.g. '1 (manager)'")
        if len(ends) == 2 and len(cards) == 2 and sorted(cards) not in (["1", "1"], ["1", "N"], ["M", "N"]):
            rep.err(pname, f"relationship {rname!r}: cardinality must be 1:1, 1:N or M:N, got {':'.join(cards)}")
        if verts[rid]["kind"] == "id_relationship":
            weak = [(eid, e) for eid, e in ends if verts[e["target"]]["kind"] in ("weak_entity", "ref_weak_entity")]
            # dependent end: a weak entity on a double line (an owner may itself be weak)
            dep = [(eid, e) for eid, e in weak if e["kind"] == "total_edge"] if len(ends) == 2 else []
            if len(ends) != 2 or not weak:
                rep.err(pname, f"identifying relationship {rname!r} must be binary and connect a weak entity")
            elif not dep:
                rep.err(pname, f"identifying relationship {rname!r}: weak side must be a double line (total)")
            else:
                if len(dep) == 2:
                    dep = [d for d in dep if card_of.get([o for o, _ in ends if o != d[0]][0]) == "1"]
                if len(dep) != 1:
                    rep.err(pname, f"identifying relationship {rname!r}: cannot tell the dependent weak entity "
                                   "from its owner (exactly one owner end must be labelled 1)")
                else:
                    owner_eid = [o for o, _ in ends if o != dep[0][0]][0]
                    if card_of.get(owner_eid) != "1":
                        rep.err(pname, f"identifying relationship {rname!r}: the owner end must be labelled 1")
                    else:
                        identified.add(dep[0][1]["target"])
        if not re.match(r"^[A-Z]", rname or "x"):
            rep.warn(pname, f"relationship {rname!r} should be a capitalised verb phrase")
        for t in targets:
            for u in targets:
                if t != u:
                    adjacency[t].add(u)
        rel_sigs.append((rname.lower(), tuple(sorted(sig_ends))))
        for a in attrs_of.get(rid, []):
            if verts[a]["kind"] in ("key_attribute", "partial_key"):
                rep.err(pname, f"relationship {rname!r} cannot have a key attribute ({name_of[a]!r})")

    # entities: keys, references, naming
    for cid, v in entities.items():
        n = name_of[cid]
        attrs = attrs_of.get(cid, [])
        kinds = [verts[a]["kind"] for a in attrs]
        is_ref = v["kind"] in ("ref_entity", "ref_weak_entity")
        if is_ref and attrs:
            rep.err(pname, f"reference entity {n!r} must not have attributes (draw them on its home page)")
        if not is_ref and is_overview and attrs:
            pass  # reported once as "the Overview must not show attributes"
        elif not is_ref and not is_overview:
            if v["kind"] == "weak_entity":
                if kinds.count("partial_key") != 1 or kinds.count("key_attribute"):
                    rep.err(pname, f"weak entity {n!r} needs exactly one partial key (dashed underline) and no key")
                if cid not in identified:
                    rep.err(pname, f"weak entity {n!r} is not the dependent end of an identifying relationship "
                                   "(double diamond, double line) on its home page")
            else:
                if kinds.count("key_attribute") != 1 or kinds.count("partial_key"):
                    rep.err(pname, f"entity {n!r} needs exactly one underlined key attribute "
                                   f"(found {kinds.count('key_attribute')})")
        words = n.split()
        if words and any(w[0].isalpha() and not w[0].isupper() for w in words):
            rep.warn(pname, f"entity {n!r} should be a singular noun in Title Case")
        for a in attrs:
            an = name_of[a]
            mm = FK_RE.match(an)
            ref = mm.group(1).strip().lower() if mm else None
            if ref and ref in all_entity_names and ref != n.lower():
                rep.err(pname, f"attribute {an!r} of {n!r} references entity {mm.group(1)!r}: "
                               "draw it as a relationship, not an attribute (foreign key)")
            if an and an[0].isalpha() and not an[0].isupper():
                rep.warn(pname, f"attribute {an!r} should be in Sentence case")

    for cid, v in verts.items():
        if v["kind"] in ENTITY_KINDS | REL_KINDS | ATTR_KINDS | {"sub_attribute"}:
            for rx, what in PHYSICAL_RES:
                mm = rx.search(name_of[cid])
                if mm:
                    rep.err(pname, f"{cid} label {name_of[cid]!r} contains a {what} ({mm.group(0)!r}); "
                                   "ERDs are conceptual only")
                    break
        if v["kind"] == "note":
            t = name_of[cid]
            if not (t.startswith("Constraint:") or t.startswith("Rule:")):
                rep.err(pname, f"note {cid} must start with 'Constraint:' or 'Rule:'")

    titles = [c for c, v in verts.items() if v["kind"] == "title"]
    legends = [c for c, v in verts.items() if v["kind"] == "legend"]
    if not any("Conceptual ERD" in name_of[t] for t in titles):
        rep.err(pname, "page needs a title text containing '<Project name> — Conceptual ERD'")
    if not legends:
        rep.err(pname, "page needs a notation legend (text box with the legend style)")

    check_layout(rep, pname, verts, edges)
    return {
        "name": pname,
        "entities": {name_of[c].lower(): (verts[c]["kind"], bool(attrs_of.get(c))) for c in entities},
        "display": {name_of[c].lower(): name_of[c] for c in entities},
        "rels": rel_sigs,
        "adjacency": {name_of[c].lower(): {name_of[u].lower() for u in s} for c, s in adjacency.items()},
        "has_attrs": any(v["kind"] in ATTR_KINDS | {"sub_attribute"} for v in verts.values()),
        "notes": {name_of[c] for c, v in verts.items() if v["kind"] == "note"},
    }


def check_connectivity(rep, pname, info, allow):
    adj = info["adjacency"]
    allow = {a.lower() for a in allow}
    for n, nbrs in adj.items():
        if not nbrs and n not in allow:
            rep.err(pname, f"entity {info['display'][n]!r} takes part in no relationship; add the missing "
                           "relationship or justify it with --allow-isolated")
    nodes = [n for n in adj if adj[n]]
    if not nodes:
        return
    seen, stack = {nodes[0]}, [nodes[0]]
    while stack:
        for u in adj[stack.pop()]:
            if u not in seen:
                seen.add(u)
                stack.append(u)
    rest = [info["display"][n] for n in nodes if n not in seen and n not in allow]
    if rest:
        rep.err(pname, f"entity graph is disconnected; not reachable from {info['display'][nodes[0]]!r}: "
                       f"{sorted(rest)} (add the missing relationship or justify with --allow-isolated)")


def validate(path, allow_isolated=()):
    rep = Report()
    try:
        tree = ET.parse(path)
    except ET.ParseError as ex:
        rep.err("file", f"not well-formed XML: {ex}")
        return rep, 2
    except OSError as ex:
        rep.err("file", f"cannot read: {ex}")
        return rep, 2
    root = tree.getroot()
    if root.tag != "mxfile":
        rep.err("file", f"root element must be <mxfile>, found <{root.tag}>")
        return rep, 1
    diagrams = root.findall("diagram")
    if not diagrams:
        rep.err("file", "no <diagram> pages")
        return rep, 1
    pids = [d.get("id") for d in diagrams]
    if len(set(pids)) != len(pids) or None in pids:
        rep.err("file", "every <diagram> needs a unique id")
    all_entity_names = set()
    for d in diagrams:
        for c in d.iter("mxCell"):
            if c.get("vertex") == "1" and classify_vertex(C.parse_style(c.get("style")), c.get("value")) in ENTITY_KINDS:
                all_entity_names.add(plain(c.get("value")).lower())
    multi = len(diagrams) > 1
    infos = [i for i in (analyse_page(rep, d, multi and k == 0, all_entity_names)
                         for k, d in enumerate(diagrams)) if i]
    if len(infos) != len(diagrams):
        return rep, 1
    if len(infos) == 1:
        check_connectivity(rep, infos[0]["name"], infos[0], allow_isolated)
        if len(infos[0]["entities"]) >= 10:
            rep.warn(infos[0]["name"], "10+ entities on one page: consider an Overview plus subject-area pages")
    else:
        ov, details = infos[0], infos[1:]
        if ov["name"] != "1 - Overview":
            rep.err(ov["name"], "first page of a multi-page model must be named '1 - Overview'")
        if ov["has_attrs"]:
            rep.err(ov["name"], "the Overview must not show attributes")
        check_connectivity(rep, ov["name"], ov, allow_isolated)
        all_ents = {}
        for d in details:
            for n, (kind, _) in d["entities"].items():
                all_ents.setdefault(n, []).append((d["name"], kind))
        for n, occ in all_ents.items():
            homes = [p for p, k in occ if k in ("entity", "weak_entity")]
            if len(homes) != 1:
                rep.err("file", f"entity {n!r} must have exactly one home page (found {homes or 'none'})")
            if n not in ov["entities"]:
                rep.err(ov["name"], f"entity {n!r} is missing from the Overview")
        for n, (kind, _) in ov["entities"].items():
            if kind in ("ref_entity", "ref_weak_entity"):
                rep.err(ov["name"], f"entity {n!r} must not be a reference entity on the Overview")
            if n not in all_ents:
                rep.err("file", f"entity {n!r} appears only on the Overview (needs a home page)")
        det_rels = {r for d in details for r in d["rels"]}
        for r in ov["rels"]:
            if r not in det_rels:
                rep.err("file", f"relationship {r[0]!r} between {list(r[1])} is not on any detail page")
        for r in det_rels:
            if r not in set(ov["rels"]):
                rep.err(ov["name"], f"relationship {r[0]!r} between {list(r[1])} is missing from the Overview")
        for d in details:
            for t in d["notes"] - ov["notes"]:
                rep.err(ov["name"], f"note from {d['name']!r} is not repeated on the Overview: {t[:50]!r}")
    return rep, (1 if rep.errors else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--allow-isolated", nargs="*", default=[], metavar="ENTITY",
                    help="entity names confirmed to have no relationships")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--decompress", nargs=2, metavar=("IN", "OUT"),
                    help="rewrite a compressed .drawio file as uncompressed XML")
    args = ap.parse_args(argv)
    if args.decompress:
        src, dst = args.decompress
        try:
            tree = ET.parse(src)
            for d in tree.getroot().findall("diagram"):
                if d.find("mxGraphModel") is None and (d.text or "").strip():
                    gm = ET.fromstring(decompress_diagram(d.text.strip()))
                    d.text = None
                    d.append(gm)
            ET.indent(tree.getroot(), space="  ")
            tree.write(dst, encoding="utf-8", xml_declaration=True)
        except (OSError, ET.ParseError, ValueError, zlib.error) as ex:
            print(f"ERROR: cannot decompress: {ex}", file=sys.stderr)
            return 2
        print(f"Wrote {dst}")
        return 0
    if not args.file:
        ap.error("file is required")
    rep, code = validate(args.file, args.allow_isolated)
    if args.json:
        print(json.dumps({"file": args.file, "errors": rep.errors, "warnings": rep.warnings,
                          "ok": code == 0}, indent=2))
    else:
        for e in rep.errors:
            print(f"ERROR   {e}")
        for w in rep.warnings:
            print(f"WARNING {w}")
        print(f"{'PASS' if code == 0 else 'FAIL'}: {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return code


if __name__ == "__main__":
    sys.exit(main())
