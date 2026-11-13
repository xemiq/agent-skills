#!/usr/bin/env python3
"""export_svg.py - write SVG previews of a diagrams.net (.drawio) ERD.

Usage:
  python3 export_svg.py db-design/conceptual-erd.drawio [--drawio-svg] [--no-svg]

Writes, next to the .drawio file:
  <base>.svg                single-page file: one preview
  <base>.p1.svg, .p2.svg    multi-page file: one preview per page (p1 = Overview)
  <base>.drawio.svg         with --drawio-svg: first page as SVG with the whole diagram embedded,
                            so diagrams.net can open and edit it (not diffable; the .drawio stays
                            the source of truth)

The previews are generated files: never edit them. After changing the .drawio (for example a manual
nudge in diagrams.net), run this script again. render_erd.py calls it automatically.

The drawing is an approximation of what diagrams.net shows, covering the shapes and styles of the
skill's catalog (rectangles, double rectangles, diamonds, ellipses, double ellipses, notes, text boxes,
single and double lines, edge labels, waypoints). Standard library only.
Exit codes: 0 ok, 1 file is not a readable uncompressed diagram, 2 file-system error.
"""
import argparse
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from xml.sax.saxutils import escape, quoteattr

FONT = "Helvetica, Arial, sans-serif"
MARGIN = 20


# ----------------------------------------------------------------------------- helpers
def num(v):
    """Compact, deterministic number formatting for SVG attributes."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def parse_style(style):
    out = {}
    for tok in (style or "").split(";"):
        tok = tok.strip()
        if not tok:
            continue
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k.strip()] = v.strip()
        else:
            out[tok] = None
    return out


def color(st, key, default):
    v = st.get(key, default)
    return "none" if v in (None, "none", "") else v


def char_w(fs, bold):
    return fs * (0.60 if bold else 0.55)


# ----------------------------------------------------------------------------- HTML labels
class _Label(HTMLParser):
    """Turns a draw.io HTML label into lines of runs: (text, {bold, italic, underline, dashed, size})."""

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.stack = [base]
        self.lines = [[]]

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.lines.append([])
            return
        cur = dict(self.stack[-1])
        if tag in ("b", "strong"):
            cur["bold"] = True
        elif tag in ("i", "em"):
            cur["italic"] = True
        elif tag == "u":
            cur["underline"] = True
        style = (dict(attrs).get("style") or "").replace(" ", "").lower()
        if "border-bottom" in style and "dashed" in style:
            cur["dashed"] = True
        m = re.search(r"font-size:(\d+(?:\.\d+)?)px", style)
        if m:
            cur["size"] = float(m.group(1))
        if tag in ("div", "p") and self.lines[-1]:
            self.lines.append([])
        self.stack.append(cur)

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.lines.append([])

    def handle_endtag(self, tag):
        if tag != "br" and len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data):
        data = re.sub(r"\s+", " ", data)
        if data:
            self.lines[-1].append((data, self.stack[-1]))


def label_lines(value, st, max_w):
    """Wrap a label into lines of runs that fit max_w (estimated glyph widths)."""
    fs = float(st.get("fontSize", 11))
    fstyle = int(st.get("fontStyle", 0) or 0)
    base = {"bold": bool(fstyle & 1), "italic": bool(fstyle & 2), "underline": bool(fstyle & 4),
            "dashed": False, "size": fs}
    if st.get("html") == "1":
        p = _Label(base)
        p.feed(value or "")
        p.close()
        raw = p.lines
    else:
        raw = [[(ln, base)] for ln in (value or "").split("\n")]
    out = []
    for runs in raw:
        tokens = [(t, f) for text, f in runs for t in re.findall(r"\S+|\s+", text)]
        line, width = [], 0.0
        for t, f in tokens:
            tw = len(t) * char_w(f["size"], f["bold"])
            if t.isspace():
                if line:
                    line.append((t, f))
                    width += tw
                continue
            if line and width + tw > max_w:
                while line and line[-1][0].isspace():
                    width -= len(line[-1][0]) * char_w(line[-1][1]["size"], line[-1][1]["bold"])
                    line.pop()
                out.append(line)
                line, width = [], 0.0
            line.append((t, f))
            width += tw
        while line and line[-1][0].isspace():
            line.pop()
        out.append(line)
    while out and not out[-1]:
        out.pop()
    return out


def draw_text(parts, lines, x, y, w, h, st, fill_default="#000000"):
    """Draw wrapped label lines inside the box (x, y, w, h) using the cell's align/verticalAlign."""
    if not lines:
        return
    fc = color(st, "fontColor", fill_default)
    align = st.get("align", "center")
    valign = st.get("verticalAlign", "middle")
    sp = float(st.get("spacing", 2))
    left = x + sp + float(st.get("spacingLeft", 0))
    right = x + w - sp - float(st.get("spacingRight", 0))
    sizes = [max([f["size"] for _, f in ln] or [float(st.get("fontSize", 11))]) for ln in lines]
    heights = [s * 1.25 for s in sizes]
    total = sum(heights)
    if valign == "top":
        cy = y + sp + float(st.get("spacingTop", 0))
    elif valign == "bottom":
        cy = y + h - sp - total
    else:
        cy = y + (h - total) / 2
    for ln, s, lh in zip(lines, sizes, heights):
        base_y = cy + lh * 0.8
        cy += lh
        if not ln:
            continue
        widths = [len(t) * char_w(f["size"], f["bold"]) for t, f in ln]
        lw = sum(widths)
        if align == "left":
            tx, anchor, start = left, "start", left
        elif align == "right":
            tx, anchor, start = right, "end", right - lw
        else:
            tx, anchor, start = (left + right) / 2, "middle", (left + right) / 2 - lw / 2
        merged = []  # adjacent words with the same format become one run
        for t, f in ln:
            if merged and merged[-1][1] == f:
                merged[-1] = (merged[-1][0] + t, f)
            else:
                merged.append((t, f))
        spans = []
        for t, f in merged:
            a = []
            if f["bold"]:
                a.append('font-weight="bold"')
            if f["italic"]:
                a.append('font-style="italic"')
            if f["underline"]:
                a.append('text-decoration="underline"')
            if f["size"] != s:
                a.append(f'font-size="{num(f["size"])}"')
            spans.append(f'<tspan {" ".join(a)}>{escape(t)}</tspan>' if a else escape(t))
        parts.append(f'<text x="{num(tx)}" y="{num(base_y)}" font-size="{num(s)}" fill="{fc}" '
                     f'text-anchor="{anchor}" xml:space="preserve">{"".join(spans)}</text>')
        xx = start
        for (t, f), tw in zip(ln, widths):
            if f["dashed"] and not t.isspace():
                parts.append(f'<line x1="{num(xx)}" y1="{num(base_y + 2.5)}" x2="{num(xx + tw)}" '
                             f'y2="{num(base_y + 2.5)}" stroke="{fc}" stroke-width="1" stroke-dasharray="3,2"/>')
            xx += tw


