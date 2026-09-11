#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_rough_cut.py — 访谈类源素材自动粗剪与无效片段剔除（阶段 0，门控启用）

适用：仅访谈 / 口播类原始素材。教程 / 业务演示 / 社媒宣发模式默认不启用。
触发：只有当用户明确对访谈视频请求「自动粗剪与无效片段剔除」时才调用本脚本。

流程：
  run    Silero VAD 静音检测 + 文本嵌入冗余检测 -> work/cut_plan.json（可审阅）
  apply  cut_plan.json -> ffmpeg filtergraph 重编码 concat -> 粗剪成品（需 review 通过）

设计要点与参数见 references/00-source-rough-cut.md。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# 通用工具
# ----------------------------------------------------------------------------

DEFAULT_PARAMS = {
    "vad": {
        "model": "silero-vad",
        "threshold": 0.5,
        "minSpeechSec": 0.25,
        "maxSilenceSec": 0.5,
        "speechPadSec": 0.10,
    },
    "silence": {
        "deadAirThresholdSec": 1.8,
        "edgePaddingSec": 0.15,
        "keepShortPauses": True,
    },
    "redundancy": {
        "embedder": "paraphrase-multilingual-MiniLM-L12-v2",
        "windowSec": 45,
        "simThreshold": 0.86,
        "minSegmentSec": 3.0,
        "strategy": "drop_shorter",
    },
    "output": {
        "reencode": True,
        "videoCodec": "libx264",
        "audioCodec": "aac",
        "crf": 18,
    },
}


def get_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def run_ffmpeg(args):
    exe = get_ffmpeg()
    cmd = [exe, *args]
    print("[ffmpeg]", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)


def get_duration(input_path: str) -> float:
    for exe in ("ffprobe", get_ffmpeg().replace("ffmpeg", "ffprobe")):
        try:
            out = subprocess.run(
                [exe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", input_path],
                capture_output=True, text=True,
            )
            if out.returncode == 0 and out.stdout.strip():
                return float(out.stdout.strip())
        except Exception:
            pass
    # 兜底：解析 ffmpeg 输出的 Duration
    out = subprocess.run([get_ffmpeg(), "-i", input_path],
                         stderr=subprocess.PIPE, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", out.stderr)
    if m:
        h, mn, s, ms = (int(x) for x in m.groups())
        return h * 3600 + mn * 60 + s + ms / 100.0
    raise SystemExit(f"[失败] 无法获取视频时长：{input_path}")


def fmt_sec(x: float) -> float:
    return round(float(x), 3)


# ----------------------------------------------------------------------------
# 阶段 A：Silero VAD 静音检测
# ----------------------------------------------------------------------------

def extract_mono_16k(input_path: str, wav_path: str):
    run_ffmpeg([
        "-y", "-i", input_path,
        "-vn", "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        wav_path,
    ])


def detect_speech(input_path: str, params: dict, work: str) -> list:
    """返回 speech intervals（秒）。依赖 silero-vad / torch / soundfile。"""
    try:
        import numpy as np
        import soundfile as sf
        import torch
        from silero_vad import load_silero_vad, get_speech_timestamps
    except ImportError as e:
        raise SystemExit(
            f"[缺失依赖] 静音检测需要 silero-vad / torch / soundfile：{e}\n"
            "请安装：pip install silero-vad torch soundfile\n"
            "（本脚本不静默回退；缺依赖时请去掉冗余检测或人工粗剪）"
        )
    vad = params.get("vad", {})
    wav_path = os.path.join(work, "_vad_tmp.wav")
    extract_mono_16k(input_path, wav_path)
    audio, _ = sf.read(wav_path, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    wav = torch.from_numpy(audio)
    model = load_silero_vad()
    ts = get_speech_timestamps(
        wav, model, sampling_rate=16000,
        threshold=vad.get("threshold", 0.5),
        min_speech_duration_ms=int(vad.get("minSpeechSec", 0.25) * 1000),
        min_silence_duration_ms=int(vad.get("maxSilenceSec", 0.5) * 1000),
        speech_pad_ms=int(vad.get("speechPadSec", 0.10) * 1000),
        return_seconds=True,
    )
    return [{"startSec": fmt_sec(t["start"]), "endSec": fmt_sec(t["end"])} for t in ts]


def derive_silence(speech: list, duration: float, params: dict) -> list:
    """由 speech 反推「无效空白」区间：speech 两侧留 padding 后取补集，
    仅保留时长 >= deadAirThresholdSec 的静音段。"""
    sil = params.get("silence", {})
    dead = sil.get("deadAirThresholdSec", 1.8)
    pad = sil.get("edgePaddingSec", 0.15)
    keep = []
    for s in speech:
        keep.append((max(0.0, s["startSec"] - pad), min(duration, s["endSec"] + pad)))
    keep.sort()
    merged = []
    for a, b in keep:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append([a, b])
    out = []
    prev = 0.0
    for a, b in merged:
        if a - prev >= dead:
            out.append({
                "startSec": fmt_sec(prev), "endSec": fmt_sec(a),
                "durationSec": fmt_sec(a - prev), "classification": "dead_air",
            })
        prev = b
    if duration - prev >= dead:
        out.append({
            "startSec": fmt_sec(prev), "endSec": fmt_sec(duration),
            "durationSec": fmt_sec(duration - prev), "classification": "dead_air",
        })
    return out


# ----------------------------------------------------------------------------
# 阶段 B：转写解析 + 文本嵌入冗余检测
# ----------------------------------------------------------------------------

_TS = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})"
)


