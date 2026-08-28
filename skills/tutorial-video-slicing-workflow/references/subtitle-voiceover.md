# 字幕时间轴配音规范

## 目标

把带开始/结束时间的字幕转换为与画面对齐的配音轨，并安全合成回视频。时间码是唯一排布基准；不要按全文字数平均分配时间。

## 输入优先级

按以下顺序接收字幕：

1. `.srt`：首选。
2. `.vtt`：解析 cue 时间码后使用。
3. `.ass`：读取 `[Events]` 的 `Dialogue`，去除样式标签并保留换行语义。
4. 带时间码的 JSON：接受数组，或 `subtitles`、`segments`、`cues` 数组；每项至少包含 `start`、`end`、`text`。

只有整篇纯文本时，可以生成连续配音，但不得声称已经与画面对齐。应先按画面拆句并制作 SRT；无法可靠判断时间点时，向用户索要带时间码字幕或确认人工时间表。

## 文案边界

- 说明字幕不一定适合朗读。章节编号、按钮标签、纯视觉提示和重复信息默认不进入配音稿。
- 每个 cue 只保留自然口语的一句话；长句先改写、拆句，再调整语速。
- 专有名词、数字、英文缩写和 Skill 名称须先校对发音文本。
- 屏幕中常驻的章节标题不应在整个显示期间持续占用配音；只在章节进入时朗读一次。

## 对齐策略

逐句合成后，比较实际音频时长 `spoken` 与字幕窗口 `window = end - start`：

- `spoken <= window`：保持自然语速，在句后补静音直到 cue 结束。
- `window < spoken <= window × max_stretch`：只对该句做轻微加速。默认 `max_stretch = 1.18`，即最多约加速 18%。
- `spoken > window × max_stretch`：标记为超时并停止正式合成。优先缩短文案、移动边界或拆分 cue；不要默认截断句尾。
- cue 之间的空档按时间码插入静音。
- cue 重叠、结束早于开始或时间码超出视频时长均视为错误，先修正时间轴。

若用户明确选择激进处理，才允许提高加速上限或截断；成品说明必须记录被处理的句子。

## Voicebox 与本机声音

使用 `scripts/subtitle_voiceover.py`。中文默认音色和语速的唯一机器可读来源是 [../assets/voiceover-profile-zh-CN.json](../assets/voiceover-profile-zh-CN.json)：默认使用“黎潋（Lilian Premium）”、语速 `185`。脚本必须把实际音色、语速和配置路径写入报告。Voicebox 的具体 CLI/API 可能不同，因此通过 `--tts-command` 适配，而不把某个未确认的命令写死在 Skill 中。

禁止静默回退到 `Tingting`、其他系统音色或未确认的 Voicebox 音色。若黎潋未安装，先停止合成并让用户确认替代音色；只有用户明确指定时才使用 `--voice` 覆盖。

命令模板由参数数组执行，不经过 shell。至少包含 `{text_file}` 与 `{output_file}`；还可用 `{text}`、`{voice}`、`{rate}`。优先让 Voicebox 从 UTF-8 文本文件读取，避免长文本和引号转义问题。

示意：

```bash
python scripts/subtitle_voiceover.py captions.srt \
  --tts-command 'voicebox synth --text-file {text_file} --output {output_file}' \
  --raw-extension wav \
  --output-audio voiceover.wav \
  --report voiceover-report.json
```

在 macOS 上使用默认中文音色验证流程：

```bash
python scripts/subtitle_voiceover.py captions.srt \
  --backend say \
  --output-audio voiceover.wav \
  --video input.mp4 --output-video dubbed.mp4 \
  --report voiceover-report.json
```

先运行 `say -v '?'` 确认 `Lilian (Premium)` 已安装；若不存在，必须让用户确认替代音色，不能自行改用其他声音。
`say` 依赖 macOS 的语音服务和已下载语音；无桌面音频服务的沙箱或远程环境可能只能完成时间轴检查。此时使用 `--backend command` 接 Voicebox 做正式合成，不把系统声音失败误判为时间轴失败。

## 音轨合成

- 默认 `replace`：保留视频流，用对齐后的配音替换原音轨。
- `mix`：保留原声并降低音量后与配音混合，适合保留操作音或轻背景声。
- 若需要 BGM，确保层级为配音 > 原声/操作声 > BGM，并在有人声区间做压低。
- 最终视频使用 AAC；尽量复制原视频流，避免无必要的二次视频编码。

## 强制质检

交付前检查 `voiceover-report.json`，并完成：

- `status` 为 `ok`，且没有 `overrun` 或时间轴错误。
- 抽听第一句、最长句、发生轻微加速的句子、章节切换和最后一句。
- 检查发音、断句、静音长度、音量、峰值和声画同步。
- 使用 ffprobe 确认成片包含视频流和 AAC 音频流，且时长合理。
- 保留原字幕文件、最终配音稿、报告和独立 WAV 音轨，便于重做单句。
- 运行 `scripts/validate_render_lock.py`，确认实际音色、语速和字幕样式均与锁定配置一致。
