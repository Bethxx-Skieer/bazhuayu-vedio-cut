# 项目清单字段与校验

`project-manifest.json` 是唯一结构化事实源。新项目使用 `1.1` 模板，原有 `1.0` 清单继续可读；模板位于 `assets/project-manifest.template.json`。

## 关键字段

- `status`：必须遵循主 Skill 的状态链；
- `approvals.content`、`approvals.visualDirection`：记录状态、时间和备注；
- `sources[]`：资料与真实视频的来源、许可和证据；
- `narrative.sentences[]`：唯一讲稿、证据与实际时间；
- `visualDirection`：风格、人物、真实视频和视觉占比；
- `assets[]`：候选与选定资产；
- `scenes[]`：场景时间、视觉节拍、故事动作、锚点和转场；
- `voiceover`：人工录音路径、时长和锁定状态；
- `captions`：启用状态、Remotion Caption JSON 路径与样式；新项目默认开启，正式时间线锁定前可暂不填写文件路径；
- `music`：启用状态、文件、来源、许可、增益和人声避让设置；
- `outputs`：预览、正式视频和质检报告。

坐标框使用 0–1 归一化的 `x/y/width/height`。场景可以因连续转场发生重叠：下一场景的 `startSec` 应等于上一场景的 `startSec + durationSec - transitionOut.durationSec`。最后场景结束时间应与人工录音时长一致，容差默认 0.1 秒。

`visualBeats[].startSec` 是相对场景的时间。`kind` 支持 `illustration`、`character`、`real-video`、`screenshot`、`diagram`、`text-card`；`changeRole` 区分 `major` 与 `micro`，微动作不参与主要视觉节奏警告；`surface` 可为 `none` 或 `panel`，默认无装饰外框。真实视频可保存 `sourceInSec`、`sourceOutSec` 和 `playbackRate`。

新项目每个主要场景填写 `storyAction`：`question`、`concept`、`actorId`（无人场景可为 null）、`objectIds`、`action`、`outcome`、`triggerNarrationId`、`startSec`、`endSec`、`holdSec`。动作时间相对场景；人物与物件 ID 引用本场景视觉节拍。它是制作与审片契约，抽象概念必须显示物件状态怎样变化。模板只实现基础显示；需要搬运、合并、对照等具体关系时，在生成工程的 `src/CustomScenes.tsx` 按 `sceneId` 注册专门场景或转场组件。自定义场景接管可见物件，基础层不会再重复绘制。

新格式正式渲染时，若某场景只剩无素材的文字／图示占位而未注册自定义场景，工程会拒绝渲染。必须补上真实视觉资产或专门动画，不能把构思阶段的占位布局当成成片。

`captions.sourcePath` 指向 Caption JSON 数组，每条包含 `text`、`startMs`、`endMs`、`timestampMs`、`confidence`。构建时复制到工程并生成同时间轴的 SRT；旧项目缺少 `captions` 时保持原本无字幕行为。`music.sourceId` 引用 `sources[]`，`path` 指向本地媒体文件；音乐启用后需记录许可与试听确定的 `gain`，`ducking` 控制旁白期间的避让。

正式构建前运行：

```bash
python scripts/validate_project.py project-manifest.json
node scripts/build.mjs --validate project-manifest.json
```

校验报告中的 `error` 阻止构建；`warning` 必须在预览中人工检查。
