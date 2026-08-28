#!/usr/bin/env python3
"""Compose reusable product-demo sound effects from a JSON cue sheet."""

from __future__ import annotations

import argparse
import json
import math
import wave
from array import array
from pathlib import Path


def read_wav(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise ValueError(f"Only mono PCM16 WAV is supported: {path}")
        sample_rate = handle.getframerate()
        pcm = array("h")
        pcm.frombytes(handle.readframes(handle.getnframes()))
    return sample_rate, [sample / 32768.0 for sample in pcm]


def write_wav(path: Path, sample_rate: int, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array("h", (int(max(-1.0, min(1.0, sample)) * 32767) for sample in samples))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def db_to_gain(db: float) -> float:
    return 10 ** (db / 20.0)


def peak_dbfs(samples: list[float]) -> float:
    peak = max((abs(sample) for sample in samples), default=0.0)
    return -120.0 if peak <= 0 else 20.0 * math.log10(peak)


def load_event_map(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["events"]


def resolve_asset(cue: dict, events: dict[str, dict], sequence: dict[str, int]) -> str:
    if cue.get("asset"):
        return cue["asset"]
    event_name = cue.get("event")
    if not event_name or event_name not in events:
        raise ValueError(f"Cue needs a valid asset or event: {cue}")
    assets = events[event_name]["sfx_assets"]
    if not assets:
        raise ValueError(f"Event has no sound asset: {event_name}")
    if "variant" in cue:
        index = int(cue["variant"]) % len(assets)
    else:
        index = sequence.get(event_name, 0) % len(assets)
        sequence[event_name] = index + 1
    return assets[index]


def compose(cue_sheet_path: Path, manifest_path: Path, event_map_path: Path,
            output_path: Path, report_path: Path, preset_override: str | None) -> None:
    cue_sheet = json.loads(cue_sheet_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    events = load_event_map(event_map_path)
    assets = {item["id"]: item for item in manifest["assets"]}
    sample_rate = int(manifest["sample_rate_hz"])
    preset = preset_override or cue_sheet.get("preset") or manifest["default_intensity"]
    if preset not in manifest["intensity_gain_db"]:
        raise ValueError(f"Unknown intensity preset: {preset}")
    preset_gain_db = float(manifest["intensity_gain_db"][preset])

    duration = float(cue_sheet["duration_seconds"])
    timeline = [0.0] * int(math.ceil(duration * sample_rate))
    sequence: dict[str, int] = {}
    report_cues: list[dict] = []

    for cue in sorted(cue_sheet["cues"], key=lambda item: float(item["time"])):
        if cue.get("enabled", True) is False:
            continue
        asset_id = resolve_asset(cue, events, sequence)
        if asset_id not in assets:
            raise ValueError(f"Unknown asset id: {asset_id}")
        wav_path = manifest_path.parent / assets[asset_id]["path"]
        wav_rate, samples = read_wav(wav_path)
        if wav_rate != sample_rate:
            raise ValueError(f"Sample-rate mismatch for {wav_path}: {wav_rate} != {sample_rate}")
        start = int(round(float(cue["time"]) * sample_rate))
        cue_gain_db = float(cue.get("gain_db", 0.0))
        gain = db_to_gain(preset_gain_db + cue_gain_db)
        for index, sample in enumerate(samples):
            target = start + index
            if 0 <= target < len(timeline):
                timeline[target] += sample * gain
        report_cues.append({
            "time": float(cue["time"]),
            "event": cue.get("event"),
            "asset": asset_id,
            "gain_db": round(preset_gain_db + cue_gain_db, 2),
            "note": cue.get("note", ""),
        })

    pre_normalize_peak = peak_dbfs(timeline)
    ceiling = float(manifest["rules"]["final_mix_peak_ceiling_dbfs"])
    normalization_db = min(0.0, ceiling - pre_normalize_peak)
    if normalization_db < 0:
        scale = db_to_gain(normalization_db)
        timeline = [sample * scale for sample in timeline]
    write_wav(output_path, sample_rate, timeline)

    report = {
        "schema_version": "1.0",
        "cue_sheet": str(cue_sheet_path),
        "output": str(output_path),
        "preset": preset,
        "duration_seconds": duration,
        "sample_rate_hz": sample_rate,
        "cue_count": len(report_cues),
        "pre_normalize_peak_dbfs": round(pre_normalize_peak, 2),
        "normalization_gain_db": round(normalization_db, 2),
        "final_peak_dbfs": round(peak_dbfs(timeline), 2),
        "cues": report_cues,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    print(f"Wrote {report_path}")


def main() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("cue_sheet", type=Path)
    parser.add_argument("--manifest", type=Path,
                        default=skill_dir / "assets/sfx/product-demo-clean/manifest.json")
    parser.add_argument("--event-map", type=Path,
                        default=skill_dir / "assets/enhancement-event-map.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--preset", choices=["subtle", "clear", "promo"])
    args = parser.parse_args()
    output = args.output.resolve()
    report = args.report.resolve() if args.report else output.with_suffix(".json")
    compose(args.cue_sheet.resolve(), args.manifest.resolve(), args.event_map.resolve(),
            output, report, args.preset)


if __name__ == "__main__":
    main()