# ----------------------------------------------------------------------------- shapes
def shape_kind(st):
    if "text" in st or st.get("shape") == "text":
        return "text"
    if st.get("shape") == "note":
        return "note"
    if st.get("shape") == "rhombus" or "rhombus" in st:
        return "rhombus"
    if "ellipse" in st or st.get("shape") in ("ellipse", "doubleEllipse"):
        return "ellipse"
    return "rect"


def draw_vertex(parts, v):
    st, (x, y, w, h) = v["style"], v["geo"]
    kind = v["kind"]
    fill, stroke = color(st, "fillColor", "#ffffff"), color(st, "strokeColor", "#000000")
    if kind == "text":
        fill, stroke = color(st, "fillColor", "none"), color(st, "strokeColor", "none")
    dash = ' stroke-dasharray="5,3"' if st.get("dashed") == "1" else ""
    common = f'fill="{fill}" stroke="{stroke}"{dash}'
    if kind == "text":
        if fill != "none" or stroke != "none":
            parts.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" {common}/>')
    elif kind == "note":
        s = float(st.get("size", 14))
        parts.append(f'<path d="M{num(x)},{num(y)} H{num(x + w - s)} L{num(x + w)},{num(y + s)} V{num(y + h)} '
                     f'H{num(x)} Z" {common}/>')
        parts.append(f'<path d="M{num(x + w - s)},{num(y)} V{num(y + s)} H{num(x + w)}" fill="none" '
                     f'stroke="{stroke}"/>')
    elif kind == "rhombus":
        cx, cy = x + w / 2, y + h / 2
        parts.append(f'<polygon points="{num(cx)},{num(y)} {num(x + w)},{num(cy)} {num(cx)},{num(y + h)} '
                     f'{num(x)},{num(cy)}" {common}/>')
        if st.get("double") == "1":
            dy = 6
            dx = dy * w / h
            parts.append(f'<polygon points="{num(cx)},{num(y + dy)} {num(x + w - dx)},{num(cy)} '
                         f'{num(cx)},{num(y + h - dy)} {num(x + dx)},{num(cy)}" fill="none" stroke="{stroke}"{dash}/>')
    elif kind == "ellipse":
        cx, cy = x + w / 2, y + h / 2
        parts.append(f'<ellipse cx="{num(cx)}" cy="{num(cy)}" rx="{num(w / 2)}" ry="{num(h / 2)}" {common}/>')
        if st.get("shape") == "doubleEllipse":
            parts.append(f'<ellipse cx="{num(cx)}" cy="{num(cy)}" rx="{num(w / 2 - 4)}" ry="{num(h / 2 - 4)}" '
                         f'fill="none" stroke="{stroke}"{dash}/>')
    else:
        parts.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" {common}/>')
        if st.get("double") == "1":
            m = float(st.get("margin", 3))
            parts.append(f'<rect x="{num(x + m)}" y="{num(y + m)}" width="{num(w - 2 * m)}" '
                         f'height="{num(h - 2 * m)}" fill="none" stroke="{stroke}"{dash}/>')
    if kind == "text":
        lines = label_lines(v["value"], st, w - 2 * float(st.get("spacing", 2)))
    else:
        lines = label_lines(v["value"], st, w - 8)
    draw_text(parts, lines, x, y, w, h, st)


