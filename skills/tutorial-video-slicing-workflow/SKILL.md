---
name: tutorial-video-slicing-workflow
name_en: Tutorial & Business Demo Video Workflow
name_zh: 教程与企业业务演示视频工作流
description: Build tutorial slices, effect-first social promos, and narrated enterprise business demo videos from articles, screen recordings, and real operation footage. Keeps one evidence library, one locked script and one content timeline; derives voiceover, subtitles, shots and 16:9/3:4 variants from the same timeline with gated previews, automated QA and incremental re-rendering. Use for video slicing, promo editing, business case narration, caption-driven voiceover, landscape/portrait adaptation, or replication QC.
description_en: Build tutorial slices, effect-first social promos, and narrated enterprise business demo videos with one evidence library, one locked script, one content timeline, gated previews, automated QA and incremental re-rendering.
description_zh: 从教程、屏幕录制、宣传文章、产品资料和真实业务操作素材中制作教程切片、社媒宣发片与企业业务演示视频。先建立素材证据库和唯一脚本，再生成完全匹配的配音字幕时间线、逐句匹配真实素材或动画，并从同一内容时间线派生16:9横版、3:4小红书版和其他画幅；也适用于已有字幕配音、产品演示增强、增量修改和成片质检。
argument-hint: Attach articles/footage/reports, state the mode (slicing / promo / business demo) and target formats
argument-hint-en: Attach articles/footage/reports, state the mode (slicing / promo / business demo) and target formats
argument-hint-zh: 附上文章/录屏/报告与目标，说明模式（教程切片/社媒宣发/业务演示）与交付画幅
user-invocable: true
version: 3.0.0
---

# 教程、社媒宣发与企业业务演示视频总控（调度）

唯一总控：管理阶段顺序、唯一内容源、下游能力调用与质量闸门。进入任何阶段前先完整读取对应子文档；禁止在主流程之外另建脚本、字幕、配音或横竖版时间线。本文件 `name`+`description` 与 `agents/openai.yaml` 供 WorkBuddy 加载，双语元数据与 `.skill-metadata.yaml` 供千问办公加载，两端共享同一份内容与闸门。

## 核心生产链（严格按序执行）

```text
接收文章、录屏、报告和品牌资料 → 建立素材证据库 → 撰写并锁定唯一旁白脚本
→ 拆分完整自然句并估算目标时长 → 试听锁定音色、语速、发音和停顿 → 生成实际配音
→ 按实际配音时长锁定显示字幕时间线 → 逐句匹配真实素材或统一动画
→ 同一内容时间线派生横版与竖版 → 双重预览 → 自动质检 → 交付
```

目标时长只用于规划；最终字幕和画面时间必须来自实际配音时长，不得用字数估算值替代。

## 不可违反的约束

1. 只保留一份项目清单、一份最终旁白和一份内容时间线。
2. 脚本确认前不生成正式配音、字幕和全片画面；用户只要求方案时停在方案交付。
3. 按完整自然句配音；字幕可分屏但拼接文字与实际朗读一致；断句和 cue 句末不留标点，停顿单独管理，不靠字幕标点控制。
4. 特殊词先试听再锁定；显示文本、朗读原文、TTS 别名和停顿策略分别保存。
5. 真实素材优先，关键任务至少形成「输入或调用 → 稳定结果」；素材缺口用统一组件补齐，不得直接删除业务信息。
6. 默认排除加载骨架、无变化等待、错误尝试、不完整结果和无关滚动。
7. 横竖版共用旁白、字幕、镜头 ID、素材入出点和播放速度；禁止复制第二套镜头数组。
8. 全片渲染前必须同时通过前 60 秒音画预览与跨章节关键帧检查。
9. 修改脚本、配音、字幕或镜头后，只重做受影响节点及其下游产物；自动校验失败时不得交付或宣称完成。

## 任务模式（先选一个主模式，混合任务以最终交付目标为准）

| 模式 | 判断标准 | 必读子 Skill |
|---|---|---|
| 教程切片 | 保留长教程结构、切章节、提取高光 | [references/mode-tutorial-slicing.md](references/mode-tutorial-slicing.md) |
| 企业业务演示 | 真实操作素材＋业务解说呈现任务链与结果 | [references/enterprise-business-demo-production.md](references/enterprise-business-demo-production.md) |
| 社媒效果宣发 | 先展示用户结果和证据，再讲安装使用 | [references/social-promo-effect-first.md](references/social-promo-effect-first.md) |

