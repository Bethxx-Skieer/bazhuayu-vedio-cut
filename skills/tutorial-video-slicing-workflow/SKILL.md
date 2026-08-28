---
name: tutorial-video-slicing-workflow
name_en: Tutorial & Business Demo Video Workflow
name_zh: 教程与企业业务演示视频工作流
description: Slice tutorials and screen recordings into sections and highlight clips; rebuild silent demos into effect-first social promos; turn real Agent/RPA/SaaS operation footage into narrated business demo videos. Builds a footage evidence library and one locked script, aligns sentence-level voiceover with unified subtitles, fills gaps with brand components, and renders 16:9 and 3:4 outputs from one timeline. Use when the user asks for tutorial slicing, product or Skill promo edits, enterprise case narration, burned-in subtitles, caption-driven voiceover, Xiaohongshu 3:4 videos, or batch delivery.
description_en: Slice tutorials and screen recordings into sections and highlight clips; rebuild silent demos into effect-first social promos; turn real Agent/RPA/SaaS operation footage into narrated business demo videos with locked scripts, sentence-level voiceover, unified subtitles, and 16:9 + 3:4 renders from one timeline.
description_zh: 从教程、屏幕录制或真实产品操作素材中识别板块、制作切片、社媒宣发片和企业业务演示视频。先建立素材证据库和唯一业务脚本，再逐句对齐配音字幕、连续展示任务输入—执行—分析—结果，用统一组件补齐缺失画面，从一套时间线渲染16:9横版与冰蓝品牌3:4成品。适用于教程剪辑、产品或 Skill 效果宣发、企业案例解说、统一字幕、字幕转配音、小红书3:4与批量产出。
argument-hint: Attach source video/zip and transcript, state the mode (slicing / promo / business demo) and the output folder
argument-hint-en: Attach source video/zip and transcript, state the mode (slicing / promo / business demo) and the output folder
argument-hint-zh: 附上视频素材（zip/mp4）与文字稿，说明模式（切片/宣发/业务演示）与输出目录
user-invocable: true
version: 2.0.0
---

# 教程与企业业务演示视频工作流（总控调度）

本文件只负责调度：先判断用户任务属于哪个场景，再**完整读取对应子 Skill 文档**后执行。禁止凭记忆或略读开工；多场景组合任务（如切片+字幕+配音+竖版）时，逐个读全对应的全部子文档。

## 场景路由表

| 用户诉求 | 必读子 Skill |
|---|---|
| 教程剪辑：切板块、提高光、出切片成品 | [references/slicing-workflow-steps.md](references/slicing-workflow-steps.md)（执行 Step 1–6）＋ [references/slicing-matrix-method.md](references/slicing-matrix-method.md)（切片选题） |
| 企业业务演示视频：Agent/RPA/SaaS/数字员工/自动化案例的真实操作素材＋业务解说 | [references/enterprise-business-demo-production.md](references/enterprise-business-demo-production.md)（含专属 `01_正式视频`–`07_工程` 交付结构） |
| 社媒宣发、效果前置：无字幕无配音的产品/Skill 演示素材 | [references/social-promo-effect-first.md](references/social-promo-effect-first.md) |
| 统一字幕、章节卡、字幕预览 | [references/subtitle-style.md](references/subtitle-style.md) |
| 给已有字幕按时间码生成对齐配音并合回 | [references/subtitle-voiceover.md](references/subtitle-voiceover.md) |
| 小红书 3:4 冰蓝品牌画布、竖版派生、封面 | [references/xhs-portrait-composition.md](references/xhs-portrait-composition.md) |
| 点击/输入/等待/阶段/结果等界面事件的音效与视觉增强 | [references/product-demo-enhancement.md](references/product-demo-enhancement.md) |

任何模式在整片渲染与交付前，都必须执行 [references/common-standards.md](references/common-standards.md) 中的锁定闸门、技术参数与质检清单。

## 全局硬闸门（三种叙事模式共用）