def clip(v, toward):
    """Point where the line from the centre of shape v toward `toward` leaves the shape."""
    x, y, w, h = v["geo"]
    cx, cy = x + w / 2, y + h / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    hw, hh = w / 2, h / 2
    if (dx == 0 and dy == 0) or hw <= 0 or hh <= 0:
        return cx, cy
    if v["kind"] == "ellipse":
        t = 1 / math.sqrt((dx / hw) ** 2 + (dy / hh) ** 2)
    elif v["kind"] == "rhombus":
        t = 1 / (abs(dx) / hw + abs(dy) / hh)
    else:
        t = min(hw / abs(dx) if dx else math.inf, hh / abs(dy) if dy else math.inf)
    t = min(t, 1.0)
    return cx + dx * t, cy + dy * t


def point_along(pts, frac):
    segs = list(zip(pts, pts[1:]))
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    total = sum(lens)
    if total == 0:
        return pts[0]
    d = total * frac
    for (a, b), ln in zip(segs, lens):
        if d <= ln and ln > 0:
            return a[0] + (b[0] - a[0]) * d / ln, a[1] + (b[1] - a[1]) * d / ln
        d -= ln
    return pts[-1]


def edge_path(e, verts):
    s, t = verts.get(e["source"]), verts.get(e["target"])
    if not s or not t:
        return None
    sc = (s["geo"][0] + s["geo"][2] / 2, s["geo"][1] + s["geo"][3] / 2)
    tc = (t["geo"][0] + t["geo"][2] / 2, t["geo"][1] + t["geo"][3] / 2)
    mid = e["points"]
    start = clip(s, mid[0] if mid else tc)
    end = clip(t, mid[-1] if mid else sc)
    return [start] + mid + [end]


def draw_edge(parts, e, pts):
    st = e["style"]
    stroke = color(st, "strokeColor", "#000000")
    path = " ".join(f"{num(x)},{num(y)}" for x, y in pts)
    dash = ' stroke-dasharray="5,3"' if st.get("dashed") == "1" else ""
    if st.get("shape") == "link":  # double line: a wide stroke with a white core
        parts.append(f'<polyline points="{path}" fill="none" stroke="{stroke}" stroke-width="5"{dash}/>')
        parts.append(f'<polyline points="{path}" fill="none" stroke="#ffffff" stroke-width="3"/>')
    else:
        parts.append(f'<polyline points="{path}" fill="none" stroke="{stroke}" stroke-width="1"{dash}/>')


