# 生图提示词规则

Only read and apply this file after the user has replied `生图画面规格确认无误`. Generate prompts first. After delivering the prompts, ask the user to choose the current-session image tool, a configured relay, or prompt-only mode; then ask whether to generate a complete image or a background for deterministic overlay. The default requested model is `gpt-image-2`. Do not call or upload to an external provider before explicit confirmation.

## 执行能力与点位优先

- 先检测当前 Agent 是否具备可调用的生图模型/工具，不根据 Agent 名称猜测能力。
- 没有生图能力，或用户明确要使用其他生图模型时，只输出独立可用的提示词、参考图清单、构图要求和负面约束，不声称已生成图片。
- 点位优先模式：先生成小尺寸打卡点图供用户判断；用户确认后跳过总览图，直接生成路线详图。

## 强制几何层

- 每条路线图提示词都必须列出路线 SVG、PNG 预览和布局 JSON。向生图模型提交视觉参考时优先使用 PNG，不假设模型能解析 SVG。
- SVG 用于编辑和最终确定性叠加，PNG 用于视觉参考，布局 JSON 用于校验点位锚点和路线拓扑。
- 标注点必须沿 SVG 原位置、原顺序、原编号显示，禁止遗漏、重排、镜像、旋转或移到路线外。
- 若 SVG 标注点未生成，流程阻断，先补齐参考资产。
- 默认不要求或自动生成示意等高线。只有用户提供可靠地形数据并明确要求时，才把地形图层加入提示词。

## 1. Build prompts from the current route

Never reuse screen directions, point counts, segment counts, aspect ratios, or styles from a previous route. Derive them from the approved review document and current image task.

For every image, specify:

- image type and intended use;
- image scope: full route, one segment, one checkpoint, or information card;
- target aspect ratio and shared visual style;
- route type, start and finish relationship, major-anchor sequence, and travel direction;
- included global checkpoint numbers and names;
- real-photo frames versus AI-derived landmark scenes;
- exact text, data, safety, supply, and seasonal information requested for this image;
- negative constraints and an acceptance checklist.
- mandatory geometry assets: the route SVG, PNG preview, layout JSON, and annotation points.

When route intensity is shown, use the confirmed `route_intensity.score` and `route_intensity.level`. Do not convert cave, wet surface, cliff exposure, construction status, or ladder use into the route-intensity value; keep them as separate safety text.

## 2. Route fidelity modes

- **氛围自由**: preserve only route type and broad direction.
- **结构相似**: preserve overall silhouette, major turns, start/finish relationship, travel direction, and checkpoint order; allow local simplification. Use as the default for illustrated travel maps.
- **精确轨迹**: use a fixed route layer or deterministic composition instead of asking a generative model to redraw the route.

Fit the route into the requested canvas without non-uniform stretching. Add padding when source and target aspect ratios differ. Do not mirror or rotate unless approved.

## 3. Describe route structure generically

Convert track geometry into a small ordered set of major screen-space anchors. Describe the current route using those anchors, for example:

```text
start at <relative position>;
continue toward <direction> through anchor A;
turn toward <direction> through anchor B;
reach the finish at <relative position>;
```

For loops, state how the final section reconnects to the start. For out-and-back routes, identify the overlapping return. For point-to-point routes, keep start and finish distinct.

Bind each checkpoint to both track progress and the anchor interval containing it. Never rely only on a textual `1→2→...→N` list.

## 4. Preserve numbering across multiple images

Use one global checkpoint list. Overview and detail images must keep the same numbers. A detail image containing checkpoints 4, 5, and 6 must display 4, 5, and 6.

If a detail image includes a route inset:

- show the full route in a muted color;
- highlight the current segment;
- indicate its position in the full journey.

## 5. Handle reference materials by role

Label every input image as one of:

- route geometry reference;
- real photo to insert;
- AI scene reference;
- style reference.

For route screenshots, use only the polyline silhouette, major turns, travel direction, and layout. Ignore satellite backgrounds, map labels, pins, phone UI, and controls.

For a generated route skeleton, prefer attaching the SVG or a rasterized preview as the geometry reference. Also include the compact normalized path signature from the generated prompt fragment. Do not paste hundreds of original track points into the prompt.

### Real photo mode

When the user wants the existing photo itself:

- reserve a frame in the generated base image;
- keep the original photo out of the generative redraw path;
- create a deterministic composition instruction with crop focus, frame shape, size, position, and privacy treatment;
- do not claim the model will preserve original photo pixels merely because it received a reference image.

### AI-derived scene mode

Extract only confirmed features:

- primary scene;
- distinctive objects;
- environment and colors;
- foreground, middle-ground, and background relationships;
- must-preserve features;
- allowed simplifications;
- avoid items.

Do not reproduce identifiable people unless the user explicitly requests and authorizes it.

## 6. Keep prompt priorities clear

Use this priority order unless the user changes it:

1. image scope and route structure;
2. checkpoint order and placement;
3. checkpoint names and function icons;
4. landmark scenes or real-photo frames;
5. typography, information cards, decoration, and atmosphere.

When content conflicts with route readability, shrink or move secondary illustrations instead of changing route structure.

## 7. Recommended prompt structure

```text
use case and asset type |
image scope and layout |
shared style |
reference-image roles |
route fidelity and geometry |
segment display |
global checkpoints and topology |
checkpoint scenes and real-photo frames |
text and route data |
safety, supply, and seasonal information |
background and decoration |
visual constraints |
negative constraints
```

## 8. Negative constraints

Include only relevant constraints, such as:

`wrong route type, route shape unrelated to reference, mirrored route, unauthorized rotation, non-uniformly stretched route, wrong checkpoint order, reversed checkpoint numbering, checkpoint renumbered in detail map, checkpoints rearranged for visual balance, disconnected markers, marker on wrong segment, route hidden behind illustrations, oversized landmark cards, real photo redrawn by AI, satellite map UI, photo pins, phone controls, garbled Chinese characters, cropped route`

## 9. Multi-image execution

Create one prompt per image task plus a shared execution plan. Keep shared style, global numbers, segment colors, names, and landmark invariants consistent.

For overview-first cadence, generate and review the overview before compiling targeted revisions for detail images. For generate-all cadence, execute each image as a separate task; do not use multiple variants of one prompt as a substitute for distinct image prompts.

## 10. Capability and authorization

- If the user selected prompt-only mode, stop after delivering prompts.
- If generation is authorized, check whether an image-generation tool is actually available in the current session.
- If available, generate or edit using the current tool's supported path.
- If unavailable, provide prompts and composition instructions; never claim that an image was generated.
- Never silently switch to an external credentialed API or CLI fallback.
# 多日徒步补充规则

多日路线的每条独立提示词必须包含：`第几天`、`当天起点`、`当天终点/跨夜点`、`当天突出颜色`、`全局点位范围` 和 `其余路线的 inset 表现`。跨夜点必须在相邻两天重复出现，但编号和名称保持不变。
