#!/usr/bin/env python3
"""Regression tests for the db-erd-chen skill scripts (standard library only).

Run from anywhere:  python3 skills/db-erd-chen/tests/test_skill.py
"""
import base64
import copy
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.parse
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import render_erd  # noqa: E402
import validate_erd  # noqa: E402

EXAMPLE = os.path.join(SKILL, "examples", "task-tracker", "model.json")
MULTI = os.path.join(HERE, "fixtures", "order-management.model.json")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class RenderValidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self.tmp.name, "db-design")

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, model):
        path = os.path.join(self.tmp.name, "m.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(model, f)
        code = render_erd.main([path, "--out-dir", self.out])
        return code

    def latest(self):
        files = sorted(f for f in os.listdir(self.out) if f.endswith(".drawio"))
        return os.path.join(self.out, files[-1])

    def assert_valid(self, path):
        rep, code = validate_erd.validate(path)
        self.assertEqual(code, 0, "\n".join(rep.errors))

    def test_example_renders_and_validates(self):
        self.assertEqual(self.render(load(EXAMPLE)), 0)
        self.assert_valid(os.path.join(self.out, "conceptual-erd.drawio"))
        for ext in (".summary.md", ".model.json"):
            self.assertTrue(os.path.exists(os.path.join(self.out, "conceptual-erd" + ext)))

    def test_committed_example_output_is_valid(self):
        self.assert_valid(os.path.join(SKILL, "examples", "task-tracker", "db-design", "conceptual-erd.drawio"))

    def test_multi_page_renders_and_validates(self):
        self.assertEqual(self.render(load(MULTI)), 0)
        path = os.path.join(self.out, "conceptual-erd.drawio")
        self.assert_valid(path)
        xml = read(path)
        self.assertIn('name="1 - Overview"', xml)
        self.assertIn("dashed=1;fillColor=#f5f5f5", xml)  # reference entities exist

    def test_never_overwrites_creates_new_version(self):
        self.render(load(EXAMPLE))
        self.render(load(EXAMPLE))
        self.assertTrue(os.path.exists(os.path.join(self.out, "conceptual-erd-v2.drawio")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "conceptual-erd-v2.summary.md")))

    def test_render_is_deterministic(self):
        self.render(load(EXAMPLE))
        self.render(load(EXAMPLE))
        a = read(os.path.join(self.out, "conceptual-erd.drawio"))
        b = read(os.path.join(self.out, "conceptual-erd-v2.drawio"))
        self.assertEqual(a, b)

    def test_html_special_characters_are_escaped(self):
        m = load(EXAMPLE)
        m["project"] = 'R&D <Tools> "X"'
        m["entities"][0]["attributes"][1]["name"] = "Budget & <limits>"
        self.assertEqual(self.render(m), 0)
        self.assert_valid(self.latest())


class DocumentationSyncTests(unittest.TestCase):
    def test_skill_md_snippet_matches_committed_example(self):
        skill = read(os.path.join(SKILL, "SKILL.md"))
        snippet = skill.split("```xml", 1)[1].split("```", 1)[0]
        example = read(os.path.join(SKILL, "examples", "task-tracker", "db-design", "conceptual-erd.drawio"))
        example_lines = {ln.strip() for ln in example.splitlines()}
        for ln in snippet.splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("<!--"):
                self.assertIn(ln, example_lines, f"SKILL.md snippet line not in example output: {ln}")

    def test_committed_example_is_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_erd.main([EXAMPLE, "--out-dir", tmp])
            fresh = read(os.path.join(tmp, "conceptual-erd.drawio"))
        committed = read(os.path.join(SKILL, "examples", "task-tracker", "db-design", "conceptual-erd.drawio"))
        self.assertEqual(fresh, committed, "re-render the example (see SKILL.md section 12)")