## 阶段路由（进入阶段时完整读取对应子文档，不要一次加载全部）

| 阶段 | 子 Skill | 需要时同时读取 |
|---|---|---|
| 1 素材理解与证据库 | [references/01-intake-and-evidence.md](references/01-intake-and-evidence.md) | — |
| 2 脚本策划与时长规划 | [references/02-script-writing.md](references/02-script-writing.md) | 脚本未确认时停止下游生产 |
| 3 配音、字幕与正式时间线 | [references/03-voice-caption-timeline.md](references/03-voice-caption-timeline.md) | 已有字幕转配音：subtitle-voiceover.md ＋ `scripts/subtitle_voiceover.py`；字幕视觉：subtitle-style.md ＋ `scripts/subtitle_layout.py` / `scripts/burn_subtitles.py` |
| 4 画面匹配与动画补齐 | [references/04-visual-matching.md](references/04-visual-matching.md) | 界面事件音效与视觉增强：product-demo-enhancement.md |
| 5 横版与竖版适配 | [references/05-landscape-portrait-adaptation.md](references/05-landscape-portrait-adaptation.md) | 冰蓝 3:4 画布：xhs-portrait-composition.md ＋ [assets/xhs-portrait-octopus-blue-1080x1440.json](assets/xhs-portrait-octopus-blue-1080x1440.json) |
| 6 预览、质检与交付 | [references/06-preview-qa-delivery.md](references/06-preview-qa-delivery.md) | 含七目录交付细则与逐项通过条件 |

## 项目状态与闸门

状态链：`initialized → evidence_ready → script_locked → voice_style_locked → voice_generated → subtitle_timeline_locked → visual_timeline_locked → preview_approved → variants_rendered → qa_passed → delivered`。

在项目根目录复制 [assets/project-manifest.template.json](assets/project-manifest.template.json) 为 `project-manifest.json` 持续更新；每次推进状态前运行 `python scripts/validate_project_manifest.py project-manifest.json`，不得手工跳过失败项。状态→必备产物→进阶条件详表与字段规则见 [references/07-project-lifecycle.md](references/07-project-lifecycle.md) 与 [references/project-manifest.md](references/project-manifest.md)。

## 工具与下游能力

Skill 是路由和专业规范，不是底层程序：常规生产只运行版本受控、已通过测试的脚本、TTS 适配器和 Remotion 工程；只有新增能力、修改实现或脚本未覆盖的异常，才读取对应独立 Skill（`ffmpeg` / `remotion` / `generate-voiceover` / `moviepy`）。四层能力模型、阶段边界、FFmpeg 查找顺序、跨系统复现等级与启动检查见 [references/runtime-and-tool-routing.md](references/runtime-and-tool-routing.md)。运行宿主为 WorkBuddy 或千问办公均可：按上述查找顺序复用共享运行时，不因切换对话重复安装依赖。

## 数据与样式单一来源

旁白、字幕、音频和镜头用稳定 ID 关联；平台版本只存布局覆盖项，不存第二份旁白、字幕或镜头表；字体、颜色、字号、标签、产品框和字幕卡一律读取资产配置，不逐镜头写值；项目特殊要求写进项目清单或 `design-overrides`。VOC/品牌读法、项目固定时间码和具体审美偏好属于项目配置，不写回通用 Skill。

## 完成标准（硬门槛摘要）

业务事实与证据一致；旁白独立可懂、特殊词读法已确认；字幕与朗读逐字一致、无溢出遮挡；每句旁白有可理解画面、关键任务闭环；横竖版同源、组件与字幕样式统一；前 60 秒预览与跨章节关键帧通过；`validate_project_manifest.py` 与 `validate_render_lock.py` 均返回 `status: ok`；成片完整解码、工程可增量重渲染。交付目录组织（`delivery/01_正式视频`–`07_工程`，七目录只放当前最终版）与逐项通过条件见 [references/06-preview-qa-delivery.md](references/06-preview-qa-delivery.md)。