def _to_sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(str(ms).ljust(3, "0")) / 1000.0


def _parse_srt_vtt(text: str) -> list:
    blocks = re.split(r"\n\s*\n", text.strip())
    out = []
    for i, blk in enumerate(blocks):
        m = _TS.search(blk)
        if not m:
            continue
        g = m.groups()
        start = _to_sec(*g[:4])
        end = _to_sec(*g[4:])
        lines = [l.strip() for l in blk.splitlines()
                 if l.strip() and not _TS.search(l) and not l.strip().isdigit()]
        out.append({
            "id": f"seg_{i:03d}", "startSec": fmt_sec(start),
            "endSec": fmt_sec(end), "text": " ".join(lines),
        })
    return out


def parse_transcript(path: str) -> list:
    """读取 SRT / VTT / JSON 转写，返回按源视频时间戳对齐的分段列表。
    复用仓库既有「读取既有字幕」约定（参见 scripts/subtitle_voiceover.py）。"""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        segs = data if isinstance(data, list) else data.get(
            "segments", data.get("transcriptSegments", []))
        out = []
        for i, s in enumerate(segs):
            start = float(s.get("start", s.get("startSec", 0)))
            end = float(s.get("end", s.get("endSec", 0)))
            out.append({
                "id": s.get("id", f"seg_{i:03d}"),
                "startSec": fmt_sec(start), "endSec": fmt_sec(end),
                "text": s.get("text", ""),
            })
        return out
    return _parse_srt_vtt(p.read_text(encoding="utf-8", errors="ignore"))


def analyze_redundancy(segments: list, params: dict) -> list:
    """滑动窗口 + 全局近邻，计算相邻/非相邻段的嵌入余弦相似度。"""
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise SystemExit(
            f"[缺失依赖] 冗余检测需要 sentence-transformers：{e}\n"
            "请安装：pip install sentence-transformers"
        )
    rp = params.get("redundancy", {})
    model = SentenceTransformer(rp.get("embedder", "paraphrase-multilingual-MiniLM-L12-v2"))
    emb = model.encode([s["text"] for s in segments],
                       convert_to_numpy=True, normalize_embeddings=True)
    sim_threshold = rp.get("simThreshold", 0.86)
    window = rp.get("windowSec", 45)
    n = len(segments)
    seen = set()
    pairs = []

    def consider(i, j):
        key = tuple(sorted((i, j)))
        if key in seen:
            return
        seen.add(key)
        sim = float(np.dot(emb[i], emb[j]))
        if sim < sim_threshold:
            return
        a, b = segments[i], segments[j]
        da, db = (a, b) if (b["endSec"] - b["startSec"]) <= (a["endSec"] - a["startSec"]) else (b, a)
        pairs.append({
            "a": a["id"], "b": b["id"], "similarity": fmt_sec(sim),
            "action": "drop", "dropTarget": da["id"], "reason": "near_duplicate_text",
        })

    # 滑动窗口（时间相邻）
    for i in range(n):
        j = i + 1
        while j < n and segments[j]["startSec"] - segments[i]["startSec"] <= window:
            consider(i, j)
            j += 1
    # 全局近邻（捕捉非相邻重复）
    for i in range(n):
        for j in range(i + 1, n):
            consider(i, j)
    return pairs


