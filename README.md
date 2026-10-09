# 八爪鱼视频制作 Skill 库（bazhuayu-vedio-cut）

这是一个面向运营、内容和知识传播工作的 **AI 视频制作流程仓库**。它把团队做过的教程剪辑、案例宣发、业务演示、客户访谈和知识讲解动画，整理成可选择的 Skill、工程模板、脚本和质检规则。目标不是“上传素材后一键出片”，而是让不同成员从资料到成片都能按同一套可检查的步骤工作，减少重复剪辑和返工。

你提供主题、资料、录屏或访谈视频，以及目标平台和已有录音；选定对应 Skill 后，AI 协助梳理内容、设计分镜与素材、对齐声音和画面、制作字幕与版本，并在交付前检查事实、节奏、转场和画面遮挡。讲稿、视觉方向及最终效果仍由人确认。按任务可产出讲稿、分镜、项目清单、可编辑工程、成片和质检记录，而不只是一份视频文件。

| 要做的视频 | 典型输入 | 主要用途 |
|---|---|---|
| 教程切片、案例宣发、业务演示 | 教程录屏、真实操作素材、平台要求 | 从一份素材制作结构清楚、适合不同平台的案例或演示视频，并保留真实操作链路 |
| 人物访谈 | 采访原片、文字记录、传播重点 | 从原声中整理主线、删去重复表达，保留观点对应的原始证据 |
| 知识讲解动画 | 主题、参考资料、人工旁白 | 把抽象概念拆成角色和物件的可见动作，让非专业观众跟得上讲解 |