def draw_edge_label(parts, e, pts):
    st = e["style"]
    lines = label_lines(e["value"], st, 400)
    if not lines:
        return None
    frac = (e["label_x"] + 1) / 2 if e["label_x"] is not None else 0.5
    lx, ly = point_along(pts, frac)
    sizes = [max(f["size"] for _, f in ln) if ln else float(st.get("fontSize", 11)) for ln in lines]
    w = max(sum(len(t) * char_w(f["size"], f["bold"]) for t, f in ln) for ln in lines) + 6
    h = sum(s * 1.25 for s in sizes) + 2
    box = (lx - w / 2, ly - h / 2, w, h)
    bg = color(st, "labelBackgroundColor", "none")
    if bg != "none":
        parts.append(f'<rect x="{num(box[0])}" y="{num(box[1])}" width="{num(w)}" height="{num(h)}" fill="{bg}"/>')
    draw_text(parts, lines, *box, dict(st, align="center", verticalAlign="middle", spacing="0"))
    return box


# ----------------------------------------------------------------------------- pages
def read_page(diagram):
    """Vertices and edges of one <diagram>, with absolute geometry. None if the page is compressed."""
    gm = diagram.find("mxGraphModel")
    if gm is None:
        return None
    root = gm.find("root")
    cells = list(root.findall("mxCell")) if root is not None else []
    for wrapper in (root.findall("object") + root.findall("UserObject")) if root is not None else []:
        inner = wrapper.find("mxCell")
        if inner is not None:
            inner.set("id", wrapper.get("id", ""))
            inner.set("value", wrapper.get("label", ""))
            cells.append(inner)
    order = {c.get("id"): i for i, c in enumerate(cells)}
    edge_ids = {c.get("id") for c in cells if c.get("edge") == "1"}
    offsets, verts, edges, labels = {}, {}, {}, {}
    for c in cells:
        cid, parent = c.get("id"), c.get("parent")
        if cid in ("0", "1"):
            continue
        st = parse_style(c.get("style"))
        geo = c.find("mxGeometry")
        if c.get("vertex") == "1" and ("edgeLabel" in st or parent in edge_ids):
            labels[parent] = (labels.get(parent, "") + " " + (c.get("value") or "")).strip()
            continue
        try:
            gx = float(geo.get("x", 0)) if geo is not None else 0.0
            gy = float(geo.get("y", 0)) if geo is not None else 0.0
        except ValueError:
            continue
        ox, oy = offsets.get(parent, (0.0, 0.0))
        if c.get("vertex") == "1" and ("group" in st or (c.get("connectable") == "0" and not c.get("value"))):
            offsets[cid] = (ox + gx, oy + gy)
            continue
        if c.get("vertex") == "1" and geo is not None:
            try:
                w, h = float(geo.get("width", 0)), float(geo.get("height", 0))
            except ValueError:
                continue
            verts[cid] = {"geo": (ox + gx, oy + gy, w, h), "style": st, "kind": shape_kind(st),
                          "value": c.get("value") or "", "order": order[cid]}
        elif c.get("edge") == "1":
            pts = []
            lx = None
            if geo is not None:
                try:
                    lx = float(geo.get("x")) if geo.get("x") is not None else None
                    arr = geo.find("Array")
                    if arr is not None:
                        pts = [(float(p.get("x", 0)) + ox, float(p.get("y", 0)) + oy) for p in arr.findall("mxPoint")]
                except ValueError:
                    pts, lx = [], None
            edges[cid] = {"style": st, "source": c.get("source"), "target": c.get("target"),
                          "value": c.get("value") or "", "points": pts, "label_x": lx, "order": order[cid]}
    for eid, text in labels.items():
        if eid in edges and not edges[eid]["value"]:
            edges[eid]["value"] = text
            edges[eid]["style"] = dict(edges[eid]["style"], html="1")
    return verts, edges