1. **先锁脚本**：唯一旁白脚本经用户确认前，不展开正式配音、字幕和画面制作；用户只要方案时停在方案交付。
2. **整句配音**：按完整自然句生成语音；显示字幕可按语义拆分，但不得反向切碎配音。中文默认使用黎潋（[assets/voiceover-profile-zh-CN.json](assets/voiceover-profile-zh-CN.json)），缺音色或换音色必须先获用户确认，禁止静默回退婷婷等默认值。
3. **真实素材优先**：关键任务连续展示「提出需求 → Agent 调用 → RPA 执行 → 数据返回 → Agent 分析 → 输出结果」；没有真实素材的必要业务信息用统一组件补齐，不得直接删除。
4. **统一代码渲染、单一时间源**：组件、真实视频、图片和章节卡进入同一条主时间线，先渲染无字幕无配音的画面母版，再合成配音和字幕。字幕内容和时间只允许一份 SRT/JSON：横版与 3:4 共用文案、时间码、配音和音效，各自排版渲染；禁止复制出第二套字幕，禁止把已烧录的横版字幕缩进竖版产品框。
5. **双重预览＋交付闸门**：整片渲染前，前 60 秒音画预览与跨章节关键帧两项必须同时通过；字幕烧录只允许 `scripts/burn_subtitles.py`，禁止临时重写渲染器；交付前 `scripts/validate_render_lock.py` 必须返回 `status: ok`，失败不得交付。

## 主流程总览

```text
接收素材与文字稿 → 解压/探测/截图 → 场景检测确认边界 → 判定叙事模式
→ 锁定唯一脚本 → 展开音画方案 → 生成整句配音与显示字幕 → 匹配真实素材
→ 统一组件补齐 → 渲染无字幕内容母版 → 合成16:9横版与3:4品牌成品
→ 质检交付 + 说明文档
```

## 资源索引

- `scripts/`：`burn_subtitles.py`（唯一字幕烧录器）、`subtitle_layout.py`（横版字幕布局）、`subtitle_voiceover.py`（时间轴配音，先 `--dry-run` 校验）、`validate_render_lock.py`（交付闸门）、`compose_product_demo_sfx_track.py`（cue sheet→音效轨）、`render_subtitle_adaptive_preview.py`、`render_product_demo_style_preview.py`、`build_product_demo_sfx_library.py`
- `assets/`：字幕样式 `subtitle-style-1920x1080.json`；中文声音 `voiceover-profile-zh-CN.json`；竖版画布 `xhs-portrait-octopus-blue-1080x1440.json`；增强三件套 `enhancement-cue-sheet.example.json` / `enhancement-event-map.json` / `enhancement-styles/product-demo-clean-1920x1080.json`；音效库 `sfx/product-demo-clean/manifest.json`；逐镜头取景 `framing-cues.example.json`；各预览图
- 环境：Python 3.12+ 与 `imageio-ffmpeg`（自带 ffmpeg，免装系统 ffmpeg），安装步骤见 slicing-workflow-steps.md「环境准备」

## 子 Skill 文档地图

| 文件 | 职责 |
|---|---|
| references/slicing-workflow-steps.md | 教程切片执行流程：环境准备＋Step 1–6 脚本级操作 |
| references/slicing-matrix-method.md | 切片矩阵方法论、爆款判断、平台策略、效率基准与扩展用法 |
| references/common-standards.md | 锁定闸门细则与三条子流程、技术参数、目录结构、FAQ、清单、变量表 |
| references/enterprise-business-demo-production.md | 企业业务演示模式总控 SOP 与交付结构 |
| references/social-promo-effect-first.md | 效果前置宣发模式 SOP |
| references/subtitle-style.md ／ subtitle-voiceover.md | 字幕视觉规范 ／ 字幕时间轴配音规范 |
| references/xhs-portrait-composition.md | 小红书 3:4 品牌画布动态合成 |
| references/product-demo-enhancement.md | 产品演示音效与视觉增强 |