# ----------------------------------------------------------------------------
# 阶段 C：合并区间 + 生成 cut_plan.json
# ----------------------------------------------------------------------------

def merge_intervals(intervals: list) -> list:
    iv = sorted((max(0.0, i["startSec"]), i["endSec"]) for i in intervals)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def build_plan(source, params, silence, redundancy_pairs, segments) -> dict:
    duration = source["durationSec"]
    remove = []
    for s in silence:
        remove.append({"startSec": s["startSec"], "endSec": s["endSec"],
                       "source": "silence", "confidence": 0.95, "note": "dead air"})
    seg_by_id = {s["id"]: s for s in segments}
    for idx, p in enumerate(redundancy_pairs):
        tgt = seg_by_id.get(p["dropTarget"])
        if tgt:
            remove.append({"startSec": tgt["startSec"], "endSec": tgt["endSec"],
                           "source": "redundancy", "link": f"redundancyPairs[{idx}]",
                           "confidence": p["similarity"]})
    merged = merge_intervals(remove)
    keep = []
    prev = 0.0
    for a, b in merged:
        if a > prev:
            keep.append({"startSec": fmt_sec(prev), "endSec": fmt_sec(a)})
        prev = b
    if duration > prev:
        keep.append({"startSec": fmt_sec(prev), "endSec": fmt_sec(duration)})

    sil_rem = sum(s["durationSec"] for s in silence)
    red_rem = sum(
        (seg_by_id[p["dropTarget"]]["endSec"] - seg_by_id[p["dropTarget"]]["startSec"])
        for p in redundancy_pairs if p["dropTarget"] in seg_by_id)
    removed = sum(b - a for a, b in merged)

    return {
        "schemaVersion": "1.0.0",
        "generatedAt": __import__("datetime").datetime.now().astimezone().isoformat(),
        "source": source,
        "params": params,
        "silenceIntervals": silence,
        "transcriptSegments": [{"id": s["id"], "startSec": s["startSec"],
                                "endSec": s["endSec"], "text": s["text"]} for s in segments],
        "redundancyPairs": redundancy_pairs,
        "removeIntervals": remove,
        "keepIntervals": keep,
        "summary": {
            "sourceDurationSec": fmt_sec(duration),
            "removedDurationSec": fmt_sec(removed),
            "keptDurationSec": fmt_sec(duration - removed),
            "removedPct": fmt_sec(removed / duration * 100) if duration else 0,
            "silenceRemovedSec": fmt_sec(sil_rem),
            "redundancyRemovedSec": fmt_sec(red_rem),
            "segmentCount": len(segments),
            "redundantPairs": len(redundancy_pairs),
        },
        "review": {"status": "pending", "autoApproved": False,
                   "approvedBy": None, "approvedAt": None},
    }


# ----------------------------------------------------------------------------
# 阶段 D：执行剪切（ffmpeg filtergraph 重编码 concat）
# ----------------------------------------------------------------------------

def build_filtergraph(keep: list) -> str:
    vparts, aparts, concat_in = [], [], []
    for i, iv in enumerate(keep):
        a, b = iv["startSec"], iv["endSec"]
        vparts.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{i}]")
        aparts.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{i}]")
        concat_in += [f"[v{i}]", f"[a{i}]"]
    n = len(keep)
    fc = ";".join(vparts + aparts + [
        f"{''.join(concat_in)}concat=n={n}:v=1:a=1[outv][outa]"])
    return fc


def validate_plan(plan: dict) -> bool:
    dur = plan["source"]["durationSec"]
    keep = plan["keepIntervals"]
    if not keep:
        print("[校验失败] keepIntervals 为空", file=sys.stderr)
        return False
    prev = 0.0
    for iv in keep:
        if iv["startSec"] < prev - 0.01:
            print("[校验失败] keepIntervals 重叠或乱序", file=sys.stderr)
            return False
        prev = iv["endSec"]
    if abs(prev - dur) > 0.1:
        print(f"[校验失败] keep 未覆盖到视频末尾（{prev} vs {dur}）", file=sys.stderr)
        return False
    if plan["review"]["status"] != "approved":
        print("[校验失败] review.status 未 approved，禁止渲染", file=sys.stderr)
        return False
    return True