各能力独立维护，按任务选择，不会让访谈流程改写教程流程。教程技能组 v3 支持 WorkBuddy（Codex）与千问办公；访谈和知识讲解动画各自使用独立 Skill。想先看成片，可观看 [Git 是什么：知识讲解动画案例](examples/git-explainer/README.md)。

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
│   ├── interview-video-editing/           # 原声访谈：主线/证据/执行脚本 + 可换色组件与生成器
│   └── knowledge-explainer-video/         # 独立知识动画 Skill：内容拆解、角色交互、配音对齐、字幕与逐帧质检
├── examples/
│   └── git-explainer/                    # Git 知识讲解动画最终成片及案例说明
├── projects/
│   ├── _template/                         # 新建剪辑项目的模板（含闸门留痕清单）
│   └── <项目名>/                          # 每个剪辑项目一个文件夹
└── work/                                  # 临时处理区（解压、截图、中间产物），不入库
```

教程技能组以 `project-manifest.json` 为唯一结构化事实源，状态按 `initialized → evidence_ready → script_locked → voice_style_locked → voice_generated → subtitle_timeline_locked → visual_timeline_locked → preview_approved → variants_rendered → qa_passed → delivered` 推进，每次推进前必须过校验脚本。详见 [项目生命周期](skills/tutorial-video-slicing-workflow/references/07-project-lifecycle.md) 与 [清单规范](skills/tutorial-video-slicing-workflow/references/project-manifest.md)；访谈和知识讲解 Skill 使用各自的项目清单与检查流程。

## 技术栈、插件与各自的作用

这个仓库不是一款单独的视频编辑软件，而是三套可选的 AI 制作工作流，加上可复用脚本、素材模板和工程。工作时通常是：**Skill 指导内容与审批 → JSON 清单固定事实、时间线和素材 → Python／Node.js 脚本校验与组装 → 对应渲染工具出片 → 自动检查与人工审片**。三套 Skill 共享这个分层思路，但不共用同一个渲染器，也不要求安装所有依赖。

| 技术或组件 | 在本仓库做什么 | 适用范围 |
|---|---|---|
| `SKILL.md`、`references/`、`assets/` | 告诉 AI 如何拆内容、确认方案、制作和质检；保存分镜、样式、清单等可复用模板。Skill 是工作方法，不是视频引擎。 | 三套 Skill 各自独立 |
| `agents/openai.yaml`、`.skill-metadata.yaml` | 向对应宿主展示技能名称、简介或推荐提示词，帮助成员找到并调用 Skill；它们不负责剪辑和渲染。 | 宿主适配元数据；跨宿主能力仍需实际验证 |
| JSON 项目清单与时间线 | 记录已确认的讲稿、证据／原声位置、镜头、资产、字幕、音乐和交付状态，让脚本与人工审片依据同一份项目事实。 | 各 Skill 有自己的清单格式，不可直接互换 |
| Python、Node.js 脚本 | 校验输入和阶段条件，处理字幕与资源，生成或检查可执行工程；把重复操作固定下来，而不是每次临时拼命令。 | 按所选 Skill 运行对应脚本 |
| FFmpeg／FFprobe | 探测素材与时长、裁切和转码、处理音视频、导出检查帧并验证成片能否解码；它们是外部命令行工具，不随 Skill 文件夹自动安装。 | 教程、访谈、知识讲解的媒体处理／质检环节 |
| Git／GitHub | 管理 Skill、脚本、模板与案例的版本，让团队可以追踪修改和协作；不参与视频渲染。 | 整个仓库 |

三条制作路径使用技术的重点不同：

| 制作路径 | 关键技术及实际职责 |
|---|---|
| [教程／宣发／业务演示](skills/tutorial-video-slicing-workflow/SKILL.md) | Python 脚本管理清单、字幕和交付检查；FFmpeg 负责底层媒体操作；正式画面编排默认使用项目中另行准备、锁定依赖的 Remotion 工程，基于同一内容时间线做横竖版。当前仓库提供工作流与脚本，不随 Skill 附赠可直接渲染所有教程的统一工程。需要 AI 配音时接入**另行配置**的本地或云端 TTS 引擎，并锁定音色与参数；`generate-voiceover`、`ffmpeg`、`remotion` 等下游 Skill 只是按需使用的接入／诊断指导，不等于本仓库内置了对应服务。MoviePy 仅是明确选择后的特殊 Python 合成路径，不是 Remotion 出错时的自动替代。详见[运行时与工具路由](skills/tutorial-video-slicing-workflow/references/runtime-and-tool-routing.md)。 |
| [人物访谈](skills/interview-video-editing/SKILL.md) | Node.js [生成脚本](skills/interview-video-editing/scripts/build.mjs)读取剪辑执行配置，用 FFprobe 核对原片、FFmpeg 裁切原声片段并生成字幕时间线；[HTML 渲染模板](skills/interview-video-editing/assets/renderer.html)交给锁定版本的 HyperFrames 组成画面。原始受访者声音和源时间码是证据，不用 TTS 代说。HyperFrames 是这条访谈路径的渲染运行时，并非整个仓库的统一引擎。 |
| [知识讲解动画](skills/knowledge-explainer-video/SKILL.md) | Node.js [构建脚本](skills/knowledge-explainer-video/scripts/build.mjs)把已确认的清单、人物贴图、旁白、字幕和音乐装入工程；React／TypeScript 与 Remotion 制作角色、物件、镜头和连续转场，依赖见[工程配置](skills/knowledge-explainer-video/assets/remotion-template/package.json)。Python [校验脚本](skills/knowledge-explainer-video/scripts/validate_project.py)与 [成片质检脚本](skills/knowledge-explainer-video/scripts/qa_render.py)检查清单、时间线、关键帧和解码。正式版以用户人工录音定时；模板不会自动克隆声音，也不会仅凭主题自动生成可核对的真实视频素材。 |

知识讲解工程中的 Remotion 主包负责逐帧时间线、场景和动画；`@remotion/cli` 负责预览与导出，`@remotion/media` 把旁白、音乐或真实视频片段放入画面，`@remotion/captions` 提供字幕数据类型，字幕显示由工程自己的组件实现。React 用于把人物、物件和文字组织成可复用组件，TypeScript 用于约束项目数据。这里的字幕插件**不会自动转写录音**，字幕仍须依据真实录音制作并校对。

图片生成、转写、TTS、音乐库或外部真实视频素材可以按项目需要接入，但不是三套 Skill 的共同内置功能。使用前要确认工具可用性、素材来源和许可，并在项目清单里记录；只复制 Skill 文件夹不会一并安装 Node.js、Python、FFmpeg、字体、浏览器或第三方服务。安装需求应以所选路径及其文档为准。

## 技能安装（团队成员每人一次）

先下载或克隆本仓库，再把想用的 Skill **整个文件夹**复制到宿主的技能目录；可只安装当前任务需要的一个，不必把整个仓库放进去。

| Skill | 要复制的目录 | 在 Codex 中显式调用 |
|---|---|---|
| 教程／宣发／业务演示 | `skills/tutorial-video-slicing-workflow/` | `$tutorial-video-slicing-workflow` |
| 原声人物访谈 | `skills/interview-video-editing/` | `$interview-video-editing` |
| 知识讲解动画 | `skills/knowledge-explainer-video/` | `$knowledge-explainer-video` |

复制到以下目录，保持 Skill 文件夹名不变：

| 宿主 | 技能目录 |
|---|---|
| 千问办公 | Windows `%USERPROFILE%\.qwenworkcn\skills\`；macOS `~/.qwenworkcn/skills/` |
| WorkBuddy（Codex） | Windows `%USERPROFILE%\.codex\skills\`；macOS `~/.codex/skills/` |

复制后重启宿主，在新任务中使用上表的名称调用。教程技能组 v3 明确支持 WorkBuddy（Codex）与千问办公，并共用同一份规范；访谈和知识讲解 Skill 也有独立的宿主元数据，但在不同宿主、操作系统上的生成与渲染仍应按各自文档验证。

运行环境因 Skill 而异：教程流程按 [运行时说明](skills/tutorial-video-slicing-workflow/references/runtime-and-tool-routing.md) 核对 Python、Node.js 与 FFmpeg；访谈需 Node.js 22+、FFmpeg/FFprobe；知识动画的 Remotion 工程需 Node.js/npm，验证与质检还会用到 Python 和 FFmpeg。只做内容策划时，不必先安装全部渲染依赖。

## 使用方式

在新任务里先写 Skill 名称，再给素材文件／路径和目标。说明观众是谁、发布平台、希望的时长与画幅、是否已有录音，以及这次只要方案还是要完整视频；不确定的选项可以让 Skill 先提出建议。**一次先选一个主 Skill**：长教程或操作演示选教程 Skill，受访者原声为核心选访谈 Skill，解释一个概念或方法选知识动画 Skill。只要求讲稿、分镜或剪辑方案时，流程停在该阶段，不会直接渲染。

### 教程、社媒宣发与业务演示：`tutorial-video-slicing-workflow`

- **准备什么：**教程视频／录屏、文章或产品资料、真实操作素材；再说明是要按章节切教程、先展示结果做宣发，还是展示“输入 → 执行 → 结果”的业务案例。附上目标平台、横竖版要求和品牌规范；没有的项目可先让 Skill 建议。
- **怎么开始：**`$tutorial-video-slicing-workflow 请把这段八爪鱼 RPA 教程做成 16:9 案例视频和 3:4 社媒版。先整理素材证据库与唯一讲稿，给我确认后再继续。`
- **会怎样制作：**选定一种主模式 → 整理证据 → 确认唯一讲稿 → 试听并锁定配音 → 按实际声音制作字幕与镜头时间线 → 从同一时间线派生平台版本 → 看前 60 秒和跨章节预览 → 自动与人工质检。真实操作要保留可理解的任务闭环，不用无关画面填充。
- **你会得到：**按批准范围交付讲稿、证据与项目清单、预览、横竖版成片及工程。脚本未确认时不进入正式配音和全片制作；已有字幕转配音、字幕样式调整和局部返修可在同一项目中继续做。详见 [教程 Skill](skills/tutorial-video-slicing-workflow/SKILL.md)。

### 人物／客户访谈：`interview-video-editing`

- **准备什么：**原始访谈视频或音频、受访者身份与主题、期望保留的观点、发布平台；最好附转写文本，没有转写时先完成转写并回听。若有客户案例资料，提供可核对的业务证据。
- **怎么开始：**`$interview-video-editing 请用这段客户访谈做一支人物案例片。先通读原声、删去重复表达，列出主线、金句、问题顺序和对应的源时间码，给我剪辑执行表确认。`
- **会怎样制作：**看听原片 → 提炼主旨与 Q&A 顺序 → 为每个观点定位原声和证据 → 确认唯一执行表 → 粗剪真实原声 → 加人物、问题、回答和字幕组件 → 先验收片头与首个 Q&A，再审完整片。字幕忠于原话，不用 TTS 冒充受访者说话。
- **你会得到：**带源时间码的证据表、剪辑执行表，以及按批准范围生成的样段或完整访谈片。默认画幅为 3:4；换人物要换其真实素材与身份信息，不能沿用示例客户。详见 [访谈 Skill](skills/interview-video-editing/SKILL.md)。

### 概念、方法与项目演进：`knowledge-explainer-video`

- **准备什么：**最低只需主题和资料；可以补充目标观众、偏好的画风、是否要卡通人物、是否插入真实视频、字幕要不要开。正式成片还需提供人工录音；暂时没有录音，可以先做到静音预览。
- **怎么开始：**`$knowledge-explainer-video 请面向 Vibe Coding 新手讲清楚 Git。我提供资料，先给我口语化讲稿和内容结构；确认后再设计人物、代表帧和转场。等我录音后按声音做完整视频。`
- **会怎样制作：**核对事实、从具体问题切入 → 第一次确认讲稿与风格 → 设计人物、三张代表帧及连续转场样片 → 第二次确认视觉 → 制作图片和角色贴图 → 按人工录音安排动作、停顿、字幕与配乐 → 用 Remotion 制作并逐段审片。
- **你会得到：**讲稿、分镜与素材计划、代表帧／样片、带字幕的最终视频、独立字幕文件和可复用工程；若关闭字幕则不烧录。人物必须参与操作，转场从已有物件自然承接，重点检查遮挡与穿模。可先看 [Git 成片案例](examples/git-explainer/README.md)，再读 [知识讲解 Skill](skills/knowledge-explainer-video/SKILL.md)。

这些 Skill 都按“先确认内容，再制作下游”的原则运行。你可以在任一阶段要求暂停、只看样段，或针对某处返修；不需要每次都从头做一遍。

## 工程执行与项目协作

上面的用法面向视频需求提出者；下面记录清单、命令和交付约束，供实际制作与维护时使用。

### 独立知识讲解视频 skill

主题资料、项目演进、方法论、产品能力和概念科普使用 [knowledge-explainer-video](skills/knowledge-explainer-video/SKILL.md)。这是与教程切片、人物访谈并列的独立 Skill，不会自动触发；请在 Codex 中明确调用，例如：`$knowledge-explainer-video 用这些资料讲清楚 Git，先确认讲稿和画风`。

最低输入是“主题 + 资料”。Skill 先核对事实与受众，从具体场景中的问题切入，形成唯一口语化讲稿和“旁白句 → 知识点 → 人物／物件动作 → 可见结果”的分镜。每段只推进一个主要认识，让术语对应观众能看见的变化。可以选择迭代循环、概念拆解或对比论证；时长服从内容和实际录音，不硬塞进固定分钟数。

制作有两次确认：第一次确认讲稿、受众、风格、人物是否出现、真实视频策略、画幅和字幕开关；第二次确认角色姿势／表情、三张代表帧、素材比例、字幕安全区及一段 8–12 秒连续转场样片。画面把人物当作行动组件，让角色与物件发生提问、操作、检查、选择或协作；人物和插画默认不套白框，只有真实窗口或容器才加边界。图片可多做候选，成片只保留准确且风格统一的素材；通过景别、局部特写、状态变化和承接物转场增加观赏性，不用通用卡片排版冒充知识动画。

正式成片以用户人工录音为时间基准：按自然句和重点词安排“出现 → 操作 → 反馈 → 停留 → 交接”，允许清理口误和明显冗余空白，不加速正常语速。字幕默认开启、可在第一次确认时关闭；开启时按录音断句，交付烧录字幕视频及独立字幕文件。没有锁定录音时只允许静音预览。用户素材优先；外部真实视频和配乐要登记来源与许可。配乐要能听见又不盖住人声，并在整片试听后调整。

模板只提供时间线、透明素材渲染、字幕／音乐入口和基础组件；复杂知识关系须在 Remotion 工程里制作专门动画。每个场景和转场都要核对人物、物件、动作、结果与承接物；导出边界前／中／后帧以及复杂动作的起点／中间／落点，检查穿模、遮挡、文字互压、箭头语义、提前入场和残留。完整预览、字幕、混音与最终视频解码通过后才能交付。默认横版 1920×1080、30fps；主场景通常约 8–15 秒，仅作规划参考，画面速度由讲解和阅读负担决定。

项目清单使用 [manifest 模板](skills/knowledge-explainer-video/assets/project-manifest.template.json)；新版为 1.1，同时可读取旧版 1.0 清单。复制模板到项目目录、填写素材与分镜并完成相应确认后，在仓库根目录运行：

```bash
python skills/knowledge-explainer-video/scripts/validate_project.py projects/my-explainer/project-manifest.json
node skills/knowledge-explainer-video/scripts/build.mjs --validate projects/my-explainer/project-manifest.json
node skills/knowledge-explainer-video/scripts/build.mjs --preview projects/my-explainer/project-manifest.json work/explainer-preview
cd work/explainer-preview && npm ci && npm run render:preview
cd ../..
# 录音与时间线锁定、两次确认完成后：
node skills/knowledge-explainer-video/scripts/build.mjs projects/my-explainer/project-manifest.json work/explainer-final
cd work/explainer-final && npm ci && npm run render
cd ../..
python skills/knowledge-explainer-video/scripts/qa_render.py projects/my-explainer/project-manifest.json work/explainer-final/out/final.mp4 work/explainer-final/qa
```

已完成的 [Git 是什么：从 Vibe Coding 到多人协作](examples/git-explainer/README.md) 可作为本 Skill 的成片案例，包含带字幕和配乐的[最终视频](examples/git-explainer/git-explainer-final.mp4)。案例只提交最终成片，不提交用户原始录音、工程缓存或中间版本。

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
- 视频、音频、截图等大文件原则上不提交（见 `.gitignore`）；唯一例外是 `examples/git-explainer/git-explainer-final.mp4` 公开案例成片。其他素材走网盘/共享目录，仓库只保留脚本、cue 表、时间轴、配置和说明文档。
- 正式交付结构遵循 `references/06-preview-qa-delivery.md`（`delivery/01_正式视频`–`07_工程`），项目清单与校验报告随工程入库。
- 修改剪辑规范时更新对应的 `skills/tutorial-video-slicing-workflow/`、`skills/interview-video-editing/` 或 `skills/knowledge-explainer-video/` 并提 PR，合并后成员 `git pull` 重新拷贝对应 skill 到宿主技能目录。

## 更新流程

```bash
git pull
# 再把本次需要更新的 skills/tutorial-video-slicing-workflow、
# skills/interview-video-editing 或 skills/knowledge-explainer-video
# 整个目录覆盖拷贝到对应宿主技能目录
```

### 知识动画 Skill 1.4.0：动态设计、产品演示与修订验收

在既有讲稿、分镜和 Remotion 工程流程上，新增以下可按需读取的制作规范：

- [画面与动画优化推理](skills/knowledge-explainer-video/references/visual-revision-logic.md)：从语义、因果、注意力、连续性、阅读与证据诊断 PPT 感；用户明确选择本 Skill 时，支持旁白、解释动画与真实操作证据结合的产品能力片。
- [字幕与手机可读性](skills/knowledge-explainer-video/references/captions-and-readability.md)：自然断句、字号层级、字体加载、可选底板与句间闪烁检查；案例参数不作为所有主题的统一样式。

- [动画十二原则与动作谱](skills/knowledge-explainer-video/references/motion-language.md)：先确定观看过程，再安排预备、操作、接触、反馈和理解停顿；连续转场检查位置、速度、遮挡及物件所有权。
- [组件交互契约](skills/knowledge-explainer-video/references/interaction-contracts.md)：人物、指针、镜头和物件协同；屏幕裁切、容器前缘遮挡及多人选择的过程设计，避免穿模和 PPT 化。
- [特殊视频素材融合](skills/knowledge-explainer-video/references/footage-integration.md)：按内容与源时间码拆解录屏／实拍素材，设计动画切入、局部解释、原声处理与切出。
- [配乐与 MP4 导出](skills/knowledge-explainer-video/references/audio-and-export.md)：从干声重混，记录许可与署名，核对最终编码、音轨、时长并完整解码。
- [反馈回归](skills/knowledge-explainer-video/references/feedback-and-regressions.md)与[分项审查模板](skills/knowledge-explainer-video/assets/revision-review.template.json)：分别记录静帧、原速动画、音画试听和文件检查，不把技术成功当作整体效果通过。

动作谱可用 `python skills/knowledge-explainer-video/scripts/validate_motion_score.py <motion-score.json>` 校验。它检查计划数据，不自动评定动画审美。本次不替换 Git 演示视频，也不改变教程或访谈 Skill 的流程。

## 版本记录

- **knowledge-explainer-video v1.4.0**：增加画面优化推理、产品能力片证据指引与字幕可读性规范；明确人物可选、人工录音完整性检查及用户授权声音处理后的统一时间线。

- **knowledge-explainer-video v1.3.0**：补充十二原则、特殊素材融合、组件交互契约、配乐重混、MP4 导出验证和分项审片记录；兼容旧项目清单。

- **knowledge-explainer-video v1.1**：把 Git 讲解片经验固化为角色／物件／动作／结果分镜、按人工录音对齐的慢节奏动画、无默认白框的透明素材与专门场景、默认可关闭的字幕、许可可查的配乐及逐段／逐边界 QA；清单和 Remotion 模板同步升级。
- **knowledge-explainer-video v1**：新增可显式选择的知识讲解视频 Skill；内置证据驱动叙事、两次人工确认、卡通角色素材表、真实素材授权台账、慢节奏标准、共享载体连续转场、人工配音锁定、Remotion 工程生成与逐边界 QA。
- **v3（当前）**：基于「视频剪辑复刻最小包」改造；主文档压缩至 ≤100 行调度器，references 重构为阶段 01–07 + 三模式 + 清单/运行时规范；保留 `agents/openai.yaml`，新增 `.skill-metadata.yaml` 与双语 frontmatter，WorkBuddy 与千问办公双适用。
- v2：初次千问办公合规化改造（详见 git 历史）。
