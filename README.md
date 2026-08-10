# 轨迹生图 Skill

将 GPX、KML 或 KMZ 徒步/旅行轨迹整理成可核对的路线资料、全局打卡点、地标简化稿、确定性几何资产和独立生图提示词。仓库版是唯一源头；`SKILL.md` 定义 Agent 必须执行的门禁，本 README 面向安装、开发和人工操作。

## 核心原则

- 先核对事实、点位和照片，再生成任何图片。
- 原始照片每次只向地标预绘执行器上传一张，不能先拼原图再让模型整板重绘。
- 地标预绘与最终路线图使用两个独立执行角色：`landmark_prepaint` 和 `route_final`，分别选择、分别授权。
- 模型、尺寸、质量、价格或参考图容量没有证据时必须写 `unknown`，不能根据模型名猜测。
- 地标原始输出优先使用 Provider 已确认的较小方形尺寸和 low/fast/draft 档；实际像素如实记录。必要时另行生成默认 512×512 的拼板标准稿，但不能把标准稿冒充模型原始输出。
- 最终路线图最多上传两张视觉参考：第一张 `route_geometry` 轨迹 PNG，第二张可选 `landmark_reference_board`。
- SVG 和布局 JSON 只用于校验，原始照片和单张地标稿只作为事实来源，均不得进入最终路线图上传列表。
- 地标与轨迹默认采用干净无连线构图，通过相同编号、名称和邻近布局对应；只有用户明确要求时才启用引导连线。
- 地域背景只有在用户确认后才加入，并作为低对比、空气透视的 P1 远景避让路线、起终点、编号、文字和地标。

## 安装与验证

建议使用独立虚拟环境，避免系统 Python 缺少 Pillow：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -c "import PIL; print(PIL.__version__)"
```

运行测试和 Skill 结构校验：

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

如果 Pillow 不存在，参考板和图片尺寸校验脚本会明确停止，不生成替代图片。

## 强制工作流

所有阶段写入同一份 `<路线名称>-路线核对单.md`：

1. 写入基础信息，等待 `基础信息确认无误`。
2. 写入全局打卡点和标志性主照片，等待 `打卡点和标志性图片确认无误`。
3. 有真实照片时，发现当前图像工具能力，填写地标简化规格，等待 `地标简化规格确认无误`。
4. 分别展示 Provider、模型或未知状态、尺寸/质量、上传路径和隐私处理；每次只上传一张原图生成地标小稿。
5. 生成编号审核板，等待 `地标简化稿确认无误`。
6. 使用已确认点位生成编号 SVG、PNG 路线预览和布局 JSON。
7. 把画面风格、数量、逐图文字、轨迹精度、参考板和完整图片计划写回核对单。
8. 完成路线文案调研，等待 `路线文案与注意事项确认无误`。
9. 校验并展示阶段四内容，等待 `生图画面规格确认无误`。
10. 逐张生成并完整展示最终提示词，等待 `生图提示词确认无误`。
11. 重新发现并选择 `route_final` 执行器，展示最终实际上传清单并单独获得授权。
12. 构建并校验最终 manifest 后才允许调用生图工具。

没有真实照片、没有参考图工具、选择纯文字地标或要求保留原图像素时，可以按核对模板记录明确的跳过状态。

## 路线几何资产

先检查轨迹和候选点：

```bash
python3 scripts/inspect_kmz.py route.kmz --output-dir route-work
python3 scripts/detect_checkpoint_candidates.py route.kmz --output route-work/checkpoint-candidates.json
python3 scripts/route_intensity.py route.kmz
```

候选点经过用户确认后，整理为 `route-work/checkpoints-confirmed.json`，再生成带全局编号的几何资产：

```bash
python3 scripts/route_to_svg.py route.kmz \
  --output-dir route-work \
  --checkpoints-json route-work/checkpoints-confirmed.json \
  --width 900 \
  --height 1200

python3 scripts/render_route_preview.py \
  route-work/route-轨迹布局.json \
  --output route-work/route-轨迹预览.png