def apply_cut(plan: dict, input_path: str, output_path: str):
    out = plan.get("params", {}).get("output", {})
    fc = build_filtergraph(plan["keepIntervals"])
    run_ffmpeg([
        "-i", input_path, "-filter_complex", fc,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", out.get("videoCodec", "libx264"),
        "-crf", str(out.get("crf", 18)),
        "-c:a", out.get("audioCodec", "aac"),
        "-y", output_path,
    ])


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def load_params(path: str | None) -> dict:
    params = json.loads(json.dumps(DEFAULT_PARAMS))
    if path:
        with open(path, "r", encoding="utf-8") as f:
            params.update(json.load(f))
    return params


def cmd_run(args):
    params = load_params(args.params)
    work = args.work
    os.makedirs(work, exist_ok=True)
    duration = get_duration(args.input)
    source = {
        "file": os.path.basename(args.input),
        "durationSec": fmt_sec(duration),
        "fps": None, "hasVideo": True, "hasAudio": True,
        "audioTrack": "0:a:0",
        "note": "源素材原始路径；视频不入 git，仅 cut_plan.json 入库/留存于 work/",
    }
    print(f"[run] 视频时长 {duration:.2f}s，开始 VAD 静音检测 …")
    speech = detect_speech(args.input, params, work)
    silence = derive_silence(speech, duration, params)
    print(f"[run] 检测到 {len(silence)} 段无效空白，合计 "
          f"{sum(s['durationSec'] for s in silence):.2f}s")

    segments, pairs = [], []
    if args.transcript and not args.no_redundancy:
        print(f"[run] 解析转写 {args.transcript} 并做冗余检测 …")
        segments = parse_transcript(args.transcript)
        pairs = analyze_redundancy(segments, params)
        print(f"[run] 命中 {len(pairs)} 对冗余段")
    elif not args.no_redundancy:
        print("[run] 未提供 --transcript，跳过冗余检测（仅静音粗剪）。"
              "如需冗余检测请传入源视频的 SRT/VTT/JSON 转写。")

    plan = build_plan(source, params, silence, pairs, segments)
    out_path = args.output_plan or os.path.join(work, "cut_plan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"[run] 已生成可审阅 cut_plan.json：{out_path}")
    print(f"[run] 将移除 {plan['summary']['removedDurationSec']}s "
          f"({plan['summary']['removedPct']}%)，保留 "
          f"{plan['summary']['keptDurationSec']}s")
    print("[run] 请审阅后把 review.status 改为 approved，再执行 apply。")


def cmd_apply(args):
    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)
    if not args.force and not validate_plan(plan):
        raise SystemExit("[中止] cut_plan 校验未通过，未执行剪切。")
    print(f"[apply] 按 cut_plan 粗剪 {args.input} -> {args.output}")
    apply_cut(plan, args.input, args.output)
    print(f"[apply] 完成：{args.output}")


def main():
    ap = argparse.ArgumentParser(description="访谈类源素材自动粗剪（阶段0·门控）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser("run", help="检测静音+冗余并生成 cut_plan.json")
    rp.add_argument("--input", required=True, help="源视频路径")
    rp.add_argument("--transcript", default=None, help="源视频的 SRT/VTT/JSON 转写（源时间戳对齐）")
    rp.add_argument("--work", default="work", help="中间产物与 cut_plan.json 输出目录")
    rp.add_argument("--no-redundancy", action="store_true", help="仅做静音粗剪，跳过冗余检测")
    rp.add_argument("--params", default=None, help="覆盖默认参数的 JSON 路径")
    rp.add_argument("--output-plan", default=None, help="cut_plan.json 输出路径（默认 work/cut_plan.json）")
    rp.set_defaults(func=cmd_run)

    ap2 = sub.add_parser("apply", help="按 cut_plan.json 执行剪切（需 review 通过）")
    ap2.add_argument("--plan", required=True)
    ap2.add_argument("--input", required=True)
    ap2.add_argument("--output", required=True)
    ap2.add_argument("--force", action="store_true", help="跳过 review/校验闸门（不推荐）")
    ap2.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
