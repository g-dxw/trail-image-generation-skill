# 轨迹 SVG 规则

Use `scripts/route_to_svg.py` to turn the selected track into a stable layout artifact before prompt compilation.

## Outputs

- `<路线>-轨迹骨架.svg`: deterministic route skeleton and checkpoint anchors.
- `<路线>-轨迹布局.json`: normalized geometry, simplified point indices, track progress, and checkpoint anchors.
- `<路线>-轨迹提示片段.md`: compact SVG/path reference suitable for the execution prompt.
- `<路线>-轨迹预览.png`: deterministic raster preview generated from the layout JSON for image models that do not support SVG.

After the final checkpoint JSON is ready, run:

```bash
python3 scripts/route_to_svg.py route.kmz --output-dir route-work --checkpoints-json checkpoints.json \
  --start-label "已确认起点名称" --finish-label "已确认终点名称"
python3 scripts/render_route_preview.py route-work/route-轨迹布局.json --output route-work/route-轨迹预览.png
```

Use the PNG as the highest-priority image-generation geometry reference. Keep the SVG and JSON for preflight and post-generation verification; this Skill does not rely on deterministic SVG post-overlay to correct a generated route.

## Simplification

Use Douglas–Peucker simplification with a target point count rather than copying every recorded sample. Preserve:

- start and finish roles and confirmed names in the SVG, PNG preview, and layout JSON;
- route extrema;
- one far anchor for closed loops;
- confirmed checkpoint progress positions;
- segment boundaries when supplied as checkpoint-like forced progress values.

Recommended target counts:

- overview prompt reference: 30–80 points;
- complicated loops or repeated turns: 80–150 points;
- strict generation reference: use enough points to retain every visually important bend and all forced anchors.

If simplification removes a visually important bend, increase `--target-points` or add its progress to the checkpoint JSON.

## Prompt usage

Prefer this order:

1. Attach the SVG or a rasterized preview as the route geometry reference when the image tool accepts visual inputs.
2. Include the compact `path d` signature from the prompt fragment as supporting text.
3. Include a short natural-language description of route type, start/finish relation, direction, and major turns.

Do not assume that a generative model will execute SVG code like a browser. The SVG code improves structure guidance but does not guarantee pixel-accurate reproduction. Use the route PNG in the actual reference-image payload, retain the geometry lock verbatim, and reject route-drifted outputs during acceptance.

## Checkpoint anchoring

Provide an optional checkpoint JSON containing `track_progress` values from 0 to 1:

```json
{
  "checkpoints": [
    {"number": 1, "name": "起点", "track_progress": 0.0},
    {"number": 2, "name": "观景点", "track_progress": 0.24}
  ]
}
```

The same JSON may define colored route segments and unnumbered boundaries:

```json
{
  "checkpoints": [],
  "segments": [
    {"name": "上山", "start_progress": 0, "end_progress": 0.32, "color": "#e67e22"},
    {"name": "山脊线", "start_progress": 0.32, "end_progress": 0.59, "color": "#c62828"},
    {"name": "下山", "start_progress": 0.59, "end_progress": 1, "color": "#2878b5"}
  ],
  "boundaries": [
    {"name": "寨门", "track_progress": 0.32, "show_marker": false},
    {"name": "下山路口", "track_progress": 0.59}
  ]
}
```

Segment paths must be slices of the same normalized track. Do not redraw or offset them as separate approximate routes. A boundary may coincide with a numbered checkpoint; set `show_marker` to `false` to avoid overlapping symbols while retaining its label.

The script forces these positions into the simplified route and writes their normalized canvas anchors. Move display cards when crowded; do not move the anchors.
