#!/usr/bin/env python3
"""Render a supersampled preview of the product-demo enhancement style."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SCALE = 2
OUTPUT_SIZE = (1920, 1080)


def px(value: float) -> int:
    return int(round(value * SCALE))


def rect(box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(px(value) for value in box)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2 if bold else 0),
        ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
        ("/System/Library/Fonts/STHeiti Light.ttc", 1),
    ]
    for path, index in candidates:
        try:
            return ImageFont.truetype(path, size=px(size), index=index)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int,
            fill: str | tuple, outline: str | None = None, width: int = 1) -> None:
    draw.rounded_rectangle(rect(box), radius=px(radius), fill=fill,
                           outline=outline, width=px(width))


def draw_text(draw: ImageDraw.ImageDraw, position: tuple[float, float], text: str,
              text_font: ImageFont.FreeTypeFont, fill: str, anchor: str = "la") -> None:
    draw.text((px(position[0]), px(position[1])), text, font=text_font, fill=fill, anchor=anchor)


def centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str,
                  text_font: ImageFont.FreeTypeFont, fill: str) -> None:
    left, top, right, bottom = box
    draw_text(draw, ((left + right) / 2, (top + bottom) / 2), text,
              text_font, fill, anchor="mm")


def text_width(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.FreeTypeFont) -> float:
    bounds = draw.textbbox((0, 0), text, font=text_font)
    return (bounds[2] - bounds[0]) / SCALE


def check_icon(draw: ImageDraw.ImageDraw, center: tuple[float, float], color: str,
               size: int = 24, width: int = 5) -> None:
    x, y = center
    points = [
        (px(x - size * 0.46), px(y - size * 0.01)),
        (px(x - size * 0.12), px(y + size * 0.34)),
        (px(x + size * 0.54), px(y - size * 0.44)),
    ]
    draw.line(points, fill=color, width=px(width), joint="curve")
    radius = px(width / 2)
    for point in (points[0], points[-1]):
        draw.ellipse((point[0] - radius, point[1] - radius,
                      point[0] + radius, point[1] + radius), fill=color)


def document_icon(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(rect(box), radius=px(3), outline=color, width=px(3))
    draw.line(rect((left + 7, top + 11, right - 7, top + 11)), fill=color, width=px(2))
    draw.line(rect((left + 7, top + 20, right - 7, top + 20)), fill=color, width=px(2))


def status_chip(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str,
                fill: str, text_color: str, state: str) -> None:
    rounded(draw, box, 16, fill)
    label_font = font(30, True)
    left, top, right, bottom = box
    center_y = (top + bottom) / 2
    if state == "inactive":
        centered_text(draw, box, label, label_font, text_color)
        return

    icon_width = 24
    gap = 13
    label_width = text_width(draw, label, label_font)
    group_width = icon_width + gap + label_width
    group_left = (left + right - group_width) / 2
    icon_center = (group_left + icon_width / 2, center_y)
    if state == "complete":
        check_icon(draw, icon_center, text_color, 22, 4)
    else:
        radius = 11
        draw.ellipse(rect((icon_center[0] - radius, icon_center[1] - radius,
                           icon_center[0] + radius, icon_center[1] + radius)), fill=text_color)
    draw_text(draw, (group_left + icon_width + gap, center_y), label,
              label_font, text_color, anchor="lm")


def completion_chip(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str,
                    fill: str, text_color: str) -> None:
    rounded(draw, box, 18, fill)
    label_font = font(34, True)
    left, top, right, bottom = box
    center_y = (top + bottom) / 2
    icon_width = 28
    gap = 14
    label_width = text_width(draw, label, label_font)
    group_width = icon_width + gap + label_width
    group_left = (left + right - group_width) / 2
    check_icon(draw, (group_left + icon_width / 2, center_y), text_color, 26, 5)
    draw_text(draw, (group_left + icon_width + gap, center_y), label,
              label_font, text_color, anchor="lm")


def main() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", type=Path,
                        default=skill_dir / "assets/enhancement-styles/product-demo-clean-1920x1080.json")
    parser.add_argument("--subtitle-style", type=Path,
                        default=skill_dir / "assets/subtitle-style-1920x1080.json")
    parser.add_argument("--output", type=Path,
                        default=skill_dir / "assets/enhancement-styles/product-demo-clean-preview.png")
    args = parser.parse_args()
    style = json.loads(args.style.read_text(encoding="utf-8"))
    subtitle_style = json.loads(args.subtitle_style.read_text(encoding="utf-8"))
    palette = style["palette"]

    image = Image.new("RGB", (px(OUTPUT_SIZE[0]), px(OUTPUT_SIZE[1])), "#F3F6F9")
    draw = ImageDraw.Draw(image, "RGBA")

    rounded(draw, (100, 88, 1820, 980), 28, "#FFFFFF", "#DDE3EA", 3)
    rounded(draw, (100, 88, 1820, 178), 28, "#E9EDF2")
    draw.rectangle(rect((100, 150, 1820, 178)), fill="#E9EDF2")
    for x, color in [(142, "#FF5F57"), (180, "#FFBD2E"), (218, "#28C840")]:
        draw.ellipse(rect((x - 10, 123, x + 10, 143)), fill=color)
    draw_text(draw, (286, 134), "产品演示 · 产品演示增强样式",
              font(30, True), palette["charcoal"], anchor="lm")

    rounded(draw, (134, 210, 430, 914), 18, "#F5F7FA")
    draw_text(draw, (184, 276), "新建任务", font(34, True), palette["charcoal"], anchor="lm")
    for index, item in enumerate(["技能市场", "自动化", "资料库", "项目"]):
        draw_text(draw, (186, 350 + index * 84), item, font(28), palette["gray"], anchor="lm")

    draw_text(draw, (512, 258), "一句话发起任务", font(48, True), palette["charcoal"], anchor="lm")
    input_box = (512, 314, 1640, 432)
    rounded(draw, input_box, 20, "#FFFFFF", palette["blue"], 4)
    draw_text(draw, (558, 373), "分析新品上市后的全网公开口碑", font(36), palette["charcoal"], anchor="lm")
    send_box = (1486, 334, 1608, 412)
    rounded(draw, send_box, 18, palette["blue"])
    centered_text(draw, send_box, "发送", font(30, True), palette["white"])

    draw.ellipse(rect((1570, 367, 1638, 435)), outline=palette["blue"], width=px(4))
    draw.ellipse(rect((1596, 393, 1612, 409)), fill=palette["blue"])

    labels = [("检索", "complete"), ("清洗", "complete"), ("分析", "active"), ("生成", "inactive")]
    x = 554
    for label, state in labels:
        width = 174
        fill = palette["green_deep"] if state == "complete" else (palette["blue"] if state == "active" else "#202936D9")
        status_chip(draw, (x, 500, x + width, 564), label, fill, palette["white"], state)
        x += width + 16

    result_box = (512, 622, 1640, 826)
    rounded(draw, result_box, 20, "#FFFFFF", palette["green"], 4)
    cards = [
        (546, 658, 864, 790, "分析报告"),
        (902, 658, 1220, 790, "Excel 数据包"),
        (1258, 658, 1576, 790, "HTML 报告"),
    ]
    for left, top, right, bottom, label in cards:
        rounded(draw, (left, top, right, bottom), 16, "#F7FAFC", "#DDE3EA", 2)
        document_icon(draw, (left + 30, top + 35, left + 58, top + 70), palette["green_deep"])
        draw_text(draw, (left + 78, (top + bottom) / 2), label,
                  font(30, True), palette["charcoal"], anchor="lm")

    completion_chip(draw, (1430, 212, 1744, 280), "成果已交付",
                    palette["green_deep"], palette["white"])

    caption = "输入一句话，就能完成分析并拿到完整成果"
    lower = subtitle_style["lower_third"]
    single = lower["single_line"]
    caption_font = font(single["font_size"], True)
    caption_width = text_width(draw, caption, caption_font)
    box_width = int(math.ceil(caption_width + 2 * lower["padding_x"]))
    box_width = max(lower["min_width"], min(box_width, lower["max_width"]))
    if box_width % 2:
        box_width += 1
    box_x = (OUTPUT_SIZE[0] - box_width) / 2
    subtitle_box = (box_x, single["y"], box_x + box_width, single["y"] + single["height"])
    rounded(draw, subtitle_box, lower["radius"], (16, 16, 16, 220))
    centered_text(draw, subtitle_box, caption, caption_font, palette["white"])

    image = image.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
