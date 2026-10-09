---
name: knowledge-explainer-video
description: Turn a topic and supporting materials into a narration-led knowledge animation with clear character-object interactions, image-rich scenes, continuous transitions, optional licensed footage, captions, music and whole-film QA. 把主题和资料制作成慢节奏、交互清晰的知识讲解动画。Only use when explicitly selected; ordinary tutorial slicing and source-led interviews use their own skills.
metadata:
  version: "1.4.0"
  name_en: Knowledge Explainer Video
  name_zh: 知识讲解视频工作流
---

# 知识讲解视频总控

把主题和资料整理成观众能慢慢理解的完整讲解动画。默认横版 1920×1080、30fps；时长服从内容和人工录音，不把 90–180 秒当上限。图片可以多生成候选，成片只选择语义准确、风格一致的素材。人工录音是正式时间线的基准。

## 调用边界

- 仅在用户明确调用 `$knowledge-explainer-video` 或明确选择“知识讲解视频”时执行。
- 单纯把已有长教程或产品录屏切成章节，使用 `tutorial-video-slicing-workflow`；以受访者原声为主体的内容使用 `interview-video-editing`。用户明确选择本技能制作“旁白＋解释动画＋真实操作证据”的产品能力片时，沿用本工作流。
- 用户只要求策划、讲稿或分镜时，交付到对应阶段即停止，不自动生成图片或渲染。
- 未收到人工录音时只能交付静音预览，不能称为最终成片。

## 严格顺序

1. 完整读取 [workflow.md](references/workflow.md)，建立项目清单并分析资料。
2. 读取 [narrative-and-evidence.md](references/narrative-and-evidence.md)，选择叙事结构、建立证据表并写唯一讲稿。
3. 执行第一次确认：内容结构、讲稿、预计时长、风格方向、卡通人物、真实视频与画幅。
4. 读取 [visual-direction-and-assets.md](references/visual-direction-and-assets.md)，生成角色设定、三张代表帧和 8–12 秒连续转场样片。
5. 执行第二次确认：锁定人物、代表帧、素材比例和转场语言。
6. 按已确认方向制作所需图片、组件及启用时的卡通贴图，获取并登记许可清晰的真实素材和配乐；等待用户提供人工录音。
7. 读取 [pacing-and-transitions.md](references/pacing-and-transitions.md) 与 [motion-language.md](references/motion-language.md)，先写观看过程及动作谱，再按实际录音锁定自然句、重点词、动作阶段、字幕、场景和转场。十二原则按表达需要选用，不是逐项加特效。
8. 用 `scripts/build.mjs` 从项目清单生成独立 Remotion 工程。模板只提供时间线和基础组件；知识关系复杂时，在工程中编写专门场景动画。正式渲染前先出低清预览、边界帧和复杂动作的起点／中间／终点帧。
9. 读取 [qa-and-delivery.md](references/qa-and-delivery.md)，运行自动检查并完成人工视觉验收。

状态链：`initialized → evidence_ready → content_approved → visual_direction_approved → assets_ready → voice_locked → timeline_locked → preview_approved → rendered → qa_passed → delivered`。

## 两次确认是硬闸门

第一次确认必须包含：目标受众、叙事结构、完整讲稿、预计时长、视觉风格、是否加入卡通人物、人物作用、是否插入真实视频及来源策略、字幕开关、默认横版及可选派生画幅。

第二次确认必须包含：启用人物时的角色设定与 6–10 个姿势/表情计划、开场/核心/结尾代表帧、真实视频候选、素材占比、字幕安全区，以及至少一段从上一场景真实组件自然变化到下一场景的转场样片。不启用人物时由问题、数据、界面等物件承担动作。已确认的选择不重复索要批准。

确认前只更新同一份方案；禁止创建“最终版2”等并行事实源。

## 不可违反的成片标准

