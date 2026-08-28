# 教程切片执行流程（子 Skill：Step 1–6）

教程切片模式的逐步执行手册。选题与二创策略见 [slicing-matrix-method.md](slicing-matrix-method.md)；闸门、参数与质检见 [common-standards.md](common-standards.md)。

## 环境准备

要求 Python 3.12+。在本会话工作目录创建隔离虚拟环境并安装 `imageio-ffmpeg`（自带 ffmpeg 二进制，无需系统安装 ffmpeg，当前版本 7.1）：

```bash
python -m venv {WORKSPACE}/.venv
# Windows:
{WORKSPACE}/.venv/Scripts/pip.exe install imageio-ffmpeg
# macOS/Linux:
{WORKSPACE}/.venv/bin/pip install imageio-ffmpeg
```

ffmpeg 路径在任意脚本内通过以下方式获取：

```python
import imageio_ffmpeg
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
```

后续脚本中的 `{WORKSPACE}`、`{OUTPUT_ROOT}` 等占位符含义见 [common-standards.md](common-standards.md) 变量替换表。Windows 控制台为 GBK 编码，脚本内打印中文前务必重配 stdout 或改为写 UTF-8 日志文件。

## Step 1：解压视频素材（处理中文文件名）

> Windows 下中文 zip 文件名默认按 cp437 解码会乱码，按 `cp437→gbk`、`latin-1→gbk`、原始名三级 fallback 解码。

```python
#!/usr/bin/env python3
"""extract_video.py - 解压zip视频，处理中文文件名"""

import zipfile
import os
import sys

zip_path = r"{ZIP_FILE_PATH}"            # 替换为实际zip路径
extract_to = r"{WORKSPACE}/raw_footage"  # 替换为工作目录

os.makedirs(extract_to, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as z:
    for info in z.infolist():
        try:
            name = info.filename.encode('cp437').decode('gbk')
        except (UnicodeDecodeError, UnicodeEncodeError):
            try:
                name = info.filename.encode('latin-1').decode('gbk')
            except (UnicodeDecodeError, UnicodeEncodeError):
                name = info.filename

        target = os.path.join(extract_to, name)
        os.makedirs(os.path.dirname(target) or extract_to, exist_ok=True)
        with z.open(info) as src, open(target, 'wb') as dst:
            while True:
                chunk = src.read(8192 * 1024)  # 8MB分块
                if not chunk:
                    break
                dst.write(chunk)
        print(f"Done: {target}", file=sys.stderr)
```

## Step 2：探测视频信息 + 每 30 秒截图

```python
#!/usr/bin/env python3
"""probe_video.py - 获取视频信息并每30秒截图用于内容分析"""

import os
import re
import subprocess
import imageio_ffmpeg

RAW_DIR = r"{WORKSPACE}/raw_footage"
SCREENSHOT_DIR = r"{WORKSPACE}/screenshots"

video_files = [f for f in os.listdir(RAW_DIR)
               if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))]
video_path = os.path.join(RAW_DIR, video_files[0])
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

result = subprocess.run([ffmpeg_path, "-i", video_path],
                        capture_output=True, text=True)
stderr = result.stderr

duration_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', stderr)
total_seconds = 0
if duration_match:
    h, m, s = duration_match.groups()
    total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
    print(f"Duration: {h}:{m}:{s} ({total_seconds:.1f}s)")

res_match = re.search(r'(\d+)x(\d+)', stderr)
if res_match:
    print(f"Resolution: {res_match.group(1)}x{res_match.group(2)}")

fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', stderr)
if fps_match:
    print(f"Frame rate: {fps_match.group(1)} fps")

interval = 30
num_screenshots = int(total_seconds / interval) + 1
for i in range(num_screenshots):
    t = i * interval
    if t >= total_seconds:
        break
    ts_str = f"{t//3600:02d}_{(t%3600)//60:02d}_{t%60:02d}"
    output_file = os.path.join(SCREENSHOT_DIR, f"frame_{i:03d}_{ts_str}.jpg")
    subprocess.run([ffmpeg_path, "-ss", str(t), "-i", video_path,
                    "-frames:v", "1", "-q:v", "3",
                    "-vf", "scale=640:-1",
                    output_file], capture_output=True, text=True)
```

> 非 16:9 源先无拉伸标准化为 1920×1080、SAR 1:1，再进入后续步骤。

## Step 3：场景检测 + 板块边界定位

用 ffmpeg `select` 滤镜 + `scene` 阈值检测画面突变点（脚本版，跨平台，不依赖 grep/awk）：