class ModelRejectionTests(unittest.TestCase):
    def problems(self, mutate):
        m = load(EXAMPLE)
        mutate(m)
        with self.assertRaises(render_erd.ModelError) as cm:
            render_erd.normalize_model(m)
        return " | ".join(cm.exception.problems)

    def test_unconfirmed_assumption_rejected(self):
        p = self.problems(lambda m: m["assumptions"].append({"text": "guess", "confirmed_by": "agent"}))
        self.assertIn("open_questions", p)

    def test_many_to_many_needs_m_and_n(self):
        def f(m):
            m["relationships"][0]["ends"][0]["card"] = "N"
        self.assertIn("M:N", self.problems(f))

    def test_entity_without_key(self):
        def f(m):
            m["entities"][0]["attributes"][0]["kind"] = "simple"
        self.assertIn("exactly one 'key'", self.problems(f))

    def test_weak_entity_needs_identifying_relationship(self):
        def f(m):
            m["relationships"] = [r for r in m["relationships"] if r["id"] != "contains"]
        self.assertIn("identifying relationship", self.problems(f))

    def test_recursive_needs_roles(self):
        def f(m):
            del m["relationships"][-1]["ends"][0]["role"]
        self.assertIn("role", self.problems(f))

    def test_note_prefix(self):
        self.assertIn("Constraint:", self.problems(lambda m: m["notes"].append({"text": "Status is required"})))


class ValidatorNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = os.path.join(cls.tmp.name, "db-design")
        render_erd.main([EXAMPLE, "--out-dir", out])
        with open(os.path.join(out, "conceptual-erd.drawio"), encoding="utf-8") as f:
            cls.good = f.read()
        render_erd.main([MULTI, "--out-dir", out])
        with open(os.path.join(out, "conceptual-erd-v2.drawio"), encoding="utf-8") as f:
            cls.good_multi = f.read()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def errors_for(self, xml):
        path = os.path.join(self.tmp.name, "case.drawio")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        rep, code = validate_erd.validate(path)
        return code, " | ".join(rep.errors)

    def sub(self, old, new, base=None, count=1):
        base = base or self.good
        self.assertIn(old, base)
        return base.replace(old, new, count)

    def test_malformed_xml(self):
        code, _ = self.errors_for(self.good[:-30])
        self.assertEqual(code, 2)

    def test_foreign_key_attribute(self):
        code, e = self.errors_for(self.sub('value="Created on"', 'value="User ID"'))
        self.assertIn("foreign key", e)

    def test_data_type_and_snake_case(self):
        _, e = self.errors_for(self.sub('value="Title"', 'value="title varchar(200)"'))
        self.assertIn("data type", e)
        _, e = self.errors_for(self.sub('value="Title"', 'value="task_title"'))
        self.assertIn("snake_case", e)

    def test_missing_cardinality(self):
        _, e = self.errors_for(self.sub('value="M"', 'value=""'))
        self.assertIn("cardinality", e)

    def test_dangling_edge(self):
        _, e = self.errors_for(self.sub('target="E_team"', 'target="E_nothing"'))
        self.assertIn("dangling", e)

    def test_arrowhead(self):
        _, e = self.errors_for(self.sub("endArrow=none;html=1;rounded=0;strokeColor=#888888;",
                                        "endArrow=block;html=1;rounded=0;strokeColor=#888888;"))
        self.assertIn("arrowheads", e)

    def test_orphan_attribute(self):
        xml = re.sub(r'<mxCell id="e\d+" style="endArrow=none;html=1;rounded=0;strokeColor=#888888;" '
                     r'edge="1" parent="1" source="a1" target="[^"]+">\s*<mxGeometry relative="1" as="geometry" />\s*</mxCell>',
                     "", self.good, count=1)
        self.assertNotEqual(xml, self.good)
        _, e = self.errors_for(xml)
        self.assertIn("orphan", e)

    def test_isolated_entity(self):
        extra = ('<mxCell id="E_audit" value="Audit Entry" style="whiteSpace=wrap;html=1;align=center;'
                 'fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">'
                 '<mxGeometry x="3000" y="3000" width="150" height="56" as="geometry" /></mxCell></root>')
        xml = self.sub("</root>", extra)
        _, e = self.errors_for(xml)
        self.assertIn("takes part in no relationship", e)
        path = os.path.join(self.tmp.name, "iso.drawio")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        rep, _ = validate_erd.validate(path, ["Audit Entry"])
        self.assertFalse(any("Audit Entry" in x and "relationship" in x for x in rep.errors))

    def test_overlap_detected(self):
        m = re.search(r'id="E_team"[^>]*>\s*<mxGeometry x="(\d+)" y="(\d+)"', self.good)
        xml = re.sub(r'(id="E_project"[^>]*>\s*<mxGeometry) x="\d+" y="\d+"',
                     rf'\1 x="{m.group(1)}" y="{m.group(2)}"', self.good)
        _, e = self.errors_for(xml)
        self.assertIn("overlap", e)

    def test_style_drift(self):
        _, e = self.errors_for(self.sub("fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;\" vertex",
                                        "fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=16;\" vertex"))
        self.assertIn("style differs", e)

    def test_compressed_page_reported_and_decompressible(self):
        inner = self.good.split("<diagram", 1)[1].split(">", 1)[1].rsplit("</diagram>", 1)[0].strip()
        comp = zlib.compressobj(9, zlib.DEFLATED, -15)
        data = comp.compress(urllib.parse.quote(inner, safe="").encode()) + comp.flush()
        b64 = base64.b64encode(data).decode()
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net">'
               f'<diagram id="erd" name="1 - Conceptual ERD">{b64}</diagram></mxfile>')
        code, e = self.errors_for(xml)
        self.assertIn("compressed", e)
        src = os.path.join(self.tmp.name, "case.drawio")
        dst = os.path.join(self.tmp.name, "plain.drawio")
        self.assertEqual(validate_erd.main(["--decompress", src, dst]), 0)
        rep, code = validate_erd.validate(dst)
        self.assertEqual(code, 0, rep.errors)

    def test_overview_with_attribute_and_missing_entity(self):
        ov = self.good_multi.split("</diagram>")[0]
        bad_ov = ov.replace('value="Warehouse"', 'value="Depot"', 1)
        xml = self.good_multi.replace(ov, bad_ov, 1)
        _, e = self.errors_for(xml)
        self.assertIn("missing from the Overview", e)

    def test_reference_entity_with_attribute(self):
        pages = self.good_multi.split("</diagram>")
        catalog = [p for p in pages if 'name="3 - Catalog"' in p][0]
        rid = re.search(r'id="(E_\w+)" value="Order Line" style="[^"]*dashed=1', self.good_multi)
        self.assertIsNone(rid)  # Order Line is not on Catalog; use Sales page reference Product instead
        sales = [p for p in pages if 'name="2 - Sales"' in p][0]
        extra = ('<mxCell id="a999" value="Price" style="ellipse;whiteSpace=wrap;html=1;align=center;'
                 'fillColor=#ffffff;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">'
                 '<mxGeometry x="5000" y="5000" width="124" height="44" as="geometry" /></mxCell>'
                 '<mxCell id="e999" style="endArrow=none;html=1;rounded=0;strokeColor=#888888;" edge="1" '
                 'parent="1" source="a999" target="E_product"><mxGeometry relative="1" as="geometry" /></mxCell></root>')
        xml = self.good_multi.replace(sales, sales.replace("</root>", extra), 1)
        _, e = self.errors_for(xml)
        self.assertIn("reference entity", e)
        self.assertTrue(catalog)


