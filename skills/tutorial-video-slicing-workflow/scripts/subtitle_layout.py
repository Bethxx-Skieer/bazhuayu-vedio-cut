#!/usr/bin/env python3
"""Normalize and measure single-line adaptive lower-third subtitles."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DEFAULT_STYLE = Path(__file__).resolve().parents[1] / "assets/subtitle-style-1920x1080.json"
CLOSING_MARKS = "」』”’\"'"


def normalize_subtitle_text(text: str) -> str:
    """Collapse whitespace and remove terminal Chinese/English full stops."""
    normalized = re.sub(r"\s+", " ", text).strip()
    closers = ""
    while normalized and normalized[-1] in CLOSING_MARKS:
        closers = normalized[-1] + closers
        normalized = normalized[:-1].rstrip()
    normalized = re.sub(r"[。.]+$", "", normalized).rstrip()
    return normalized + closers


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2),
        ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
    ]
    for path, index in candidates:
        try:
            return ImageFont.truetype(path, size=size, index=index)
        except OSError:
            continue
    return ImageFont.load_default()


def even_ceil(value: float) -> int:
    result = int(math.ceil(value))
    return result if result % 2 == 0 else result + 1


def cjk_equivalent_length(text: str) -> float:
    total = 0.0
    for char in text:
        if char.isspace():
            total += 0.5
        elif ord(char) < 128:
            total += 0.55
        else:
            total += 1.0
    return total


def measure_subtitle(text: str, style: dict) -> dict:
    clean_text = normalize_subtitle_text(text)
    lower = style["lower_third"]
    single = lower["single_line"]
    rules = style["copy_rules"]
    font = load_font(int(single["font_size"]))
    canvas = Image.new("L", (8, 8))
    draw = ImageDraw.Draw(canvas)
    bounds = draw.textbbox((0, 0), clean_text, font=font)
    text_width = float(bounds[2] - bounds[0])
    max_text_width = float(lower["measurement"]["max_text_width"])
    raw_width = text_width + 2 * float(lower["padding_x"])
    width = even_ceil(max(float(lower["min_width"]), min(raw_width, float(lower["max_width"]))))
    x = int(round((style["master_canvas"]["width"] - width) / 2))
    cjk_length = cjk_equivalent_length(clean_text)
    fits = bool(clean_text) and "\n" not in clean_text and text_width <= max_text_width
    return {
        "original_text": text,
        "text": clean_text,
        "terminal_full_stop_removed": clean_text != re.sub(r"\s+", " ", text).strip(),
        "fits_single_line": fits,
        "recommended_to_split": cjk_length > float(rules["recommended_single_line_cjk_chars"]),
        "overflow_strategy": rules["overflow_strategy"] if not fits else None,
        "cjk_equivalent_length": round(cjk_length, 2),
        "text_width": round(text_width, 2),
        "box": {
            "x": x,
            "y": int(single["y"]),
            "width": width,
            "height": int(single["height"]),
            "bottom_y": int(lower["bottom_y"]),
            "center_x": int(lower["center_x"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", action="append", required=True,
                        help="Subtitle text; repeat for multiple examples")
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 2 when any subtitle cannot fit a single line")
    args = parser.parse_args()
    style = json.loads(args.style.read_text(encoding="utf-8"))
    results = [measure_subtitle(text, style) for text in args.text]
    payload = {"style_version": style["version"], "results": results}
    output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.strict and any(not result["fits_single_line"] for result in results):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