```python
#!/usr/bin/env python3
"""detect_scenes.py - 场景变化点检测（阈值0.15）"""

import re
import subprocess
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO = r"{WORKSPACE}/raw_footage/{VIDEO_FILENAME}"
THRESHOLD = 0.15

result = subprocess.run(
    [FFMPEG, "-i", VIDEO, "-vf",
     f"select='gt(scene,{THRESHOLD})',showinfo", "-an", "-f", "null", "-"],
    capture_output=True, text=True)

pts = [round(float(m), 2)
       for m in re.findall(r"pts_time:\s*([\d.]+)", result.stderr)]
print("Scene change points (s):")
for p in pts:
    print(f"  {p}")
```

对检测到的关键时间点提取帧做视觉确认：

```bash
"$FFMPEG" -y -ss {ts} -i "$VIDEO" -frames:v 1 -q:v 2 scene_frames/scene_{ts}.jpg
```

用 `Read` 工具逐帧阅读截图，确认每个板块标题卡出现的精确时间。典型系列教程板块结构：

| 板块 | 识别特征 | 典型时间占比 |
|------|---------|-------------|
| 片头目录 | 标题动画 + 板块列表 | 0-10% |
| 效果展示 | 产品演示/Step1-4操作 | 10-35% |
| 业务背景 | 痛点/PPT文字密集 | 35-60% |
| 功能设计 | 架构图/功能清单 | 60-80% |
| 实操教程 | 屏幕录制+配置步骤 | 80-95% |
| 片尾 | 辅助工具/引导关注 | 95-100% |

> **关键经验**：标题卡（板块分隔页）是最可靠的边界标记，场景检测可定位其出现的精确帧。阈值选择见 common-standards.md FAQ。

## Step 4：板块切割

```python
#!/usr/bin/env python3
"""cut_sections.py - 按精确时间码切割视频为板块"""

import subprocess
import os
import json
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO = r"{WORKSPACE}/raw_footage/{VIDEO_FILENAME}"
OUTPUT_DIR = r"{OUTPUT_ROOT}/01_板块切割"

# 板块边界（由Step 3视觉确认，替换为实际时间码）
SEGMENTS = [
    {"name": "00_片头目录",    "start": "0:00",  "end": "2:00",  "desc": "标题 + 目录总览"},
    {"name": "01_效果展示",    "start": "2:00",  "end": "6:18",  "desc": "产品四步演示"},
    {"name": "02_业务背景",    "start": "6:18",  "end": "12:30", "desc": "痛点分析与工作流"},
    {"name": "03_功能设计",    "start": "12:30", "end": "15:48", "desc": "功能清单与架构"},
    {"name": "04_实操教程",    "start": "15:48", "end": "19:00", "desc": "五步配置教程"},
    {"name": "05_片尾辅助工具", "start": "19:00", "end": "19:57", "desc": "辅助工具 + 结尾"},
]

def time_to_seconds(t):
    parts = t.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(t)

def cut_segment(seg):
    start_sec = time_to_seconds(seg["start"])
    duration = time_to_seconds(seg["end"]) - start_sec
    output_file = os.path.join(OUTPUT_DIR, f"{seg['name']}.mp4")
    cmd = [FFMPEG, "-y", "-ss", str(start_sec), "-i", VIDEO, "-t", str(duration),
           "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-c:a", "aac", "-b:a", "256k",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    ok = result.returncode == 0 and os.path.exists(output_file)
    print(f"[{'OK' if ok else 'FAIL'}] {seg['name']}")
    return ok

os.makedirs(OUTPUT_DIR, exist_ok=True)
results = [(s["name"], cut_segment(s)) for s in SEGMENTS]
with open(os.path.join(OUTPUT_DIR, "segments.json"), "w", encoding="utf-8") as f:
    json.dump(SEGMENTS, f, ensure_ascii=False, indent=2)
assert all(ok for _, ok in results), "存在切割失败，检查上方日志"
```

编码参数依据（libx264 / CRF 18 / preset fast / yuv420p / +faststart）见 common-standards.md 技术参数速查。

## Step 5：切片提取 + 单源多画布渲染

默认流程**不是**把完成字幕的横版整体缩小。先完成无平台字幕的 16:9 增强内容母版，再共用同一字幕时间轴、配音、音效和增强事件，分别渲染 16:9 横版与 3:4 冰蓝品牌版。3:4 的逐镜头裁切、标题、产品框和字幕按 [xhs-portrait-composition.md](xhs-portrait-composition.md) 执行。