def _ent(i, weak=False, area=None, extra=()):
    e = {"id": i, "name": i.capitalize() + " item", "weak": weak,
         "attributes": [{"name": "Code", "kind": "partial_key" if weak else "key"}, {"name": "Label"}] + list(extra)}
    if area:
        e["area"] = area
    return e


def _rel(i, a, b, ca="1", cb="N", ident=False, total_b=False):
    return {"id": i, "name": "Has " + i, "identifying": ident,
            "ends": [{"entity": a, "card": ca}, {"entity": b, "card": cb, "total": total_b}]}


class AdversarialRegressionTests(unittest.TestCase):
    """Cases found by the adversarial review (v0.1.0)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def render_validate(self, model, allow=()):
        path = os.path.join(self.tmp.name, "m.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(model, f)
        out = os.path.join(self.tmp.name, "out")
        code = render_erd.main([path, "--out-dir", out])
        self.assertEqual(code, 0)
        files = sorted(f for f in os.listdir(out) if f.endswith(".drawio"))
        rep, vcode = validate_erd.validate(os.path.join(out, files[-1]), allow)
        return vcode, rep

    def assert_rejected(self, model, fragment):
        with self.assertRaises(render_erd.ModelError) as cm:
            render_erd.normalize_model(model)
        self.assertIn(fragment, " | ".join(cm.exception.problems))

    def test_malformed_types_give_clean_errors(self):
        bad = [
            {"project": "T", "entities": "abc"},
            {"project": "T", "entities": [_ent("a")], "relationships": None, "notes": ["Rule: x"]},
            {"project": "T", "entities": [{"id": "a", "name": "A", "attributes": "Name"}]},
            {"project": "T", "entities": [_ent("a"), _ent("b")], "relationships": [{"id": "r", "name": "R", "ends": ["a", "b"]}]},
            {"project": None, "entities": [_ent("a")]},
            {"project": "T", "entities": [dict(_ent("a"), weak="false")]},
            {"project": "T", "entities": [_ent("a")], "layout": {"main": {"positions": {"a": "00"}}}},
            {"project": "T", "entities": [_ent("a")], "layout": {"main": None}},
            {"project": "T", "entities": [_ent("a", extra=[{"name": "Addr", "kind": "composite", "parts": "Street"}])]},
        ]
        for m in bad:
            with self.assertRaises(render_erd.ModelError, msg=str(m)):
                render_erd.normalize_model(m)

    def test_bom_and_non_utf8_model_files(self):
        path = os.path.join(self.tmp.name, "bom.json")
        with open(path, "w", encoding="utf-8-sig") as f:
            json.dump(load(EXAMPLE), f)
        self.assertEqual(render_erd.main([path, "--check"]), 0)
        with open(path, "wb") as f:
            f.write(b'{"project": "\xff\xfe"}'.replace(b"\\", b"\\") + b"\xff")
        self.assertEqual(render_erd.main([path, "--check"]), 1)

    def test_empty_area_rejected(self):
        m = load(MULTI)
        m["areas"].append({"id": "empty", "name": "Empty"})
        self.assert_rejected(m, "has no entities")

    def test_ternary_cannot_repeat_entity(self):
        m = {"project": "T", "entities": [_ent("a"), _ent("b")], "relationships": [
            {"id": "t", "name": "Links", "ends": [{"entity": "a", "card": "M", "role": "x"},
                                                  {"entity": "a", "card": "N", "role": "y"},
                                                  {"entity": "b", "card": "N", "role": "z"}]}]}
        self.assert_rejected(m, "ternary relationship cannot repeat")

    def test_parallel_relationships_on_vertical_pair(self):
        m = {"project": "T", "entities": [_ent("a"), _ent("b")],
             "relationships": [_rel("ra", "a", "b"), _rel("rb", "a", "b"), _rel("rc", "a", "b")],
             "layout": {"main": {"positions": {"a": [0, 0], "b": [0, 1]}}}}
        code, rep = self.render_validate(m)
        self.assertEqual(code, 0, rep.errors)

    def test_multi_page_without_layout_validates(self):
        m = load(MULTI)
        m.pop("layout")
        code, rep = self.render_validate(m)
        self.assertEqual(code, 0, rep.errors)

    def test_weak_entity_owned_by_weak_entity(self):
        m = {"project": "T", "entities": [_ent("bld"), _ent("room", True), _ent("seat", True)],
             "relationships": [_rel("has", "bld", "room", ident=True, total_b=True),
                               _rel("holds", "room", "seat", ident=True, total_b=True)]}
        code, rep = self.render_validate(m)
        self.assertEqual(code, 0, rep.errors)

    def test_identifying_relationship_drawn_on_weak_entity_home_page(self):
        m = {"project": "T", "areas": [{"id": "x", "name": "X"}, {"id": "z", "name": "Z"}],
             "entities": [_ent("own", area="x"), _ent("wk", True, "z")],
             "relationships": [_rel("idr", "own", "wk", ident=True, total_b=True)]}
        code, rep = self.render_validate(m)
        self.assertEqual(code, 0, rep.errors)

    def test_business_words_are_not_data_types(self):
        extra = [{"name": n} for n in ("Serial number", "Blob storage size", "Time (24h)", "Number (1-10) rating",
                                       "Date of birth", "Time zone", "Index number", "Cascade level")]
        m = {"project": "T", "entities": [_ent("a", extra=extra), _ent("b")], "relationships": [_rel("ab", "a", "b")]}
        code, rep = self.render_validate(m)
        self.assertEqual(code, 0, rep.errors)

    def test_physical_names_are_caught(self):
        for name in ("Price (decimal)", "Name String", "Primary key", "CustomerID", "Customer_ID", "customerId",
                     "Code varchar(20)"):
            m = {"project": "T", "entities": [_ent("a", extra=[{"name": name}]), _ent("customer")],
                 "relationships": [_rel("ab", "a", "customer")]}
            code, rep = self.render_validate(m)
            self.assertEqual(code, 1, f"{name!r} should be rejected")

    def test_composite_key(self):
        m = {"project": "T", "entities": [
            {"id": "flight", "name": "Flight", "attributes": [
                {"name": "Flight ID", "kind": "key", "parts": ["Flight number", "Departure date"]}, {"name": "Gate"}]},
            _ent("b")], "relationships": [_rel("ab", "flight", "b")]}
        code, rep = self.render_validate(m)
        self.assertEqual(code, 0, rep.errors)

    def test_versioning_never_reuses_gaps(self):
        out = os.path.join(self.tmp.name, "dd")
        for _ in range(3):
            render_erd.main([EXAMPLE, "--out-dir", out])
        for ext in (".drawio", ".summary.md", ".model.json"):
            os.remove(os.path.join(out, "conceptual-erd-v2" + ext))
        render_erd.main([EXAMPLE, "--out-dir", out])
        self.assertTrue(os.path.exists(os.path.join(out, "conceptual-erd-v4.drawio")))

    def test_summary_escapes_pipes(self):
        m = load(EXAMPLE)
        m["entities"][0]["attributes"][1]["name"] = "Budget | limit"
        render_erd.normalize_model(m)
        _, pages, _ = render_erd.build(m)
        self.assertIn("Budget \\| limit", render_erd.summary_md(m, "x.drawio", pages))


class ValidatorRegressionTests(ValidatorNegativeTests):
    """Validator cases found by the adversarial review (v0.1.0)."""

    def test_entity_without_attributes_needs_key(self):
        xml = re.sub(r'<mxCell id="(e\d+)" style="endArrow=none;html=1;rounded=0;strokeColor=#888888;" '
                     r'edge="1" parent="1" source="(a\d+)" target="E_team">.*?</mxCell>', "", self.good, flags=re.S)
        _, e = self.errors_for(xml)
        self.assertIn("Team", e)
        self.assertIn("key", e)

    def test_overview_must_match_detail_cardinality(self):
        ov = self.good_multi.split("</diagram>")[0]
        m = re.search(r'<mxCell id="(e\d+)" value="1" style="endArrow=none[^"]*" edge="1" parent="1" '
                      r'source="R_places" target="E_customer">', ov)
        self.assertIsNotNone(m)
        bad = ov.replace(m.group(0), m.group(0).replace('value="1"', 'value="N"', 1))
        _, e = self.errors_for(self.good_multi.replace(ov, bad, 1))
        self.assertIn("Places", e.replace("places", "Places"))

    def test_identifying_owner_must_be_one(self):
        xml = self.good
        xml = re.sub(r'(value=")1(" style="endArrow=none[^"]*" edge="1" parent="1" source="R_contains")', r"\1N\2", xml)
        _, e = self.errors_for(xml)
        self.assertIn("owner end must be labelled 1", e)

    def test_hand_added_edge_label_and_bad_waypoint(self):
        xml = self.sub('value="M" style=', 'value="" style=')
        xml = xml.replace("</root>", '<mxCell id="lbl1" value="M" style="edgeLabel;html=1;align=center;" vertex="1" '
                          'connectable="0" parent="' + re.search(r'<mxCell id="(e\d+)" value="" style=', xml).group(1) +
                          '"><mxGeometry x="0.6" relative="1" as="geometry" /></mxCell></root>')
        code, e = self.errors_for(xml)
        self.assertNotIn("catalog element", e)
        self.assertNotIn("cardinality label", e)
        bad_wp = self.good.replace('<mxPoint x="105" y="220" />', '<mxPoint x="abc" y="220" />', 1)
        code, e = self.errors_for(bad_wp)
        self.assertIn("non-numeric waypoint", e)


if __name__ == "__main__":
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):  # silence "Wrote ..." lines from the renderer
        result = unittest.main(verbosity=0, exit=False).result
    print(f"Ran {result.testsRun} tests: {len(result.failures)} failures, {len(result.errors)} errors")
    sys.exit(0 if result.wasSuccessful() else 1)
