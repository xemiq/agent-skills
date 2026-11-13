# Manual fallback: writing the `.drawio` XML by hand

Use this only when `python3` is not available (SKILL.md §4, Step 7b). On the normal path the
renderer writes the XML, and you never edit it by hand.

## 1. Procedure

1. Finish Steps 1–5 of the SKILL.md workflow as usual, including the clarification gate.
2. Write the XML following `references/erd-guide.md` §4:
   - the structure `<mxfile><diagram><mxGraphModel><root>`, with the mandatory first cells
     `id="0"` and `id="1" parent="0"`;
   - the exact styles and sizes from the guide's §4.5 catalog (which `scripts/erd_catalog.py` mirrors);
   - the id convention from guide §4.6: `E_<entity>`, `R_<relationship>`, `a<n>`, `s<n>`, `e<n>`,
     `n<n>`, `t<n>`, `l<n>`;
   - relationship connectors go from the diamond (source) to the entity (target), attribute
     connectors from the ellipse to its owner, with the cardinality as the connector `value` and
     `x="0.6"` so the label sits next to the entity;
   - values XML-escaped (and HTML-escaped, since `html=1`). Never compress the file.
   - a title and a legend on every page, and the multi-page rules of guide §3.1 if there are areas.
3. Pick the version name yourself following SKILL.md §5.2: the next free `-vN`, never overwrite.
4. Write the `.summary.md` by hand with the same sections the renderer produces: entities, keys,
   attributes, relationships with ratio and participation, notes, confirmed assumptions with their
   source, open questions, omitted items.
5. The validator cannot run, so check every item of the SKILL.md §7 checklist **and** guide §5
   item by item.
6. Say in the chat summary that the file was hand-written and validated manually.

## 2. Template

From `examples/task-tracker/db-design/conceptual-erd.drawio`: the weak entity, its identifying
relationship and partial key, and a recursive role-labelled end. The minimal complete example is in
guide §4.7.

```xml
<mxfile host="app.diagrams.net" agent="db-erd-chen skill" version="24.0.0">
  <diagram id="erd" name="1 - Conceptual ERD">
    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="E_project" value="Project" style="whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">
          <mxGeometry x="1206" y="810" width="150" height="56" as="geometry" />
        </mxCell>
        <mxCell id="E_task" value="Task" style="shape=ext;margin=3;double=1;whiteSpace=wrap;html=1;align=center;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;" vertex="1" parent="1">
          <mxGeometry x="310" y="810" width="150" height="56" as="geometry" />
        </mxCell>
        <mxCell id="R_contains" value="Contains" style="shape=rhombus;double=1;perimeter=rhombusPerimeter;whiteSpace=wrap;html=1;align=center;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="768" y="801" width="130" height="74" as="geometry" />
        </mxCell>
        <mxCell id="a12" value="&lt;span style=&quot;border-bottom: 1px dashed;&quot;&gt;Task #&lt;/span&gt;" style="ellipse;whiteSpace=wrap;html=1;align=center;fillColor=#ffffff;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="194" y="884" width="124" height="44" as="geometry" />
        </mxCell>
        <!-- … other entities, attributes, title, legend and notes … -->
        <mxCell id="e5" value="1" style="endArrow=none;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_contains" target="E_project">
          <mxGeometry x="0.6" relative="1" as="geometry">
            <mxPoint as="offset" />
          </mxGeometry>
        </mxCell>
        <mxCell id="e6" value="N" style="shape=link;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_contains" target="E_task">
          <mxGeometry x="0.6" relative="1" as="geometry">
            <mxPoint as="offset" />
          </mxGeometry>
        </mxCell>
        <mxCell id="e9" value="1 (mentor)" style="endArrow=none;html=1;rounded=0;fontStyle=1;fontSize=13;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="R_mentors" target="E_user">
          <mxGeometry x="0.6" relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="105" y="220" />
              <mxPoint x="325" y="220" />
            </Array>
            <mxPoint as="offset" />
          </mxGeometry>
        </mxCell>
        <!-- … -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

`tests/test_skill.py` checks that every line of this template appears in the committed example, so
it cannot drift from the renderer's output.