```python
#!/usr/bin/env python3
"""create_slices.py - 提取16:9高光母版并登记3:4品牌版渲染队列"""

import subprocess
import os
import json
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO = r"{WORKSPACE}/raw_footage/{VIDEO_FILENAME}"
OUT_H = r"{OUTPUT_ROOT}/02_横版切片"
OUT_V = r"{OUTPUT_ROOT}/03_小红书3比4"

# 切片定义（时间码、描述、是否转竖版）— 根据Step 3截图分析结果填写
SLICES = [
    {"name": "01_效果展示-一句话自动化", "start": "2:20",  "end": "3:05",
     "desc": "对话触发自动化任务-核心价值", "vertical": True},
    {"name": "01_效果展示-数据秒出",     "start": "4:30",  "end": "5:15",
     "desc": "数据采集与清洗-效率震撼",   "vertical": True},
    # ... 其余切片见 slicing-matrix-method.md 选题矩阵
]

def time_to_seconds(t):
    parts = t.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(t)

def cut_horizontal(s):
    start_sec = time_to_seconds(s["start"])
    duration = time_to_seconds(s["end"]) - start_sec
    output_file = os.path.join(OUT_H, f"{s['name']}.mp4")
    cmd = [FFMPEG, "-y", "-ss", str(start_sec), "-i", VIDEO, "-t", str(duration),
           "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-c:a", "aac", "-b:a", "256k",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"H-CUT ERROR: {result.stderr[-300:]}")
        return None
    return output_file

def convert_vertical_legacy_black(input_file, output_file):
    """旧兼容模式：16:9成片转3:4纯黑留边。仅限用户明确要求完整保留横版画面
    并接受纯黑留边时使用；默认品牌版禁止调用。"""
    vf = "scale=1080:608:flags=lanczos,setsar=1,pad=1080:1440:0:416:black"
    cmd = [FFMPEG, "-y", "-i", input_file, "-vf", vf,
           "-c:v", "libx264", "-preset", "fast", "-crf", "20",
           "-c:a", "aac", "-b:a", "256k",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-r", "30", output_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

os.makedirs(OUT_H, exist_ok=True)
os.makedirs(OUT_V, exist_ok=True)
results = []
for s in SLICES:
    h_file = cut_horizontal(s)
    if not h_file:
        results.append((s["name"], "H-FAIL"))
        continue
    if s["vertical"]:
        # 只登记待渲染切片。默认品牌版必须从无字幕增强内容母版出发，
        # 读取品牌画布配置与 framing-cues.json 二次自动渲染，
        # 不能把横版成片直接传给旧黑底函数。
        results.append((s["name"], "BRAND-QUEUE"))
    else:
        results.append((s["name"], "H-ONLY"))

meta = {"slices": SLICES, "horizontal_dir": OUT_H, "vertical_dir": OUT_V,
        "render_queue": results}
with open(os.path.join(OUT_V, "slices.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
```

3:4 默认品牌合成逻辑：

```text
任意源画幅 → 标准化1920×1080（不拉伸；宣发默认内容感知裁切铺满，
完整教程必要时纯黑补边）
    → 叠加内容绑定增强，生成无平台字幕增强内容母版
        ├── 渲染16:9底部字幕 ──▶ 1920×1080横版
        └── 按framing-cues逐镜头fill裁切 ＋ 冰蓝画布、居中标题、
            产品框、框外字幕 ──▶ 1080×1440小红书品牌版
```

坐标、取景锚点、封面派生与质检以 [xhs-portrait-composition.md](xhs-portrait-composition.md) 和 `assets/xhs-portrait-octopus-blue-1080x1440.json` 为准。

## Step 6：成品输出目录结构

```text
{输出根目录}/
├── 01_板块切割/          # 按板块切割的完整横版视频（含 segments.json）
├── 02_横版切片/          # 高光片段 16:9（B站/YouTube/公众号）
├── 03_小红书3比4/        # 由增强内容母版渲染的 1080×1440 冰蓝品牌成品
└── 切片成品说明.md       # 完整成品说明文档
```

企业业务演示模式不套用本目录，改用 enterprise-business-demo-production.md 定义的 `01_正式视频`–`07_工程` 结构。说明文档需列出：每个切片的名称、时间码、内容描述、目标平台与推荐用法。

交付前执行 [common-standards.md](common-standards.md) 的质检清单与 `scripts/validate_render_lock.py`。
