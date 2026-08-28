#!/usr/bin/env python3
"""Validate that subtitle style and Chinese narration voice did not drift."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STYLE = SKILL_ROOT / "assets/subtitle-style-1920x1080.json"
DEFAULT_VOICE_PROFILE = SKILL_ROOT / "assets/voiceover-profile-zh-CN.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subtitle_report", type=Path)
    parser.add_argument("voiceover_report", type=Path)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    parser.add_argument("--voice-profile", type=Path, default=DEFAULT_VOICE_PROFILE)
    parser.add_argument("--allow-voice-override", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    subtitle = json.loads(args.subtitle_report.read_text(encoding="utf-8"))
    voiceover = json.loads(args.voiceover_report.read_text(encoding="utf-8"))
    style_bytes = args.style.read_bytes()
    style = json.loads(style_bytes.decode("utf-8"))
    profile = json.loads(args.voice_profile.read_text(encoding="utf-8"))
    errors: list[str] = []
    if subtitle.get("status") != "ok":
        errors.append("subtitle report status is not ok")
    if subtitle.get("style_sha256") != hashlib.sha256(style_bytes).hexdigest():
        errors.append("subtitle style hash does not match the locked style")
    if subtitle.get("background_rgba") != style["lower_third"]["background_rgba"]:
        errors.append("subtitle background differs from the locked style")
    if subtitle.get("font_color") != style["lower_third"]["single_line"]["color"]:
        errors.append("subtitle font color differs from the locked style")
    if subtitle.get("renderer_mode") != "pillow_rounded_rgba_card":
        errors.append("subtitle renderer must use rounded RGBA caption cards")
    if subtitle.get("background_shape") != "rounded_rectangle":
        errors.append("subtitle background must be a rounded rectangle")
    if subtitle.get("synthetic_stroke_width") != 0:
        errors.append("subtitle text must use a native bold face without synthetic white stroke")
    if subtitle.get("single_line_required") is not True:
        errors.append("social captions must be rendered as single-line cues")
    expected_ratio = style["lower_third"]["max_width"] / style["master_canvas"]["width"]
    if abs(float(subtitle.get("max_box_width_ratio", -1)) - expected_ratio) > 0.001:
        errors.append("subtitle maximum width ratio differs from the locked social caption style")
    if any(not cue.get("fits_single_line") for cue in subtitle.get("cues", [])):
        errors.append("subtitle report contains a multi-line or overflowing cue")
    if any(cue.get("box", {}).get("width", 10**9) > style["lower_third"]["max_width"] for cue in subtitle.get("cues", [])):
        errors.append("subtitle report contains a box wider than the social caption limit")
    if voiceover.get("status") != "ok":
        errors.append("voiceover report status is not ok")
    if not args.allow_voice_override and voiceover.get("voice") != profile["voice"]:
        errors.append(f"voice must be {profile['voice']!r}, got {voiceover.get('voice')!r}")
    if not args.allow_voice_override and voiceover.get("rate") != profile["rate"]:
        errors.append(f"voice rate must be {profile['rate']}, got {voiceover.get('rate')}")
    if any(cue.get("status") == "overrun" for cue in voiceover.get("cues", [])):
        errors.append("voiceover contains overrun cues")
    result = {
        "status": "ok" if not errors else "failed",
        "subtitle_report": str(args.subtitle_report.resolve()),
        "voiceover_report": str(args.voiceover_report.resolve()),
        "expected_voice": profile["voice"],
        "actual_voice": voiceover.get("voice"),
        "errors": errors,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