def page_svg(diagram, embed=None):
    """SVG text for one <diagram> page. `embed` = mxfile XML to store in a .drawio.svg."""
    data = read_page(diagram)
    if data is None:
        raise ValueError(f"page {diagram.get('name')!r} is compressed; run validate_erd.py --decompress first")
    verts, edges = data
    label_parts = []
    xs, ys = [], []
    for v in verts.values():
        x, y, w, h = v["geo"]
        xs += [x, x + w]
        ys += [y, y + h]
    items = sorted([("v", k, v) for k, v in verts.items()] + [("e", k, e) for k, e in edges.items()],
                   key=lambda it: it[2]["order"])
    body = []
    for kind, _, it in items:
        if kind == "v":
            draw_vertex(body, it)
        else:
            pts = edge_path(it, verts)
            if not pts:
                continue
            draw_edge(body, it, pts)
            xs += [p[0] for p in pts]
            ys += [p[1] for p in pts]
            if it["value"]:
                box = draw_edge_label(label_parts, it, pts)
                if box:
                    xs += [box[0], box[0] + box[2]]
                    ys += [box[1], box[1] + box[3]]
    if not xs:
        xs, ys = [0, 100], [0, 100]
    minx, miny = min(xs) - MARGIN, min(ys) - MARGIN
    w, h = max(xs) + MARGIN - minx, max(ys) + MARGIN - miny
    extra = f" content={quoteattr(embed)}" if embed is not None else ""
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{num(w)}" height="{num(h)}" '
            f'viewBox="{num(minx)} {num(miny)} {num(w)} {num(h)}" font-family="{FONT}"{extra}>')
    title = f"<title>{escape(diagram.get('name') or 'ERD')}</title>"
    bg = f'<rect x="{num(minx)}" y="{num(miny)}" width="{num(w)}" height="{num(h)}" fill="#ffffff"/>'
    return "\n".join([head, title, bg] + body + label_parts + ["</svg>"]) + "\n"


def preview_paths(drawio_path, n_pages):
    """File names of the previews for a .drawio file with n_pages pages."""
    base = drawio_path[:-len(".drawio")] if drawio_path.endswith(".drawio") else drawio_path
    if n_pages == 1:
        return [base + ".svg"]
    return [f"{base}.p{i}.svg" for i in range(1, n_pages + 1)]


def export(xml_text, drawio_path, svg=True, drawio_svg=False):
    """Write the previews for the diagram `xml_text` saved at `drawio_path`. Returns the written paths."""
    root = ET.fromstring(xml_text)
    if root.tag != "mxfile":
        raise ValueError("root element must be <mxfile>")
    pages = root.findall("diagram")
    if not pages:
        raise ValueError("no <diagram> pages")
    written = []
    if svg:
        for d, path in zip(pages, preview_paths(drawio_path, len(pages))):
            with open(path, "w", encoding="utf-8") as f:
                f.write(page_svg(d))
            written.append(path)
    if drawio_svg:
        base = drawio_path[:-len(".drawio")] if drawio_path.endswith(".drawio") else drawio_path
        path = base + ".drawio.svg"
        embed = ET.tostring(root, encoding="unicode")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page_svg(pages[0], embed=embed))
        written.append(path)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drawio")
    ap.add_argument("--drawio-svg", action="store_true", help="also write an editable <base>.drawio.svg")
    ap.add_argument("--no-svg", action="store_true", help="skip the plain .svg previews")
    args = ap.parse_args(argv)
    if not args.drawio.endswith(".drawio"):
        print("ERROR: the input must be a .drawio file", file=sys.stderr)
        return 1
    try:
        with open(args.drawio, encoding="utf-8-sig") as f:
            xml_text = f.read()
    except OSError as ex:
        print(f"ERROR: cannot read {args.drawio}: {ex}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as ex:
        print(f"ERROR: {args.drawio} is not UTF-8 text: {ex}", file=sys.stderr)
        return 1
    try:
        written = export(xml_text, args.drawio, svg=not args.no_svg, drawio_svg=args.drawio_svg)
    except (ET.ParseError, ValueError) as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 1
    except OSError as ex:
        print(f"ERROR: cannot write preview: {ex}", file=sys.stderr)
        return 2
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