```

没有 `--checkpoints-json` 的 SVG 只能用于早期轨迹观察，不能满足最终编号点位门禁。

## 运行时图像能力发现

能力发现只读取当前 Agent 工具 schema 或已审查 Provider 文档，不发起收费请求，也不上传照片。下面示例表示当前工具确认支持一张图片编辑参考，但没有暴露模型、尺寸、质量和价格：

```bash
python3 scripts/build_image_capability_report.py \
  --executor builtin \
  --executor-type current_session \
  --model tool-managed/unknown \
  --source runtime_tool_schema \
  --can-generate true \
  --can-use-reference-image true \
  --can-edit-image true \
  --selectable-model false \
  --selectable-size false \
  --selectable-quality false \
  --max-reference-images 1 \
  --cost-class unknown \
  --quality-class unknown \
  --evidence "tool schema confirms one referenced image edit; other controls are hidden" \
  --output route-work/builtin-prepaint-capabilities.json
```

不要为了让校验通过而填写未经证实的容量。最终两图模式只有在能力报告明确记录 `max_reference_images >= 2` 时才能使用。

## Provider配置

复制示例到私有路径：

```bash
mkdir -p ~/.config/trail-image-generation
cp assets/provider-config.example.json ~/.config/trail-image-generation/providers.json
```

配置只保存环境变量名，不保存密钥值。内置当前会话 Provider 默认全部为 `unknown`，必须结合本轮能力报告选择：

```bash
python3 scripts/provider_config.py validate ~/.config/trail-image-generation/providers.json

python3 scripts/provider_config.py select ~/.config/trail-image-generation/providers.json \
  --purpose landmark_prepaint \
  --provider builtin \
  --capability-report route-work/builtin-prepaint-capabilities.json
```

配置文件只描述和选择 Provider，不等于仓库已经实现网络请求。当前会话工具由 Agent 直接调用；中转站必须使用当前环境已有的可调用工具或另行审查的 adapter。不得自行猜测 HTTP 请求格式。

## 单张地标预绘

每个地标创建一份包含 `[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]` 的独立提示词。能力明确的便宜 Provider 应请求其较小方形尺寸和低质量档；工具不暴露参数时使用 `provider-default`。

用户确认本张原图上传后，先构建预绘清单：

```bash
python3 scripts/build_landmark_generation_manifest.py \
  --task-id landmark-06 \
  --checkpoint-number 6 \
  --checkpoint-name '5峰·南天门' \
  --source-photo route-work/photos/09_5峰_南天门.jpg \
  --prompt-file route-work/landmark-06-prompt.md \
  --provider builtin \
  --model tool-managed/unknown \
  --selection-method runtime_tool_schema \
  --requested-size provider-default \
  --requested-quality provider-default \
  --provider-cost-class unknown \
  --provider-quality-class unknown \
  --capability-report route-work/builtin-prepaint-capabilities.json \
  --provider-max-reference-images 1 \
  --style '已确认画风骨架' \
  --must-preserve '三开间石牌坊' \
  --must-preserve '龙柱石雕' \
  --must-preserve '南天门匾额区域' \
  --privacy-treatment '删除可识别人脸和无关人物' \
  --output-image route-work/landmarks/06-raw.png \
  --provider-authorized \
  --output route-work/landmarks/06-manifest.json
```

模型返回后，如果原始稿不是适合拼板的较小方图，生成独立标准稿：

```bash
python3 scripts/normalize_landmark_draft.py \
  route-work/landmarks/06-raw.png \
  --output route-work/landmarks/06-board-512.png \
  --size 512
```

然后使用同一命令重建 manifest，并增加：

```text
--normalized-output-image route-work/landmarks/06-board-512.png
--board-asset-size 512
```

最后校验实际图片、哈希、尺寸和能力报告：

```bash
python3 scripts/validate_landmark_generation_manifest.py \
  route-work/landmarks/06-manifest.json \
  --require-output