1. 从观众熟悉的具体问题出发。一段分镜只推进一个主要认识，并写明知识点、人物与物件、操作、可见结果和理解停顿；术语对应可观察的变化。
2. 启用人物时，人物是行动组件，与知识物件发生提问、操作、检查、选择或协作；不得固定站在展示卡旁。图片、人物贴图默认不套白框，只有真实容器、窗口或面板需要边界。
3. 大场景通常 8–15 秒，但以讲解为准；局部微动可以更短，不能机械按秒切屏。关键动作按出现、操作、反馈、停留、交接设计，让结果有阅读时间。
4. 有意义的图片、插画、动态图形或真实视频覆盖至少 75% 成片；纯文字整屏不超过 15%。丰富度来自构图、景别、物件状态和交互，而非装饰背景或卡片堆叠。
5. 人工旁白默认保留自然速度；用户明确授权调整时按 [audio-and-export.md](references/audio-and-export.md) 处理，并以处理后的唯一音轨重新对齐。实际句子和重点词触发画面，不为凑片长强行加速。字幕默认开启，按真实录音自然断句；用户可在第一次确认时关闭。
6. 默认让上一画面已有物件承接下一画面；布局差异大时可用有方向的遮罩揭示。文字先消退、载体变化、新文字再入场。转场通常约 0.8–1.5 秒，仅作参考，以阅读负担和旁白停顿调整。
7. 箭头要有唯一明确的来源和目标；轴线延伸至最后节点。逐一检查转场边界与复杂动作中间帧，禁止穿模、重复锚点、提前入场、残留、闪屏和文字互压。
8. 用户素材优先；网络真实素材和配乐必须有来源与许可记录。音乐应可感知且不压住旁白；试听实际成片后调整音量和必要的人声避让。

## 持续制作与反馈路由

- 修改既有视频先读 [feedback-and-regressions.md](references/feedback-and-regressions.md)，核对最新成片、工程、录音及字幕版本；保留已确认的选择与回退入口，不从旧 README 猜当前版本。
- 用户反馈“像 PPT”“不够华丽”“说明浅薄”，或制作需要宣传传播的产品片时，读 [visual-revision-logic.md](references/visual-revision-logic.md)。先从语义变化、因果、注意力、连续性和证据诊断画面，再选组件与特效；不要把优化简化成换皮肤。
- 修改字幕字体、大小、背景或处理手机端可读性时，读 [captions-and-readability.md](references/captions-and-readability.md)，检查实际编码结果和句间边界；案例参数是可选起点，不是所有视频的统一样式。
- 用户提供特殊视频或要求吸收参考片时，读 [footage-integration.md](references/footage-integration.md)，按内容和时间码拆解，明确仅借鉴效果／排除视频模型片段等边界。
- 新动画在设计图之前记录“观众怎样看”的过程，复杂动作填写 [motion-score.template.json](assets/motion-score.template.json)。用 `python scripts/validate_motion_score.py motion-score.json` 检查旁车计划；自动结果不能代替动态审片。
- 沿用当前工程与已批准声音，不擅自换框架、重录、克隆音色、加情绪指令或发布仓库。只改局部也要复查前后衔接；未经全片音画检查，不把预览称为已交付。
- 组件搬运、镜头推近、多人物选择或容器出入，读 [interaction-contracts.md](references/interaction-contracts.md)，先落实坐标、接触点和图层所有权，再加特效。不能用静态包围盒通过代替运动中无穿模。
- 换音乐、混音或导出 MP4，读 [audio-and-export.md](references/audio-and-export.md)。只导出时沿用当前构图、旁白和字幕，不重走创作流程；明确区分“文件已导出”和“全片审片通过”。
- 用 [revision-review.template.json](assets/revision-review.template.json) 记录本轮基线、改动范围、实际检查证据和未完成项；该文件是旁车，不要求迁移旧项目清单。

## 标准命令与入口

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

事实可追溯；两次确认已记录；角色和图片风格统一；真实素材与配乐许可完整；人工录音、字幕和画面使用同一时间线；人物交互清晰；转场有连续载体；边界与复杂动作无穿模、闪帧或残留；完整观看成片并解码通过。自动校验失败或人工视觉检查未通过时不得宣称交付完成。
