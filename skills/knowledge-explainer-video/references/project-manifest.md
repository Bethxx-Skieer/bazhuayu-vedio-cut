# 项目清单字段与校验

`project-manifest.json` 是唯一结构化事实源。模板位于 `assets/project-manifest.template.json`。

## 关键字段

- `status`：必须遵循主 Skill 的状态链；
- `approvals.content`、`approvals.visualDirection`：记录状态、时间和备注；
- `sources[]`：资料与真实视频的来源、许可和证据；
- `narrative.sentences[]`：唯一讲稿、证据与实际时间；
- `visualDirection`：风格、人物、真实视频和视觉占比；
- `assets[]`：候选与选定资产；
- `scenes[]`：场景时间、视觉节拍、锚点和转场；
- `voiceover`：人工录音路径、时长和锁定状态；
- `outputs`：预览、正式视频和质检报告。

坐标框使用 0–1 归一化的 `x/y/width/height`。场景可以因连续转场发生重叠：下一场景的 `startSec` 应等于上一场景的 `startSec + durationSec - transitionOut.durationSec`。最后场景结束时间应与人工录音时长一致，容差默认 0.1 秒。

`visualBeats[].startSec` 是相对场景的时间。`kind` 支持 `illustration`、`character`、`real-video`、`screenshot`、`diagram`、`text-card`。真实视频可保存 `sourceInSec`、`sourceOutSec` 和 `playbackRate`。

正式构建前运行：

```bash
python scripts/validate_project.py project-manifest.json
node scripts/build.mjs --validate project-manifest.json
```

校验报告中的 `error` 阻止构建；`warning` 必须在预览中人工检查。
