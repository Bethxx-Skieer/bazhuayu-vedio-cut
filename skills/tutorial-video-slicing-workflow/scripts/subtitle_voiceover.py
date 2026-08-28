#!/usr/bin/env python3
"""Generate a time-aligned voiceover track from SRT/VTT/ASS/timed JSON.

The script deliberately stops on substantial speech overruns instead of cutting words.
It uses only the Python standard library plus ffmpeg (system or imageio-ffmpeg).
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOICE_PROFILE = SKILL_ROOT / "assets/voiceover-profile-zh-CN.json"


@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str
    spoken_seconds: float | None = None
    speed_factor: float = 1.0
    status: str = "pending"

    @property
    def window_seconds(self) -> float:
        return self.end - self.start


def parse_time(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip().replace(",", ".")
    parts = value.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except ValueError as exc:
        raise ValueError(f"Invalid time value: {value!r}") from exc


def clean_ass_text(text: str) -> str:
    text = re.sub(r"\{[^}]*\}", "", text)
    return text.replace(r"\N", "\n").replace(r"\n", "\n").strip()


def parse_srt_or_vtt(path: Path) -> list[Cue]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if text.lstrip().startswith("WEBVTT"):
        text = re.sub(r"^\s*WEBVTT[^\n]*\n", "", text, count=1)
    blocks = re.split(r"\n\s*\n", text.strip())
    cues: list[Cue] = []
    time_re = re.compile(r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d+)\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d+)")
    for block in blocks:
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        time_pos = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if time_pos is None:
            continue
        match = time_re.search(lines[time_pos])
        if not match:
            raise ValueError(f"Invalid subtitle time line: {lines[time_pos]!r}")
        spoken = "\n".join(lines[time_pos + 1 :]).strip()
        if spoken:
            cues.append(Cue(len(cues) + 1, parse_time(match.group("start")), parse_time(match.group("end")), spoken))
    return cues


def parse_ass(path: Path) -> list[Cue]:
    cues: list[Cue] = []
    in_events = False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            in_events = line.lower() == "[events]"
            continue
        if not in_events or not line.lower().startswith("dialogue:"):
            continue
        values = line.split(":", 1)[1].lstrip().split(",", 9)
        if len(values) < 10:
            raise ValueError(f"Invalid ASS Dialogue row: {line!r}")
        spoken = clean_ass_text(values[9])
        if spoken:
            cues.append(Cue(len(cues) + 1, parse_time(values[1]), parse_time(values[2]), spoken))
    return cues


def parse_json_subtitles(path: Path) -> list[Cue]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        for key in ("subtitles", "segments", "cues"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError("Timed JSON must be an array or contain subtitles/segments/cues array")
    cues: list[Cue] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Every timed JSON cue must be an object")
        text = str(item.get("text", item.get("content", ""))).strip()
        if not text:
            continue
        start = item.get("start", item.get("start_time"))
        end = item.get("end", item.get("end_time"))
        if start is None or end is None:
            raise ValueError(f"JSON cue is missing start/end: {item!r}")
        cues.append(Cue(len(cues) + 1, parse_time(start), parse_time(end), text))
    return cues


def load_cues(path: Path) -> list[Cue]:
    suffix = path.suffix.lower()
    if suffix in {".srt", ".vtt"}:
        cues = parse_srt_or_vtt(path)
    elif suffix == ".ass":
        cues = parse_ass(path)
    elif suffix == ".json":
        cues = parse_json_subtitles(path)
    else:
        raise ValueError("Supported subtitle formats: .srt, .vtt, .ass, .json")
    if not cues:
        raise ValueError("No readable subtitle cues found")
    return cues


def validate_cues(cues: list[Cue], media_duration: float | None = None) -> list[str]:
    errors: list[str] = []
    previous_end = 0.0
    for cue in cues:
        if cue.start < 0 or cue.end <= cue.start:
            errors.append(f"Cue {cue.index}: end must be later than start")
        if cue.start < previous_end - 0.001:
            errors.append(f"Cue {cue.index}: overlaps the previous cue")
        if media_duration is not None and cue.end > media_duration + 0.1:
            errors.append(f"Cue {cue.index}: ends after the video ({media_duration:.3f}s)")
        previous_end = max(previous_end, cue.end)
    return errors


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


def load_voice_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    for field in ("voice", "rate", "max_stretch", "fallback_policy"):
        if field not in profile:
            raise ValueError(f"Voice profile is missing {field!r}: {path}")
    return profile


def say_voice_is_installed(voice: str) -> bool:
    result = subprocess.run(["say", "-v", "?"], text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Could not query installed macOS voices")
    return any(re.match(rf"^{re.escape(voice)}\s+", line) for line in result.stdout.splitlines())


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=capture)
    if result.returncode != 0:
        detail = result.stderr[-1600:] if capture else ""
        raise RuntimeError(f"Command failed ({result.returncode}): {shlex.join(command)}\n{detail}")
    return result


def media_duration(ffmpeg: str, path: Path) -> float:
    result = subprocess.run([ffmpeg, "-i", str(path)], text=True, capture_output=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Could not read media duration: {path}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def synthesize_say(cue: Cue, output: Path, voice: str, rate: int) -> None:
    text_file = output.with_suffix(".txt")
    text_file.write_text(cue.text, encoding="utf-8")
    run(["say", "-v", voice, "-r", str(rate), "-f", str(text_file), "-o", str(output)])


def synthesize_command(cue: Cue, output: Path, template: str, voice: str, rate: int) -> None:
    text_file = output.with_suffix(".txt")
    text_file.write_text(cue.text, encoding="utf-8")
    replacements = {
        "{text}": cue.text,
        "{text_file}": str(text_file),
        "{output_file}": str(output),
        "{voice}": voice,
        "{rate}": str(rate),
    }
    command: list[str] = []
    for arg in shlex.split(template):
        for marker, value in replacements.items():
            arg = arg.replace(marker, value)
        command.append(arg)
    if not any("{output_file}" in arg for arg in shlex.split(template)):
        raise ValueError("--tts-command must contain {output_file}")
    if not any(marker in template for marker in ("{text}", "{text_file}")):
        raise ValueError("--tts-command must contain {text} or {text_file}")
    run(command, capture=True)


def normalize_audio(ffmpeg: str, source: Path, output: Path) -> None:
    run([ffmpeg, "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(output)], capture=True)


def fit_audio(ffmpeg: str, source: Path, output: Path, window: float, speed: float) -> None:
    filters: list[str] = []
    if speed > 1.0005:
        filters.append(f"atempo={speed:.8f}")
    filters.extend([f"apad=pad_dur={window:.6f}", f"atrim=duration={window:.6f}", "asetpts=N/SR/TB"])
    run([ffmpeg, "-y", "-i", str(source), "-af", ",".join(filters), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(output)], capture=True)


def make_silence(ffmpeg: str, output: Path, duration: float) -> None:
    run([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", f"{duration:.6f}", "-c:a", "pcm_s16le", str(output)], capture=True)


def concat_wavs(ffmpeg: str, parts: list[Path], manifest: Path, output: Path) -> None:
    manifest.write_text("".join(f"file '{part.as_posix()}'\n" for part in parts), encoding="utf-8")
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c:a", "pcm_s16le", str(output)], capture=True)


def mux_video(ffmpeg: str, video: Path, audio: Path, output: Path, mode: str, original_volume: float, duration: float) -> None:
    if mode == "replace":
        command = [ffmpeg, "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output)]
    else:
        graph = f"[0:a:0]volume={original_volume:.4f}[original];[original][1:a:0]amix=inputs=2:duration=longest:dropout_transition=0[aout]"
        command = [ffmpeg, "-y", "-i", str(video), "-i", str(audio), "-filter_complex", graph, "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output)]
    run(command, capture=True)


def cue_dict(cue: Cue) -> dict[str, Any]:
    data = asdict(cue)
    data["window_seconds"] = round(cue.window_seconds, 6)
    if cue.spoken_seconds is not None:
        data["spoken_seconds"] = round(cue.spoken_seconds, 6)
    data["speed_factor"] = round(cue.speed_factor, 6)
    return data


def write_report(path: Path, status: str, args: argparse.Namespace, cues: list[Cue], errors: list[str], output_audio: Path | None = None, output_video: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": status,
        "subtitle": str(args.subtitle.resolve()),
        "backend": "dry-run" if args.dry_run else args.backend,
        "voice_profile": str(args.voice_profile.resolve()),
        "voice": args.voice,
        "rate": args.rate,
        "max_stretch": args.max_stretch,
        "errors": errors,
        "cues": [cue_dict(cue) for cue in cues],
        "output_audio": str(output_audio.resolve()) if output_audio else None,
        "output_video": str(output_video.resolve()) if output_video else None,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subtitle", type=Path)
    parser.add_argument("--backend", choices=("say", "command"), default="say")
    parser.add_argument("--tts-command", help="TTS argv template; use {text_file}/{text} and {output_file}")
    parser.add_argument("--raw-extension", default="wav", help="TTS output extension for command backend")
    parser.add_argument("--voice-profile", type=Path, default=DEFAULT_VOICE_PROFILE)
    parser.add_argument("--voice", help="Explicit voice override; requires user approval when it differs from the profile")
    parser.add_argument("--rate", type=int, help="Explicit rate override; otherwise read from the voice profile")
    parser.add_argument("--max-stretch", type=float, help="Otherwise read from the voice profile")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--video", type=Path)
    parser.add_argument("--output-audio", type=Path, default=Path("voiceover.wav"))
    parser.add_argument("--output-video", type=Path)
    parser.add_argument("--mode", choices=("replace", "mix"), default="replace")
    parser.add_argument("--original-volume", type=float, default=0.25)
    parser.add_argument("--report", type=Path, default=Path("voiceover-report.json"))
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate timing without calling TTS")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.voice_profile = args.voice_profile.resolve()
    voice_profile = load_voice_profile(args.voice_profile)
    if args.voice is None:
        args.voice = str(voice_profile["voice"])
    if args.rate is None:
        args.rate = int(voice_profile["rate"])
    if args.max_stretch is None:
        args.max_stretch = float(voice_profile["max_stretch"])
    args.subtitle = args.subtitle.resolve()
    if args.max_stretch < 1.0 or args.max_stretch > 2.0:
        raise ValueError("--max-stretch must be between 1.0 and 2.0")
    if args.output_video and not args.video:
        raise ValueError("--output-video requires --video")
    if args.backend == "command" and not args.tts_command and not args.dry_run:
        raise ValueError("command backend requires --tts-command")
    if args.backend == "say" and not args.dry_run and not say_voice_is_installed(args.voice):
        raise RuntimeError(
            f"Required voice {args.voice!r} is not installed. "
            "The profile forbids silent fallback; ask the user to confirm an alternative voice."
        )

    ffmpeg = locate_ffmpeg(args.ffmpeg) if (args.video or not args.dry_run) else None
    video_duration = media_duration(ffmpeg, args.video.resolve()) if args.video and ffmpeg else None
    cues = load_cues(args.subtitle)
    errors = validate_cues(cues, video_duration)
    if errors:
        write_report(args.report, "invalid_timeline", args, cues, errors)
        print(f"Timeline validation failed; see {args.report}", file=sys.stderr)
        return 2
    for cue in cues:
        cue.status = "planned"
    if args.dry_run:
        write_report(args.report, "ok", args, cues, [])
        print(f"Validated {len(cues)} cues; report: {args.report}")
        return 0

    assert ffmpeg is not None
    args.output_audio.parent.mkdir(parents=True, exist_ok=True)
    if args.output_video:
        args.output_video.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="subtitle-voiceover-") as tmp_name:
        tmp = Path(tmp_name)
        normalized: list[Path] = []
        for cue in cues:
            extension = "aiff" if args.backend == "say" else args.raw_extension.lstrip(".")
            raw = tmp / f"raw-{cue.index:05d}.{extension}"
            if args.backend == "say":
                synthesize_say(cue, raw, args.voice, args.rate)
            else:
                synthesize_command(cue, raw, args.tts_command, args.voice, args.rate)
            wav = tmp / f"normalized-{cue.index:05d}.wav"
            normalize_audio(ffmpeg, raw, wav)
            cue.spoken_seconds = media_duration(ffmpeg, wav)
            ratio = cue.spoken_seconds / cue.window_seconds
            if ratio > args.max_stretch + 0.001:
                cue.status = "overrun"
                errors.append(
                    f"Cue {cue.index}: speech {cue.spoken_seconds:.3f}s exceeds "
                    f"window {cue.window_seconds:.3f}s beyond max stretch {args.max_stretch:.3f}"
                )
            else:
                cue.speed_factor = max(1.0, ratio)
                cue.status = "stretched" if cue.speed_factor > 1.0005 else "padded"
            normalized.append(wav)

        if errors:
            write_report(args.report, "overrun", args, cues, errors)
            print(f"Voiceover has substantial overruns; revise cues listed in {args.report}", file=sys.stderr)
            return 3

        parts: list[Path] = []
        cursor = 0.0
        for cue, wav in zip(cues, normalized):
            gap = cue.start - cursor
            if gap > 0.0005:
                silence = tmp / f"silence-{len(parts):05d}.wav"
                make_silence(ffmpeg, silence, gap)
                parts.append(silence)
            fitted = tmp / f"fitted-{cue.index:05d}.wav"
            fit_audio(ffmpeg, wav, fitted, cue.window_seconds, cue.speed_factor)
            parts.append(fitted)
            cursor = cue.end

        target_duration = video_duration if video_duration is not None else cues[-1].end
        tail = target_duration - cursor
        if tail > 0.0005:
            silence = tmp / "silence-tail.wav"
            make_silence(ffmpeg, silence, tail)
            parts.append(silence)
        concat_wavs(ffmpeg, parts, tmp / "concat.txt", args.output_audio.resolve())

    if args.video and args.output_video:
        mux_video(ffmpeg, args.video.resolve(), args.output_audio.resolve(), args.output_video.resolve(), args.mode, args.original_volume, video_duration)
    write_report(args.report, "ok", args, cues, [], args.output_audio, args.output_video)
    print(f"Created aligned voiceover: {args.output_audio}")
    if args.output_video:
        print(f"Created dubbed video: {args.output_video}")
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
