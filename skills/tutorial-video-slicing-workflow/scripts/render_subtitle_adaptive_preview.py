#!/usr/bin/env python3
"""Render short, medium, and long adaptive single-line subtitle previews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from subtitle_layout import load_font, measure_subtitle, normalize_subtitle_text


SCALE = 2
OUTPUT = (1920, 1080)


def px(value: float) -> int:
    return int(round(value * SCALE))


def rect(box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(px(value) for value in box)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2 if bold else 0),
        ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
    ]
    for path, index in candidates:
        try:
            return ImageFont.truetype(path, size=px(size), index=index)
        except OSError:
            continue
    return ImageFont.load_default()


def rgba(values: list[float]) -> tuple[int, int, int, int]:
    return tuple(int(round(value * 255)) for value in values)


def main() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", type=Path,
                        default=skill_dir / "assets/subtitle-style-1920x1080.json")
    parser.add_argument("--output", type=Path,
                        default=skill_dir / "assets/subtitle-adaptive-preview.png")
    args = parser.parse_args()
    style = json.loads(args.style.read_text(encoding="utf-8"))
    lower = style["lower_third"]
    single = lower["single_line"]

    image = Image.new("RGB", (px(OUTPUT[0]), px(OUTPUT[1])), "#F2F5F8")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text((px(96), px(80)), "单行自适应字幕", font=font(52), fill="#202936")
    draw.text((px(96), px(146)), "无句号 · 不换行 · 背景框随文字长度变化",
              font=font(28, False), fill="#657181")

    examples = [
        ("短字幕", "开始检索。"),
        ("中等字幕", "一句话发起舆情分析。"),
        ("较长字幕", "输入分析对象，就能自动完成检索、清洗和报告交付。"),
    ]
    row_top = 224
    for index, (label, raw_text) in enumerate(examples):
        top = row_top + index * 270
        panel = (96, top, 1824, top + 222)
        draw.rounded_rectangle(rect(panel), radius=px(24), fill="#E5EAF0")
        draw.text((px(130), px(top + 32)), label, font=font(26), fill="#657181")

        measured = measure_subtitle(raw_text, style)
        text = normalize_subtitle_text(raw_text)
        width = measured["box"]["width"]
        x = (OUTPUT[0] - width) / 2
        y = top + 102
        box = (x, y, x + width, y + single["height"])
        draw.rounded_rectangle(rect(box), radius=px(lower["radius"]),
                               fill=rgba(lower["background_rgba"]))
        draw.text((px(OUTPUT[0] / 2), px(y + single["height"] / 2)), text,
                  font=font(single["font_size"]), fill=single["color"], anchor="mm")

    image = image.resize(OUTPUT, Image.Resampling.LANCZOS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
