# 项目清单规范

## 作用

`project-manifest.json` 是项目唯一结构化事实源。它连接脚本、配音、字幕、素材、镜头、平台版本、运行环境和质检结果。Markdown 方案可以用于阅读，但不得成为另一份独立时间线。

## 顶层结构

| 字段 | 内容 |
|---|---|
| `schemaVersion` | 清单格式版本 |
| `project` | 项目名称、模式、目标、工作目录和输出目录 |
| `state` | 当前流程状态 |
| `execution` | 标准执行策略、正式渲染器和是否允许备用路径 |
| `runtime` | Remotion、FFmpeg、TTS、字体和样式版本 |
| `subtitlePolicy` | 字幕与自然断句的句末标点及文字一致性规则 |
| `script` | 活跃脚本版本和自然句 |
| `pronunciations` | 显示词、TTS 别名、读法和停顿 |
| `assets` | 素材证据库 |
| `timeline` | 唯一内容时间线、字幕 cue 和镜头 |
| `variants` | 横版、竖版等布局覆盖项 |
| `approvals` | 用户确认的脚本、声音和预览 |
| `qa` | 自动与人工质检结果 |

## 唯一 ID

使用稳定 ID：

- 自然句：`N001`；
- 字幕 cue：`C001`；
- 素材：`A001`；
- 镜头：`S001`；
- 组件：`V001`。

修改文案或时间时保持 ID；只有语义完全改变或删除后重新新增时才创建新 ID。

## 自然句

每句至少保存：

- `id`；
- `spokenText`；
- `displayText`；
- `ttsText`；
- `targetDurationSec`；
- `actualDurationSec`；
- `audioPath`；
- `subtitleCueIds`；
- `evidenceIds`；
- `visualIntent`。

`displayText` 的最后一个字符不得是标点符号；句中标点可以保留。`ttsText` 可以为发音和停顿增加控制信息，但实际词语必须与 `spokenText` 对应。

## 执行策略与运行时

标准项目使用 `execution.canonicalPath=verified-scripts`。`renderer` 默认是 `remotion`，`moviepyEnabled` 默认关闭，`allowSilentFallback` 必须为 `false`。

`runtime` 不只记录版本号，还应记录运行时配置 ID、复现等级、锁文件、浏览器版本、字体与二进制哈希、TTS 模型和参数摘要。需要跨系统高度一致时，记录容器镜像摘要；需要完全复现既有配音时，保存逐句音频和哈希，而不是重新调用 TTS。

## 时间线

`timeline.id` 是平台版本共同引用的 `contentTimelineId`。时间线包含：

- 完整配音路径和时长；
- 唯一字幕 cue；
- 唯一镜头数组；
- 可选的增强事件。

平台版本不得包含 `narration`、`subtitleCues` 或 `shots` 的复制项，只能包含布局配置、裁剪覆盖和输出路径。

## 状态更新

只有对应产物和审批存在时才更新状态。状态按固定顺序推进，不允许跳级。用户要求回退文案或声音时，把状态回退到最早受影响阶段，并重新生成下游产物。

## 项目配置与通用 Skill

以下内容写入清单，不写入通用 Skill：

- 品牌、产品和专业词读法；
- 项目指定时间码；
- 目标时长和语速；
- 具体字体、标题和间距覆盖；
- 某类报告是否只展示索引；
- 用户已批准的例外。

## 校验

运行：

```text
python scripts/validate_project_manifest.py project-manifest.json
```

校验器检查结构、状态闸门、字幕文字、镜头覆盖、素材状态和平台单源关系。模板在 `initialized` 状态可以为空；推进状态后对应字段必须完整。