```

原始输出可以不是512×512；manifest 会分别记录模型原始稿和拼板标准稿。

## 地标审核板与最终参考板

最终参考板 spec 的每项必须引用已经验证的地标 manifest：

```json
{
  "items": [
    {
      "checkpoint_number": 6,
      "checkpoint_name": "5峰·南天门",
      "path": "/absolute/path/route-work/landmarks/06-board-512.png",
      "generation_manifest": "/absolute/path/route-work/landmarks/06-manifest.json",
      "focus_x": 0.5,
      "focus_y": 0.5,
      "approved": true
    }
  ]
}
```

审核板可以超过12张并自动拆分；单张最终参考板最多12格：

```bash
python3 scripts/build_landmark_reference_board.py landmark-board-spec.json \
  --mode review \
  --output route-work/landmark-review-board.png \
  --sidecar route-work/landmark-review-board.json

python3 scripts/build_landmark_reference_board.py landmark-board-spec.json \
  --mode final \
  --output route-work/route-图01-地标参考板.png \
  --sidecar route-work/route-图01-地标参考板.json
```

修改任一单张地标稿后，原审核确认和相关参考板全部失效。

## 阶段四核对单校验

核对单必须使用准确文件名 `<路线名称>-路线核对单.md`。有AI地标预绘时，必须记录：

- `地标简化规格状态: confirmed`
- `地标简化稿状态: confirmed`
- 预绘能力报告绝对路径
- 两个确认短语

没有地标预绘时使用模板列出的明确跳过状态。

```bash
python3 scripts/validate_stage4_review.py route-work/路线名称-路线核对单.md
```

## 最终路线图Manifest

重新为 `route_final` 执行器生成能力报告。以下两图示例要求报告明确支持至少两张参考图：

```bash
python3 scripts/build_generation_manifest.py \
  --task-id route-overview \
  --prompt-file route-work/route-overview-prompt.md \
  --route-png route-work/route-轨迹预览.png \
  --route-svg route-work/route-轨迹骨架.svg \
  --layout-json route-work/route-轨迹布局.json \
  --landmark-board route-work/route-图01-地标参考板.png \
  --landmark-board-sidecar route-work/route-图01-地标参考板.json \
  --provider premium-final \
  --model configured-final-model \
  --selection-method configured \
  --requested-quality high \
  --provider-cost-class premium \
  --provider-quality-class final \
  --capability-report route-work/premium-final-capabilities.json \
  --provider-max-reference-images 2 \
  --output route-work/route-overview-manifest.json

python3 scripts/validate_generation_manifest.py route-work/route-overview-manifest.json
```

Provider 只确认支持一张图时，不能静默省略参考板。必须明确选择另一 Provider，或在用户批准后使用 `--allow-route-only-fallback`，只上传轨迹 PNG 并记录被省略的参考板。

## 目录

```text
SKILL.md      Agent 强制流程与门禁
references/   核对模板、Provider规则、几何合同和提示词规则
scripts/      轨迹、能力报告、地标、参考板和manifest工具
tests/        单元测试
examples/     公开案例、效果图和可核对几何资产
```

## 案例与限制

- [武功山单日反穿：高山草甸线](examples/wugongshan.md)
- [五台山顺朝：两天一夜大五朝台](examples/wutaishan.md)
- [南川下乐村：照片预筛选与路线强度](examples/nanchuan-xiale.md)
- [重庆南山十二峰：无连线构图与点位完整性](examples/nanshan-twelve-peaks.md)

![五台山顺朝 AI 总览效果图](examples/assets/wutaishan/ai-overview.png)

### 南山十二峰案例结论

南山十二峰案例在相同轨迹、12 个点位、地标、文字和重庆南山远眺渝中区背景下，只对比地标连接方式。用户确认无连线版本明显更好：1—12 号轨迹锚点完整且无重复，画面也更干净；有连线版本则出现额外重复的 12 号锚点和较强视觉干扰。

因此 Skill 默认使用无连线构图。地标通过相同编号、名称和邻近布局对应；连线仅在用户明确要求且能够保证一一对应时启用。

![南山十二峰无连线路线总览](examples/assets/nanshan-twelve-peaks/ai-overview-no-connectors.png)

旧案例不代表当前严格门禁。提示词约束可以降低路线漂移，但不能保证生成模型实现像素级轨迹一致；模型返回成功也不等于验收通过。

## License

MIT License，见 [LICENSE](LICENSE)。
