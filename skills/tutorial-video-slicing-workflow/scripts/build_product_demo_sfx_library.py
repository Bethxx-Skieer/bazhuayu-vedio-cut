#!/usr/bin/env python3
"""Generate the reusable product-demo UI sound library.

The sounds are intentionally synthetic, dry, short, and license-free. They are
designed to sit under narration and to be placed from a cue sheet rather than
baked into a fixed template timeline.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import wave
from array import array
from pathlib import Path


SR = 48_000


def silence(seconds: float) -> list[float]:
    return [0.0] * int(seconds * SR)


def envelope(length: int, attack: float = 0.03, decay: float = 7.0) -> list[float]:
    values: list[float] = []
    for i in range(length):
        x = i / max(1, length - 1)
        fade_in = min(1.0, x / max(attack, 1e-4))
        values.append(fade_in * math.exp(-decay * x))
    return values


def normalize_peak(samples: list[float], target_dbfs: float) -> list[float]:
    peak = max((abs(v) for v in samples), default=0.0)
    if peak == 0:
        return samples
    target = 10 ** (target_dbfs / 20.0)
    gain = target / peak
    return [v * gain for v in samples]


def mix(parts: list[tuple[float, list[float], float]]) -> list[float]:
    length = max((int(offset * SR) + len(sound) for offset, sound, _ in parts), default=0)
    out = [0.0] * length
    for offset, sound, gain in parts:
        start = int(offset * SR)
        for index, value in enumerate(sound):
            out[start + index] += value * gain
    return out


def sine_tone(freq: float, duration: float, harmonic: float = 0.14, decay: float = 7.0) -> list[float]:
    n = int(duration * SR)
    env = envelope(n, 0.04, decay)
    return [
        (math.sin(2 * math.pi * freq * i / SR)
         + harmonic * math.sin(2 * math.pi * freq * 2 * i / SR)) * env[i]
        for i in range(n)
    ]


def chirp(freq0: float, freq1: float, duration: float, decay: float = 5.5) -> list[float]:
    n = int(duration * SR)
    env = envelope(n, 0.05, decay)
    out: list[float] = []
    for i in range(n):
        t = i / SR
        rate = (freq1 - freq0) / max(duration, 1e-5)
        phase = 2 * math.pi * (freq0 * t + 0.5 * rate * t * t)
        out.append((math.sin(phase) + 0.10 * math.sin(2 * phase)) * env[i])
    return out


def filtered_noise(seed: int, duration: float, smooth: float = 0.16) -> list[float]:
    rng = random.Random(seed)
    n = int(duration * SR)
    previous = 0.0
    out: list[float] = []
    for _ in range(n):
        raw = rng.uniform(-1.0, 1.0)
        previous = previous * (1.0 - smooth) + raw * smooth
        out.append(previous)
    return out


def click(seed: int, pitch: float) -> list[float]:
    duration = 0.085
    noise = filtered_noise(seed, duration, 0.35)
    tone = sine_tone(pitch, duration, 0.04, 16.0)
    env = envelope(len(noise), 0.008, 15.0)
    return [(0.62 * noise[i] + 0.38 * tone[i]) * env[i] for i in range(len(noise))]


def keypress(seed: int, pitch: float) -> list[float]:
    duration = 0.052
    noise = filtered_noise(seed, duration, 0.48)
    tone = sine_tone(pitch, duration, 0.05, 13.0)
    env = envelope(len(noise), 0.012, 13.0)
    return [(0.72 * noise[i] + 0.28 * tone[i]) * env[i] for i in range(len(noise))]


def whoosh(seed: int, duration: float, rising: bool = True) -> list[float]:
    noise = filtered_noise(seed, duration, 0.05)
    n = len(noise)
    out: list[float] = []
    for i, value in enumerate(noise):
        x = i / max(1, n - 1)
        arch = math.sin(math.pi * x) ** 1.7
        direction = 0.30 + 0.70 * (x if rising else 1.0 - x)
        out.append(value * arch * direction)
    return out


def chime(notes: list[tuple[float, float, float]], duration: float = 0.62) -> list[float]:
    parts: list[tuple[float, list[float], float]] = []
    for offset, frequency, gain in notes:
        parts.append((offset, sine_tone(frequency, duration - offset, 0.17, 6.8), gain))
    return mix(parts)


def soft_thud(seed: int, freq: float = 150.0) -> list[float]:
    duration = 0.22
    noise = filtered_noise(seed, duration, 0.08)
    tone = sine_tone(freq, duration, 0.04, 9.0)
    env = envelope(len(noise), 0.02, 10.0)
    return [(0.30 * noise[i] + 0.70 * tone[i]) * env[i] for i in range(len(noise))]


def write_wav(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array("h", (int(max(-1.0, min(1.0, value)) * 32767) for value in samples))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())


def build_specs() -> list[dict]:
    specs: list[dict] = []

    def add(asset_id: str, relpath: str, event: str, description: str,
            target_dbfs: float, samples: list[float]) -> None:
        specs.append({
            "id": asset_id,
            "path": relpath,
            "event": event,
            "description": description,
            "target_peak_dbfs": target_dbfs,
            "samples": normalize_peak(samples, target_dbfs),
        })

    for index, pitch in enumerate([1380, 1540, 1710], start=1):
        add(f"ui.click.soft.{index:02d}", f"ui/click-soft-{index:02d}.wav", "ui_click",
            "关键真实点击；多个点击时轮换使用", -18.0, click(100 + index, pitch))

    for index, pitch in enumerate([1080, 1160, 1240, 1320, 1410, 1500], start=1):
        add(f"input.keypress.soft.{index:02d}", f"input/keypress-soft-{index:02d}.wav", "typing",
            "单次键盘音变体；只跟随真实字符出现", -24.0, keypress(200 + index, pitch))
    add("input.ime.confirm", "input/ime-confirm.wav", "ime_confirm",
        "中文输入法转换或关键词输入完成", -20.0, chirp(620, 880, 0.13, 8.0))

    add("navigation.page.enter", "navigation/page-enter.wav", "page_enter",
        "重要页面或章节进入", -22.0, whoosh(301, 0.34, True))
    add("navigation.tab.switch", "navigation/tab-switch.wav", "tab_switch",
        "标签页或视图切换", -20.0, chirp(720, 910, 0.12, 8.0))
    add("navigation.menu.open", "navigation/menu-open.wav", "menu_open",
        "菜单、抽屉或弹层展开", -22.0, whoosh(302, 0.22, True))

    add("task.start", "task/task-start.wav", "task_start",
        "任务提交并开始响应", -18.0, chime([(0.00, 440, 0.72), (0.07, 554, 0.58)], 0.34))
    add("task.progress.pulse.01", "task/progress-pulse-01.wav", "progress_pulse",
        "等待超过三秒时的稀疏进度提示", -24.0, sine_tone(420, 0.19, 0.10, 8.5))
    add("task.progress.pulse.02", "task/progress-pulse-02.wav", "progress_pulse",
        "等待超过三秒时的稀疏进度提示变体", -24.0, sine_tone(510, 0.19, 0.10, 8.5))

    stage_data = [
        ("search", 580, "检索"), ("collect", 650, "采集"), ("clean", 720, "清洗"),
        ("validate", 790, "校验"), ("analyze", 860, "分析"),
        ("generate", 940, "生成"), ("export", 1020, "导出"),
    ]
    for index, (name, freq, label) in enumerate(stage_data):
        add(f"stage.{name}", f"stage/{name}.wav", f"stage_{name}",
            f"执行阶段确认：{label}", -19.0 + index * 0.45, chirp(freq, freq + 90, 0.14, 7.5))

    add("result.reveal.soft", "result/result-reveal-soft.wav", "result_reveal",
        "中间结果或报告首次稳定出现", -18.0, chime([(0.00, 660, 0.72), (0.06, 830, 0.50)], 0.33))
    add("result.file.created", "result/file-created.wav", "file_created",
        "文件、报告或数据包生成", -17.0, chime([(0.00, 520, 0.68), (0.08, 690, 0.56)], 0.40))
    add("result.save.success", "result/save-success.wav", "save_success",
        "保存完成的微反馈", -20.0, chirp(740, 880, 0.11, 9.0))
    add("result.copy.success", "result/copy-success.wav", "copy_success",
        "复制成功的微反馈", -21.0, chirp(820, 960, 0.09, 10.0))

    add("file.upload", "file/upload.wav", "upload",
        "上传开始或完成", -18.0, chirp(420, 940, 0.28, 6.0))
    add("file.download", "file/download.wav", "download",
        "下载开始或完成", -18.0, chirp(940, 420, 0.28, 6.0))
    add("system.install.success", "system/install-success.wav", "install_success",
        "Skill、插件或组件安装成功", -16.0,
        chime([(0.00, 523.25, 0.70), (0.08, 659.25, 0.58)], 0.46))
    add("system.connect.success", "system/connect-success.wav", "connect_success",
        "数据库、服务或工具连接成功", -16.0,
        chime([(0.00, 440.00, 0.64), (0.07, 554.37, 0.60), (0.14, 659.25, 0.46)], 0.52))

    add("complete.task", "complete/task-complete.wav", "task_complete",
        "普通任务完成；一条视频最多使用一次或两次", -15.0,
        chime([(0.00, 523.25, 0.72), (0.08, 659.25, 0.58), (0.16, 783.99, 0.48)], 0.58))
    add("complete.final.delivery", "complete/final-delivery.wav", "final_delivery",
        "最终成果交付；全片最高层级完成反馈", -12.5,
        chime([(0.00, 523.25, 0.78), (0.09, 659.25, 0.68), (0.18, 783.99, 0.58)], 0.72))

    add("feedback.warning", "feedback/warning.wav", "warning",
        "需要注意但不阻断流程", -16.0, chime([(0.00, 440, 0.70), (0.10, 392, 0.54)], 0.45))
    add("feedback.error", "feedback/error.wav", "error",
        "失败或阻断；避免刺耳报警", -14.0, soft_thud(701, 135.0))
    add("feedback.retry", "feedback/retry.wav", "retry",
        "重新尝试或恢复执行", -18.0, chirp(380, 700, 0.25, 6.5))

    add("transition.chapter.whoosh", "transition/chapter-whoosh.wav", "chapter_enter",
        "章节卡稳定后轻扫入", -22.0, whoosh(801, 0.40, True))
    return specs


def build_library(out_dir: Path) -> None:
    specs = build_specs()
    manifest_assets: list[dict] = []
    audition: list[float] = silence(0.5)
    audition_order: list[str] = []

    for spec in specs:
        output = out_dir / spec["path"]
        write_wav(output, spec["samples"])
        duration = len(spec["samples"]) / SR
        manifest_assets.append({key: value for key, value in spec.items() if key != "samples"} | {
            "duration_seconds": round(duration, 4),
        })
        audition.extend(spec["samples"])
        audition.extend(silence(0.34))
        audition_order.append(spec["id"])

    write_wav(out_dir / "audition.wav", normalize_peak(audition, -3.0))
    manifest = {
        "schema_version": "1.0",
        "library_id": "product-demo-clean",
        "sample_rate_hz": SR,
        "channels": 1,
        "sample_format": "pcm_s16le",
        "default_intensity": "clear",
        "intensity_gain_db": {"subtle": -4.0, "clear": 0.0, "promo": 3.0},
        "rules": {
            "human_wow": "forbidden",
            "background_music_default": "off",
            "voice_priority": True,
            "final_mix_peak_ceiling_dbfs": -1.0,
        },
        "audition_order": audition_order,
        "assets": manifest_assets,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(specs)} sounds in {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    default_out = Path(__file__).resolve().parents[1] / "assets/sfx/product-demo-clean"
    parser.add_argument("--out-dir", type=Path, default=default_out)
    args = parser.parse_args()
    build_library(args.out_dir.resolve())


if __name__ == "__main__":
    main()
