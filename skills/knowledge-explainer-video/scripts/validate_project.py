#!/usr/bin/env python3
"""Validate a knowledge-explainer project manifest without third-party packages."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


STATUS_ORDER = [
    "initialized",
    "evidence_ready",
    "content_approved",
    "visual_direction_approved",
    "assets_ready",
    "voice_locked",
    "timeline_locked",
    "preview_approved",
    "rendered",
    "qa_passed",
    "delivered",
]


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _status_at_least(manifest: dict[str, Any], status: str) -> bool:
    current = manifest.get("status")
    return current in STATUS_ORDER and STATUS_ORDER.index(current) >= STATUS_ORDER.index(status)


def _resolve(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def _union_duration(intervals: list[tuple[float, float]]) -> float:
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


def validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    base = manifest_path.parent

    def error(message: str) -> None:
        errors.append(message)

    def warn(message: str) -> None:
        warnings.append(message)

    if manifest.get("schemaVersion") != "1.0":
        error("schemaVersion must be '1.0'")
    if not str(manifest.get("projectId", "")).strip():
        error("projectId is required")
    if not str(manifest.get("topic", "")).strip():
        error("topic is required")
    if manifest.get("status") not in STATUS_ORDER:
        error(f"status must be one of: {', '.join(STATUS_ORDER)}")

    fmt = manifest.get("format") or {}
    for key in ("fps", "width", "height"):
        if not _number(fmt.get(key)) or fmt[key] <= 0:
            error(f"format.{key} must be a positive number")
    if fmt.get("fps") not in (24, 25, 30, 50, 60):
        warn("format.fps is unusual for the standard workflow; 30 is the default")

    approvals = manifest.get("approvals") or {}
    if _status_at_least(manifest, "content_approved"):
        if (approvals.get("content") or {}).get("status") != "approved":
            error("content approval must be approved at content_approved or later")
        sentences = ((manifest.get("narrative") or {}).get("sentences") or [])
        if not sentences:
            error("narrative.sentences is required after content approval")
        known_sources = {item.get("sourceId") for item in manifest.get("sources", [])}
        for sentence in sentences:
            sid = sentence.get("narrationId", "<missing>")
            if not str(sentence.get("text", "")).strip():
                error(f"sentence {sid} has no text")
            evidence_ids = sentence.get("evidenceIds") or []
            if not evidence_ids:
                warn(f"sentence {sid} has no evidenceIds")
            for evidence_id in evidence_ids:
                if evidence_id not in known_sources:
                    error(f"sentence {sid} references unknown evidence/source id {evidence_id}")

    visual = manifest.get("visualDirection") or {}
    if _status_at_least(manifest, "visual_direction_approved"):
        if (approvals.get("visualDirection") or {}).get("status") != "approved":
            error("visualDirection approval must be approved at visual_direction_approved or later")
        if not str(visual.get("stylePreset", "")).strip():
            error("visualDirection.stylePreset is required")
        if not manifest.get("scenes"):
            error("scenes are required after visual direction approval")

    sources = {item.get("sourceId"): item for item in manifest.get("sources", [])}
    assets = {item.get("assetId"): item for item in manifest.get("assets", [])}
    for asset_id, asset in assets.items():
        if not asset_id:
            error("every asset needs assetId")
            continue
        path = _resolve(base, asset.get("path"))
        if asset.get("selected") and path and not path.exists():
            error(f"selected asset {asset_id} does not exist: {path}")
        if asset.get("kind") == "real-video":
            if not asset.get("sourceId") or asset.get("sourceId") not in sources:
                error(f"real-video asset {asset_id} needs a known sourceId")
            if not str(asset.get("license", "")).strip():
                error(f"real-video asset {asset_id} needs a license value")

    if (visual.get("realFootage") or {}).get("enabled"):
        policy = (visual.get("realFootage") or {}).get("sourcePolicy")
        if policy != "authorized-or-clearly-licensed":
            error("real footage sourcePolicy must be authorized-or-clearly-licensed")

    scenes = manifest.get("scenes") or []
    visual_intervals: list[tuple[float, float]] = []
    text_intervals: list[tuple[float, float]] = []
    seen_scene_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        scene_id = scene.get("sceneId", f"scene[{index}]")
        if scene_id in seen_scene_ids:
            error(f"duplicate sceneId {scene_id}")
        seen_scene_ids.add(scene_id)
        start = scene.get("startSec")
        duration = scene.get("durationSec")
        if not _number(start) or start < 0:
            error(f"scene {scene_id} startSec must be >= 0")
            continue
        if not _number(duration) or duration <= 0:
            error(f"scene {scene_id} durationSec must be > 0")
            continue
        if duration < 8 or duration > 15:
            warn(f"scene {scene_id} is {duration:.2f}s; review the usual 8–15s knowledge pace")

        anchor = scene.get("anchor")
        if anchor:
            box = anchor.get("box") or {}
            _validate_box(box, f"scene {scene_id} anchor", error)

        beats = scene.get("visualBeats") or []
        if not beats:
            error(f"scene {scene_id} has no visualBeats")
        beat_starts = sorted(float(beat.get("startSec", 0)) for beat in beats if _number(beat.get("startSec")))
        for left, right in zip(beat_starts, beat_starts[1:]):
            gap = right - left
            if gap < 3:
                warn(f"scene {scene_id} changes focal beats after only {gap:.2f}s")
            if gap > 6:
                warn(f"scene {scene_id} has a {gap:.2f}s gap between focal changes")

        for beat in beats:
            beat_id = beat.get("beatId", "<missing>")
            rel_start = beat.get("startSec")
            beat_duration = beat.get("durationSec")
            if not _number(rel_start) or rel_start < 0:
                error(f"beat {beat_id} startSec must be >= 0")
                continue
            if not _number(beat_duration) or beat_duration <= 0:
                error(f"beat {beat_id} durationSec must be > 0")
                continue
            if rel_start + beat_duration > duration + 0.001:
                error(f"beat {beat_id} exceeds scene {scene_id}")
            if beat.get("emphasis") == "key" and beat_duration < 1.5:
                error(f"key beat {beat_id} must remain visible for at least 1.5s")
            _validate_box(beat.get("box") or {}, f"beat {beat_id}", error)
            asset_id = beat.get("assetId")
            if asset_id and asset_id not in assets:
                error(f"beat {beat_id} references unknown asset {asset_id}")
            absolute = (float(start) + float(rel_start), min(float(start) + float(rel_start) + float(beat_duration), float(start) + float(duration)))
            if beat.get("kind") in {"illustration", "character", "real-video", "screenshot", "diagram"}:
                visual_intervals.append(absolute)
            if beat.get("kind") == "text-card":
                text_intervals.append(absolute)

        transition = scene.get("transitionOut")
        if transition:
            mode = transition.get("mode")
            trans_duration = transition.get("durationSec")
            if mode not in {"continuity", "section-reset"}:
                error(f"scene {scene_id} transition mode must be continuity or section-reset")
            if not _number(trans_duration) or trans_duration <= 0:
                error(f"scene {scene_id} transition duration must be positive")
            elif mode == "continuity" and not 0.8 <= trans_duration <= 1.5:
                error(f"scene {scene_id} continuity transition must be 0.8–1.5s")
            if mode == "continuity":
                if not transition.get("anchorId"):
                    error(f"scene {scene_id} continuity transition needs anchorId")
                if not anchor or transition.get("anchorId") != anchor.get("anchorId"):
                    error(f"scene {scene_id} continuity transition anchor must match its scene anchor")
                if index + 1 >= len(scenes):
                    error(f"last scene {scene_id} cannot have a continuity transition")
                else:
                    next_anchor = scenes[index + 1].get("anchor") or {}
                    if transition.get("anchorId") != next_anchor.get("anchorId"):
                        error(f"transition {scene_id} → {scenes[index + 1].get('sceneId')} must use one shared anchorId")

        if index + 1 < len(scenes) and transition and _number(transition.get("durationSec")):
            expected = float(start) + float(duration) - float(transition["durationSec"])
            actual = scenes[index + 1].get("startSec")
            if _number(actual) and abs(float(actual) - expected) > 0.05:
                error(f"scene {scenes[index + 1].get('sceneId')} must start at {expected:.3f}s for the transition overlap")

    voice = manifest.get("voiceover") or {}
    if _status_at_least(manifest, "voice_locked"):
        if voice.get("mode") != "manual" or not voice.get("locked"):
            error("voice_locked requires locked manual voiceover")
        voice_path = _resolve(base, voice.get("path"))
        if not voice_path or not voice_path.exists():
            error("voiceover.path must exist at voice_locked or later")
        if not _number(voice.get("durationSec")) or voice["durationSec"] <= 0:
            error("voiceover.durationSec must be positive")

    if _status_at_least(manifest, "timeline_locked"):
        if not scenes:
            error("timeline_locked requires scenes")
        else:
            total = max(float(scene["startSec"]) + float(scene["durationSec"]) for scene in scenes if _number(scene.get("startSec")) and _number(scene.get("durationSec")))
            if _number(voice.get("durationSec")) and abs(total - float(voice["durationSec"])) > 0.1:
                error(f"timeline duration {total:.3f}s differs from voiceover by more than 0.1s")
            min_coverage = float(visual.get("minVisualCoverage", 0.75))
            max_text = float(visual.get("maxTextOnlyShare", 0.15))
            if total > 0:
                coverage = _union_duration(visual_intervals) / total
                text_share = _union_duration(text_intervals) / total
                if coverage + 1e-6 < min_coverage:
                    error(f"visual coverage {coverage:.1%} is below {min_coverage:.1%}")
                if text_share - 1e-6 > max_text:
                    error(f"text-only share {text_share:.1%} exceeds {max_text:.1%}")

        for sentence in ((manifest.get("narrative") or {}).get("sentences") or []):
            sid = sentence.get("narrationId", "<missing>")
            if not _number(sentence.get("startSec")) or not _number(sentence.get("endSec")):
                error(f"sentence {sid} needs actual startSec/endSec at timeline_locked")
            elif sentence["endSec"] <= sentence["startSec"]:
                error(f"sentence {sid} endSec must be after startSec")

    return {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "manifest": str(manifest_path),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "statusValue": manifest.get("status"),
            "sources": len(manifest.get("sources", [])),
            "sentences": len(((manifest.get("narrative") or {}).get("sentences") or [])),
            "assets": len(manifest.get("assets", [])),
            "scenes": len(scenes),
        },
    }


def _validate_box(box: dict[str, Any], label: str, error: Any) -> None:
    for key in ("x", "y", "width", "height"):
        if not _number(box.get(key)):
            error(f"{label} box.{key} must be a number")
            return
    if box["width"] <= 0 or box["height"] <= 0:
        error(f"{label} box width and height must be positive")
    if box["x"] < 0 or box["y"] < 0 or box["x"] + box["width"] > 1.0001 or box["y"] + box["height"] > 1.0001:
        error(f"{label} box must remain inside normalized 0–1 bounds")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "errors": [f"cannot read manifest: {exc}"]}, ensure_ascii=False, indent=2))
        return 1

    report = validate_manifest(manifest, args.manifest.resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
