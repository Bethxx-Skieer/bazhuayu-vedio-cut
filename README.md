# bazhuayu-vedio-cut

团队视频剪辑工作仓库：沉淀「教程 / 社媒宣发 / 企业业务演示 / 人物访谈」视频剪辑技能、项目工程与规范。教程技能组 v3 起为 **WorkBuddy 与千问办公双适用**——同一份内容，两端各自读取自己的接口元数据。访谈剪辑作为独立 skill 维护，不改变教程的配音生产链。

## 目录结构

```text
bazhuayu-vedio-cut/
├── README.md
├── .gitignore
├── skills/
│   ├── tutorial-video-slicing-workflow/   # 教程/宣发/演示技能组（主调度 + 子Skill + 脚本 + 素材）
│       ├── SKILL.md                       # 主文档 ≤100 行：模式/阶段路由与全局硬闸门
│       ├── .skill-metadata.yaml           # 千问办公推荐查询（7 个能力各一条，中英双语）
│       ├── agents/openai.yaml             # WorkBuddy（Codex）接口卡：展示名/简介/默认提示词
│       ├── references/                    # 子 Skill：阶段 01–07 + 三种模式 + 清单/运行时/字幕/配音等
│       ├── scripts/                       # 清单校验、字幕烧录、配音、音效合成、渲染锁定等
│       └── assets/                        # 样式/画布/音效库/项目清单与设计 token 模板
│   └── interview-video-editing/           # 原声访谈：主线/证据/执行脚本 + 可换色组件与生成器
├── projects/
│   ├── _template/                         # 新建剪辑项目的模板（含闸门留痕清单）
│   └── <项目名>/                          # 每个剪辑项目一个文件夹
└── work/                                  # 临时处理区（解压、截图、中间产物），不入库
```

技能组核心机制：`project-manifest.json` 是唯一结构化事实源，状态按 `initialized → evidence_ready → script_locked → voice_style_locked → voice_generated → subtitle_timeline_locked → visual_timeline_locked → preview_approved → variants_rendered → qa_passed → delivered` 推进，每次推进前必须过校验脚本。详见 `references/07-project-lifecycle.md` 与 `references/project-manifest.md`。

## 技能安装（团队成员每人一次）

把 `skills/tutorial-video-slicing-workflow/` 整个目录拷贝到所用宿主的技能目录：

| 宿主 | 技能目录 |
|---|---|
| 千问办公 | Windows `%USERPROFILE%\.qwenworkcn\skills\`；macOS `~/.qwenworkcn/skills/` |
| WorkBuddy（Codex） | Windows `%USERPROFILE%\.codex\skills\`；macOS `~/.codex/skills/` |

拷贝后重启宿主即可生效；两端共用同一份内容，禁止各自另改出第二套规范。

环境要求：Python 3.12+、Node.js/npm、imageio-ffmpeg（自动提供 FFmpeg）；运行时的选择、锁定与失败处理规则见 `references/runtime-and-tool-routing.md`，安装前按 `references/project-manifest.md` 的执行策略核对。

## 使用方式

在宿主新会话中附上素材并说明目标即可触发，例如：

- 教程切片：`按章节切这份教程并提取高光，先建素材证据库和唯一脚本给我确认`
- 企业业务演示：`用这些真实操作素材和业务稿制作演示视频，关键任务连续展示输入→执行→结果`
- 社媒宣发：`把这段无字幕演示素材剪成效果前置宣发片，先出时间线方案`
- 字幕/配音/横竖版派生/质检交付：参考千问办公技能卡片的推荐查询，或 WorkBuddy 默认提示词。

主 `SKILL.md` 只做调度：先选三种叙事模式之一，再按六个阶段加载对应子 Skill；所有模式共享硬闸门（单一时间源、整句配音、真实素材优先、双重预览、校验不过不交付）。

## 项目协作规范

### 独立访谈剪辑 skill

完整人物访谈、企业客户访谈使用 [interview-video-editing](skills/interview-video-editing/SKILL.md)。它以实际人物原声为时间基准，不生成或替换受访者旁白。

流程：阅读原素材 → 提炼主线 → 设计叙事节奏 → 回源定位证据 → 唯一执行脚本 → 原声粗剪 → 组件精剪 → 样段与跨章节验收 → 交付。

内置金句、人物主题页、章节气泡、Q卡、正式回答、字幕、证据插入和尾卡。可在项目配置中替换人物、主题、素材和统一配色；默认 1080×1440、30fps。依赖 Node.js 22+、FFmpeg/FFprobe，生成工程使用 HyperFrames 0.8.34。

安装时把 `skills/interview-video-editing/` 整个目录复制到个人 skill 目录。Codex 调用示例：`$interview-video-editing 请根据这些访谈视频和文字记录梳理主线，先给我剪辑执行脚本`。包含 `agents/openai.yaml` 和 `.skill-metadata.yaml`；生成/渲染测试在 macOS 完成，其他宿主和操作系统需按实际环境验证。

```bash
node skills/interview-video-editing/scripts/test.mjs
# 将 assets/project.example.json 复制到项目目录，替换素材与文案后：
node skills/interview-video-editing/scripts/build.mjs --validate projects/my-interview/config.json
node skills/interview-video-editing/scripts/build.mjs projects/my-interview/config.json work/interview-build-001
# 在生成目录执行 npm run check，通过后 npm run render
```

公开分发包只含通用代码、流程、样式和填写示例，不包含客户人像、原始采访、客户关键帧、本机绝对路径或测试视频。示例内容不是事实，必须替换并校对后才能用于客户成片。现有教程 skill 的“阶段 0 自动粗剪”保持原有授权与审核机制；独立访谈 skill 不自动调用它。

### 通用协作

- 每个剪辑任务在 `projects/` 下建独立文件夹，命名 `日期-题材`（如 `20260901-voc宣发复刻`），从 `projects/_template/` 复制起步。
- 视频、音频、截图等大文件一律不提交（见 `.gitignore`）；素材走网盘/共享目录，仓库只保留脚本、cue 表、时间轴、配置和说明文档。
- 正式交付结构遵循 `references/06-preview-qa-delivery.md`（`delivery/01_正式视频`–`07_工程`），项目清单与校验报告随工程入库。
- 修改剪辑规范时更新对应的 `skills/tutorial-video-slicing-workflow/` 或 `skills/interview-video-editing/` 并提 PR，合并后成员 `git pull` 重新拷贝对应 skill 到宿主技能目录。

## 更新流程

```bash
git pull
# 再把 skills/tutorial-video-slicing-workflow 覆盖拷贝到所用宿主的技能目录
```

## 版本记录

- **v3（当前）**：基于「视频剪辑复刻最小包」改造；主文档压缩至 ≤100 行调度器，references 重构为阶段 01–07 + 三模式 + 清单/运行时规范；保留 `agents/openai.yaml`，新增 `.skill-metadata.yaml` 与双语 frontmatter，WorkBuddy 与千问办公双适用。
- v2：初次千问办公合规化改造（详见 git 历史）。
