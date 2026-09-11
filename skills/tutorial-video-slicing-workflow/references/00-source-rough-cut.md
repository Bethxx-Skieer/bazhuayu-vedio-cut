# 阶段 0：源素材自动粗剪与无效片段剔除（访谈类 · 按需门控）

> 本阶段**不在核心生产链中**，仅在**用户对访谈 / 口播类素材明确请求**时才进入。
> 教程切片、企业业务演示、社媒效果宣发等模式默认不启用本阶段。

## 1. 触发条件（门控）

同时满足才启用：

1. 素材为**访谈 / 口播类**原始录制（非教程录屏、非业务演示操作录屏）；
2. 用户**明确**要求，例如：「对这段访谈做自动粗剪与无效片段剔除」「去掉这段口播里的长静音和重复内容」。

未同时满足时，不要主动调用 `scripts/auto_rough_cut.py`，也不要在脚本未覆盖时临时拼 ffmpeg 命令。

## 2. 目标

在建立素材证据库之前，先把原始访谈素材里的**长静音（无效空白）**和**重复 / 冗余段落**粗剪掉，减少下游证据库与脚本的噪声。本阶段是预处理，不改变业务事实，只删除可安全移除的空档与重复。

## 3. 执行脚本

`scripts/auto_rough_cut.py`（已验证脚本优先；底层用 imageio-ffmpeg 提供的 FFmpeg）。

两步走（先审阅、后剪切，符合仓库「先校验、不校验不交付」文化）：

```bash
# 第一步：检测 + 生成可审阅 cut_plan.json（落 work/）
python scripts/auto_rough_cut.py run \
  --input 访谈原始.mp4 \
  --transcript 访谈转写.srt \      # 源视频时间戳对齐的 SRT/VTT/JSON；缺省则仅做静音粗剪
  --work work/

# 第二步：人工 / 自动校验通过后，改为 approved 再执行剪切
python scripts/auto_rough_cut.py apply \
  --plan work/cut_plan.json \
  --input 访谈原始.mp4 \
  --output work/访谈粗剪.mp4
```

- `run` 不修改源视频，只产出 `work/cut_plan.json`。
- `apply` 前必须把 `cut_plan.json` 的 `review.status` 改为 `approved`；`--force` 可跳过闸门但**不推荐**。
- 仅做静音粗剪：`run --no-redundancy`（无转写或不想跑嵌入时）。

## 4. 检测原理

### 4.1 静音 / 无效空白（Silero VAD）
- 用 **Silero VAD**（本地、零网络、专为人声）在 16kHz 单声道音轨上判语音活动，**避开 BGM / 环境音干扰**（这是弃用 `silencedetect` 的原因：有背景音乐时电平检测会失效）。
- speech 区间两侧留 `edgePaddingSec`（默认 0.15s）缓冲，避免切掉词尾产生爆音。
- 由 speech 反推静音，仅保留时长 ≥ `deadAirThresholdSec`（默认 1.8s）的段作为「无效空白」——短气口（正常思考停顿）保留，成品不「喘」。

### 4.2 冗余 / 重复（本地文本嵌入）
- 读取**源视频时间戳对齐**的转写（SRT / VTT / JSON）。**时间戳必须对齐源素材时间，不是配音时间**。复用仓库既有「读取既有字幕」约定（参见 `scripts/subtitle_voiceover.py`）。
- 用本地 `sentence-transformers`（`paraphrase-multilingual-MiniLM-L12-v2`，支持中英）生成句向量。
- 相似度 = 余弦（向量已归一化，即点积）。**滑动窗口 + 全局近邻**双向比较，既抓相邻重复也抓非相邻重复。
- 相似度 ≥ `simThreshold`（默认 0.86）且段长 ≥ `minSegmentSec`（默认 3s）才标记；`action=drop` 按 `drop_shorter` 删更短 / 更晚出现的重复段，降低误删风险。

## 5. cut_plan.json 结构（可审阅中间产物）

完整 schema 见设计草稿 `auto-rough-cut-design-draft.md`（评审版，不入库）。核心字段：

- `source`：源素材元信息（视频文件不入 git）。
- `params`：本次运行参数快照，保证可复现。
- `silenceIntervals` / `transcriptSegments` / `redundancyPairs`：中间证据，供人工核对。
- `removeIntervals` / `keepIntervals`：**互补**区间，校验「删除 + 保留 = 全集、无重叠、无间隙、覆盖 [0, duration]」。
- `summary`：移除 / 保留时长与占比、冗余段对数。
- `review`：闸门。`status=pending` 禁止渲染；人工或自动校验通过后置 `approved`。

## 6. 校验闸门

`apply` 内置 `validate_plan`：检查 `keepIntervals` 单调、无负时长、覆盖到视频末尾、`review.status == approved`。任一不满足即中止，**不静默剪切**。

## 7. 依赖与降级

| 能力 | 依赖 | 缺失时 |
|---|---|---|
| 静音检测 | `silero-vad` `torch` `soundfile` | 报错退出，不静默回退 |
| 冗余检测 | `sentence-transformers` | 用 `run --no-redundancy` 仅做静音粗剪 |
| 媒体处理 | `imageio-ffmpeg`（随仓库运行时） | 退回系统 PATH 的 `ffmpeg` |

阈值初值（1.8s 死区、0.86 相似度）为起点，**待真实素材验证后再校准**；样本异常时回到本文件与脚本调参。

## 8. 与主线关系

- 本阶段产物是**源素材预处理**结果，下游证据库 / 脚本仍基于粗剪后素材，不引入第二套时间线。
- 不破坏仓库既有单一事实源与校验文化；`cut_plan.json` 落 `work/`（临时处理区，不入库），粗剪成品亦在 `work/` 预览，确认后再进入正式工程。
