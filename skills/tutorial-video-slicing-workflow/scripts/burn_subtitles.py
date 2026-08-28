#!/usr/bin/env python3
"""Burn the locked 16:9 subtitle style into a review or master video."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STYLE = SKILL_ROOT / "assets/subtitle-style-1920x1080.json"
LAYOUT_SCRIPT = SKILL_ROOT / "scripts/subtitle_layout.py"


def parse_time(value: str) -> float:
    hour, minute, second = value.replace(",", ".").split(":")
    return int(hour) * 3600 + int(minute) * 60 + float(second)


def parse_srt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    cues: list[dict] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        position = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if position is None:
            continue
        start, end = [item.strip() for item in lines[position].split("-->")]
        cues.append({
            "start": parse_time(start),
            "end": parse_time(end),
            "text": " ".join(lines[position + 1 :]),
        })
    if not cues:
        raise ValueError("No readable SRT cues found")
    return cues


def locate_ffmpeg(explicit: str | None) -> str:
    if explicit:
        return explicit
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("ffmpeg not found; install ffmpeg or imageio-ffmpeg") from exc


def probe_dimensions(ffmpeg: str, video: Path) -> tuple[int, int]:
    result = subprocess.run([ffmpeg, "-i", str(video)], text=True, capture_output=True)
    match = re.search(r"Video:.*?\b(\d{3,5})x(\d{3,5})\b", result.stderr)
    if not match:
        raise RuntimeError(f"Could not read video dimensions: {video}")
    return int(match.group(1)), int(match.group(2))


def load_layout_module():
    spec = importlib.util.spec_from_file_location("subtitle_layout", LAYOUT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load layout script: {LAYOUT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_font(explicit: Path | None, explicit_index: int | None) -> tuple[Path, int, str]:
    candidates = [
        (explicit, 0 if explicit_index is None else explicit_index, "explicit"),
        (Path("/System/Library/Fonts/Hiragino Sans GB.ttc"), 2, "Hiragino Sans GB W6"),
        (Path("/System/Library/Fonts/STHeiti Medium.ttc"), 1, "Heiti SC Medium"),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"), 0, "Noto Sans CJK Bold"),
    ]
    for candidate, index, label in candidates:
        if not candidate or not candidate.exists():
            continue
        try:
            ImageFont.truetype(str(candidate), size=48, index=index)
            return candidate, index, label
        except OSError:
            continue
    raise FileNotFoundError("No supported full-CJK font found; pass --font-file")


def escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def rgba_to_hex(values: list[float]) -> str:
    red, green, blue, alpha = values
    return f"0x{round(red*255):02X}{round(green*255):02X}{round(blue*255):02X}{round(alpha*255):02X}"


def ffmpeg_movie_escape(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_caption_card(
    path: Path,
    text: str,
    width: int,
    height: int,
    radius: int,
    background_rgba: list[float],
    font_path: Path,
    font_index: int,
    font_size: int,
) -> None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    red, green, blue, alpha = background_rgba
    fill = (round(red * 255), round(green * 255), round(blue * 255), round(alpha * 255))
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=fill)
    font = ImageFont.truetype(str(font_path), size=font_size, index=font_index)
    bounds = draw.textbbox((0, 0), text, font=font, stroke_width=0)
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    x = (width - text_width) / 2 - bounds[0]
    y = (height - text_height) / 2 - bounds[1]
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255), stroke_width=0)
    image.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("subtitle", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    parser.add_argument("--allow-style-override", action="store_true")
    parser.add_argument("--font-file", type=Path)
    parser.add_argument("--font-index", type=int)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--preset", default="fast")
    parser.add_argument("--crf", type=int, default=22)
    args = parser.parse_args()

    style_path = args.style.resolve()
    if style_path != DEFAULT_STYLE.resolve() and not args.allow_style_override:
        raise ValueError("Alternate subtitle style requires --allow-style-override and explicit user approval")
    style_bytes = style_path.read_bytes()
    style = json.loads(style_bytes.decode("utf-8"))
    ffmpeg = locate_ffmpeg(args.ffmpeg)
    width, height = probe_dimensions(ffmpeg, args.video.resolve())
    master = style["master_canvas"]
    if abs(width / height - master["width"] / master["height"]) > 0.002:
        raise ValueError("Subtitle burn-in requires a standardized 16:9 video")
    scale = width / float(master["width"])
    font, font_index, font_face = resolve_font(args.font_file, args.font_index)
    layout = load_layout_module()
    cues = parse_srt(args.subtitle.resolve())
    report_cues: list[dict] = []
    caption_specs: list[dict] = []
    for index, cue in enumerate(cues, 1):
        measured = layout.measure_subtitle(cue["text"], style)
        measured.update({"index": index, "start": cue["start"], "end": cue["end"]})
        report_cues.append(measured)
        if not measured["fits_single_line"]:
            continue
        box = measured["box"]
        x = round(box["x"] * scale)
        y = round(box["y"] * scale)
        box_width = round(box["width"] * scale)
        box_height = round(box["height"] * scale)
        font_size = round(style["lower_third"]["single_line"]["font_size"] * scale)
        caption_specs.append({
            "index": index,
            "start": cue["start"],
            "end": cue["end"],
            "text": measured["text"],
            "x": x,
            "y": y,
            "width": box_width,
            "height": box_height,
            "font_size": font_size,
            "radius": max(1, round(style["lower_third"]["radius"] * scale)),
        })

    errors = [item for item in report_cues if not item["fits_single_line"]]
    payload = {
        "status": "ok" if not errors else "overflow",
        "style_file": str(style_path),
        "style_sha256": hashlib.sha256(style_bytes).hexdigest(),
        "style_version": style.get("version"),
        "background_rgba": style["lower_third"]["background_rgba"],
        "font_color": style["lower_third"]["single_line"]["color"],
        "font_file": str(font),
        "font_index": font_index,
        "font_face": font_face,
        "font_weight_strategy": "native CJK semibold/bold face; no synthetic stroke",
        "synthetic_stroke_width": 0,
        "renderer_mode": "pillow_rounded_rgba_card",
        "background_shape": "rounded_rectangle",
        "single_line_required": True,
        "max_box_width_ratio": style["lower_third"]["max_width"] / style["master_canvas"]["width"],
        "video_dimensions": [width, height],
        "errors": [f"Cue {item['index']} exceeds one line" for item in errors],
        "cues": report_cues,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        print(f"Subtitle overflow detected; see {args.report}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="subtitle-cards-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        graph: list[str] = ["[0:v]format=rgba[v0]"]
        previous = "v0"
        for spec in caption_specs:
            card = temp_dir / f"cue-{spec['index']:04d}.png"
            render_caption_card(
                card,
                spec["text"],
                spec["width"],
                spec["height"],
                spec["radius"],
                style["lower_third"]["background_rgba"],
                font,
                font_index,
                spec["font_size"],
            )
            card_label = f"card{spec['index']}"
            next_label = f"v{spec['index']}"
            enable = f"between(t,{spec['start']:.3f},{spec['end']:.3f})"
            graph.append(f"movie='{ffmpeg_movie_escape(card)}',format=rgba[{card_label}]")
            graph.append(
                f"[{previous}][{card_label}]overlay=x={spec['x']}:y={spec['y']}:"
                f"enable='{enable}':eof_action=repeat[{next_label}]"
            )
            previous = next_label
        graph.append(f"[{previous}]format=yuv420p[vout]")
        filter_path = temp_dir / "subtitle-filter.txt"
        filter_path.write_text(";".join(graph), encoding="utf-8")
        command = [
            ffmpeg, "-y", "-i", str(args.video), "-filter_complex_script", str(filter_path),
            "-map", "[vout]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-c:a", "copy", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(args.output),
        ]
        result = subprocess.run(command)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
