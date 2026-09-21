#!/usr/bin/env python3
"""Probe, decode and extract scene-boundary frames for a rendered explainer."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from validate_project import validate_manifest


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, capture_output=capture)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("video", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print(json.dumps({"status": "error", "errors": ["ffmpeg and ffprobe are required"]}, ensure_ascii=False, indent=2))
        return 1
    if not args.video.exists():
        print(json.dumps({"status": "error", "errors": [f"video not found: {args.video}"]}, ensure_ascii=False, indent=2))
        return 1

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest_report = validate_manifest(manifest, args.manifest.resolve())
    errors = list(manifest_report["errors"])
    warnings = list(manifest_report["warnings"])

    probe = run([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(args.video)
    ])
    if probe.returncode != 0:
        errors.append(f"ffprobe failed: {probe.stderr.strip()}")
        media = {}
    else:
        media = json.loads(probe.stdout)

    streams = media.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    fmt = manifest.get("format", {})
    if not video_stream:
        errors.append("render has no video stream")
    else:
        if video_stream.get("width") != fmt.get("width") or video_stream.get("height") != fmt.get("height"):
            errors.append("render dimensions do not match manifest")
        rate = video_stream.get("avg_frame_rate", "0/1")
        numerator, denominator = (float(part) for part in rate.split("/"))
        actual_fps = numerator / denominator if denominator else 0
        if abs(actual_fps - float(fmt.get("fps", 0))) > 0.01:
            errors.append(f"render fps {actual_fps} does not match manifest")
    if manifest.get("voiceover", {}).get("locked") and not audio_stream:
        errors.append("final render has no audio stream")

    expected_duration = max(
        (float(scene["startSec"]) + float(scene["durationSec"]) for scene in manifest.get("scenes", [])),
        default=0,
    )
    actual_duration = float((media.get("format") or {}).get("duration", 0) or 0)
    frame_tolerance = 1 / float(fmt.get("fps", 30)) + 0.05
    if expected_duration and abs(actual_duration - expected_duration) > frame_tolerance:
        errors.append(f"render duration {actual_duration:.3f}s differs from manifest {expected_duration:.3f}s")

    decode = run([ffmpeg, "-v", "error", "-i", str(args.video), "-f", "null", "-"])
    if decode.returncode != 0:
        errors.append(f"full decode failed: {decode.stderr.strip()}")

    boundary_dir = args.output_dir / "boundaries"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    fps = float(fmt.get("fps", 30))
    for scene in manifest.get("scenes", [])[:-1]:
        transition = scene.get("transitionOut") or {}
        boundary = float(scene["startSec"]) + float(scene["durationSec"]) - float(transition.get("durationSec", 0))
        for suffix, offset in (("minus1", -1 / fps), ("boundary", 0), ("plus1", 1 / fps)):
            timestamp = max(0, boundary + offset)
            target = boundary_dir / f"{scene['sceneId']}-{suffix}.png"
            result = run([
                ffmpeg, "-y", "-v", "error", "-ss", f"{timestamp:.6f}", "-i", str(args.video),
                "-frames:v", "1", str(target)
            ])
            if result.returncode != 0:
                warnings.append(f"could not extract boundary frame {target.name}: {result.stderr.strip()}")

    report = {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "errors": errors,
        "warnings": warnings,
        "video": str(args.video.resolve()),
        "expectedDurationSec": expected_duration,
        "actualDurationSec": actual_duration,
        "media": media,
        "boundaryFrames": str(boundary_dir.resolve()),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "qa-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
