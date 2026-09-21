---
name: knowledge-explainer-video
description: Turn a topic and supporting materials into a slow-paced, image-rich, evidence-backed knowledge explainer with optional simple cartoon characters, clearly licensed real footage, continuity transitions, two approval gates, human voiceover timing, Remotion rendering and QA. 把主题和资料拆解为慢节奏、图片丰富的知识讲解视频。Only use this skill when the user explicitly selects it; do not route ordinary tutorial slicing or source-led interview editing here.
metadata:
  version: "1.0.0"
  name_en: Knowledge Explainer Video
  name_zh: 知识讲解视频工作流
---

# 知识讲解视频总控

把主题和资料整理成观众能慢慢理解的完整讲解视频。默认横版 1920×1080、30fps、90–180 秒；人工录音是正式时间线的唯一声音基准。图片可以多生成，但成片只选择语义准确、风格一致的素材。

## 调用边界

- 仅在用户明确调用 `$knowledge-explainer-video` 或明确选择“知识讲解视频”时执行。
- 长教程切章节、产品录屏演示使用 `tutorial-video-slicing-workflow`；以受访者原声为主体的内容使用 `interview-video-editing`。
- 用户只要求策划、讲稿或分镜时，交付到对应阶段即停止，不自动生成图片或渲染。
- 未收到人工录音时只能交付静音预览，不能称为最终成片。

## 严格顺序

1. 完整读取 [workflow.md](references/workflow.md)，建立项目清单并分析资料。
2. 读取 [narrative-and-evidence.md](references/narrative-and-evidence.md)，选择叙事结构、建立证据表并写唯一讲稿。
3. 执行第一次确认：内容结构、讲稿、预计时长、风格方向、卡通人物、真实视频与画幅。
4. 读取 [visual-direction-and-assets.md](references/visual-direction-and-assets.md)，生成角色设定、三张代表帧和 8–12 秒连续转场样片。
5. 执行第二次确认：锁定人物、代表帧、素材比例和转场语言。
6. 批量生成图片与卡通贴图，获取并登记许可清晰的真实素材；等待用户提供人工录音。
7. 读取 [pacing-and-transitions.md](references/pacing-and-transitions.md)，按实际录音锁定句子、字幕、视觉节拍、场景和转场。
8. 用 `scripts/build.mjs` 从项目清单生成独立 Remotion 工程；正式渲染前先出低清预览与边界关键帧。
9. 读取 [qa-and-delivery.md](references/qa-and-delivery.md)，运行自动检查并完成人工视觉验收。

状态链：`initialized → evidence_ready → content_approved → visual_direction_approved → assets_ready → voice_locked → timeline_locked → preview_approved → rendered → qa_passed → delivered`。

## 两次确认是硬闸门

第一次确认必须包含：目标受众、叙事结构、完整讲稿、预计时长、视觉风格、是否加入卡通人物、人物作用、是否插入真实视频、真实视频来源策略、默认横版及可选派生画幅。

第二次确认必须包含：角色设定与 6–10 个姿势/表情计划、开场/核心/结尾代表帧、真实视频候选、素材占比，以及至少一段从上一场景真实组件自然变化到下一场景的转场样片。

确认前只更新同一份方案；禁止创建“最终版2”等并行事实源。

## 不可违反的成片标准

1. 讲解从问题和实际价值出发，不做提交记录或技术名词堆砌。
2. 大场景通常保持 8–15 秒；内部每 3–6 秒只推进一个视觉焦点。
3. 有意义的图片、插画、动态图形或真实视频覆盖至少 75% 成片；纯文字整屏不超过 15%。
4. 句间保留 0.3–0.6 秒，章节间保留 0.8–1.2 秒；关键结论揭示后保持 1.5–2.5 秒。
5. 人工旁白不加速、不拉伸；画面和字幕适配声音。
6. 默认使用组件连续转场：上一场景的卡片、图片、人物或节点移动、展开或变形为下一场景载体；只有明确断章才能使用 `section-reset`。
7. 转场通常 0.8–1.5 秒；文字必须先消退再替换再出现，禁止直接闪换。
8. 一个关系只使用一个方向明确的箭头；轴线、节点和卡片必须对齐、完整、对称。
9. 场景边界逐一检查前一帧、切换帧和后一帧，禁止下一场景提前出现、上一场景人物残留或组件重叠。
10. 用户素材优先；网络真实素材必须有清晰许可和来源记录。无法确认许可时改用原创插画或组件。

## 标准命令

从 [project-manifest.template.json](assets/project-manifest.template.json) 建立唯一项目清单，字段规则见 [project-manifest.md](references/project-manifest.md)。

```bash
python scripts/validate_project.py 项目目录/project-manifest.json
node scripts/build.mjs --validate 项目目录/project-manifest.json
node scripts/build.mjs 项目目录/project-manifest.json 项目目录/remotion
cd 项目目录/remotion && npm ci && npm run preview
```

无录音时只允许显式生成静音预览：

```bash
node scripts/build.mjs 项目目录/project-manifest.json 项目目录/remotion-preview --preview
```

## 完成标准

事实可追溯；两次确认已记录；角色和图片风格统一；真实素材许可完整；人工录音、字幕和画面使用同一时间线；画面丰富但不急促；转场有连续载体；边界无闪帧或残留；最终视频完整解码。自动校验失败或人工视觉检查未通过时不得宣称交付完成。
