#!/usr/bin/env python3
"""Validate the single-source project manifest for the video workflow."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


STATES = [
    "initialized",
    "evidence_ready",
    "script_locked",
    "voice_style_locked",
    "voice_generated",
    "subtitle_timeline_locked",
    "visual_timeline_locked",
    "preview_approved",
    "variants_rendered",
    "qa_passed",
    "delivered",
]

ALLOWED_MODES = {
    "tutorial-slicing",
    "enterprise-business-demo",
    "social-promo",
}

ALLOWED_ASSET_STATES = {"transitional", "stable", "success", "error"}
FORBIDDEN_VARIANT_KEYS = {"narration", "sentences", "subtitleCues", "shots", "audio"}
IGNORED_TEXT = re.compile(r"[\s，。！？；：、,.!?;:'\"“”‘’《》〈〉【】\[\]（）()—…·|-]+")


def normalized_text(value: Any) -> str:
    return IGNORED_TEXT.sub("", str(value or ""))


def ends_with_punctuation(value: Any) -> bool:
    text = str(value or "").rstrip()
    if not text:
        return False
    return unicodedata.category(text[-1]).startswith("P") or text[-1] in "|｜"


def positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def required(mapping: dict[str, Any], key: str, path: str, errors: list[str]) -> Any:
    value = mapping.get(key)
    if value is None or value == "" or value == []:
        errors.append(f"{path}.{key} is required")
    return value


def unique_ids(items: list[dict[str, Any]], path: str, errors: list[str]) -> set[str]:
    found: set[str] = set()
    for index, item in enumerate(items):
        item_id = item.get("id")
        if not item_id:
            errors.append(f"{path}[{index}].id is required")
            continue
        if item_id in found:
            errors.append(f"{path} contains duplicate id {item_id}")
        found.add(str(item_id))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result = {"status": "error", "errors": [f"manifest not found: {args.manifest}"], "warnings": []}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    except json.JSONDecodeError as exc:
        result = {"status": "error", "errors": [f"invalid JSON: {exc}"], "warnings": []}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    if data.get("schemaVersion") != "2.0":
        errors.append("schemaVersion must be 2.0")

    state = data.get("state")
    if state not in STATES:
        errors.append(f"state must be one of: {', '.join(STATES)}")
        state_rank = -1
    else:
        state_rank = STATES.index(state)

    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    required(project, "name", "project", errors)
    mode = required(project, "mode", "project", errors)
    required(project, "goal", "project", errors)
    required(project, "outputRoot", "project", errors)
    if mode and mode not in ALLOWED_MODES:
        errors.append(f"project.mode must be one of: {', '.join(sorted(ALLOWED_MODES))}")

    execution = data.get("execution") if isinstance(data.get("execution"), dict) else {}
    if not execution:
        warnings.append("execution policy is missing; migrate this legacy manifest to the current template")
    else:
        if execution.get("canonicalPath") != "verified-scripts":
            errors.append("execution.canonicalPath must be verified-scripts")
        if execution.get("renderer") not in {"remotion", "moviepy"}:
            errors.append("execution.renderer must be remotion or moviepy")
        if execution.get("renderer") == "remotion" and execution.get("moviepyEnabled") is True:
            errors.append("MoviePy cannot be enabled alongside the canonical Remotion renderer")
        if execution.get("allowSilentFallback") is not False:
            errors.append("execution.allowSilentFallback must be false")

    subtitle_policy = data.get("subtitlePolicy") if isinstance(data.get("subtitlePolicy"), dict) else {}
    if not subtitle_policy:
        warnings.append("subtitlePolicy is missing; migrate this legacy manifest to the current template")
    else:
        if subtitle_policy.get("terminalPunctuation") != "forbidden":
            errors.append("subtitlePolicy.terminalPunctuation must be forbidden")
        if subtitle_policy.get("spokenDisplayWords") != "exact_match":
            errors.append("subtitlePolicy.spokenDisplayWords must be exact_match")

    script = data.get("script") if isinstance(data.get("script"), dict) else {}
    sentences = script.get("sentences") if isinstance(script.get("sentences"), list) else []
    sentence_ids = unique_ids(sentences, "script.sentences", errors) if sentences else set()

    assets = data.get("assets") if isinstance(data.get("assets"), list) else []
    asset_ids = unique_ids(assets, "assets", errors) if assets else set()

    timeline = data.get("timeline") if isinstance(data.get("timeline"), dict) else {}
    timeline_id = timeline.get("id")
    cues = timeline.get("subtitleCues") if isinstance(timeline.get("subtitleCues"), list) else []
    shots = timeline.get("shots") if isinstance(timeline.get("shots"), list) else []

    approvals = data.get("approvals") if isinstance(data.get("approvals"), dict) else {}
    voice = data.get("voice") if isinstance(data.get("voice"), dict) else {}
    qa = data.get("qa") if isinstance(data.get("qa"), dict) else {}

    if state_rank >= STATES.index("evidence_ready"):
        if not assets:
            errors.append("assets must not be empty at evidence_ready or later")
        for index, asset in enumerate(assets):
            required(asset, "path", f"assets[{index}]", errors)
            required(asset, "semanticType", f"assets[{index}]", errors)
            visual_state = required(asset, "visualState", f"assets[{index}]", errors)
            if visual_state and visual_state not in ALLOWED_ASSET_STATES:
                errors.append(f"assets[{index}].visualState is invalid")
            source_in = asset.get("sourceInSec")
            source_out = asset.get("sourceOutSec")
            if source_in is not None and (not isinstance(source_in, (int, float)) or source_in < 0):
                errors.append(f"assets[{index}].sourceInSec must be >= 0")
            if source_out is not None and source_in is not None and source_out <= source_in:
                errors.append(f"assets[{index}] sourceOutSec must be greater than sourceInSec")

    if state_rank >= STATES.index("script_locked"):
        required(script, "activeVersion", "script", errors)
        required(script, "sourcePath", "script", errors)
        if script.get("locked") is not True or approvals.get("script") is not True:
            errors.append("script.locked and approvals.script must both be true")
        if not sentences:
            errors.append("script.sentences must not be empty at script_locked or later")
        for index, sentence in enumerate(sentences):
            for key in ("spokenText", "displayText", "ttsText", "visualIntent"):
                required(sentence, key, f"script.sentences[{index}]", errors)
            if normalized_text(sentence.get("spokenText")) != normalized_text(sentence.get("displayText")):
                errors.append(f"sentence {sentence.get('id', index)} displayText does not match spokenText")
            if ends_with_punctuation(sentence.get("displayText")):
                errors.append(f"sentence {sentence.get('id', index)} displayText must not end with punctuation")
            if not positive_number(sentence.get("targetDurationSec")):
                errors.append(f"sentence {sentence.get('id', index)} targetDurationSec must be > 0")
            for evidence_id in sentence.get("evidenceIds", []):
                if evidence_id not in asset_ids:
                    errors.append(f"sentence {sentence.get('id', index)} references unknown asset {evidence_id}")

    if state_rank >= STATES.index("voice_style_locked"):
        if voice.get("styleLocked") is not True or approvals.get("voiceStyle") is not True:
            errors.append("voice.styleLocked and approvals.voiceStyle must both be true")
        required(voice, "samplePath", "voice", errors)
        runtime = data.get("runtime") if isinstance(data.get("runtime"), dict) else {}
        required(runtime, "ttsProvider", "runtime", errors)
        required(runtime, "voiceId", "runtime", errors)

    if state_rank >= STATES.index("voice_generated"):
        required(voice, "fullAudioPath", "voice", errors)
        required(voice, "reportPath", "voice", errors)
        if not positive_number(voice.get("durationSec")):
            errors.append("voice.durationSec must be > 0")
        for sentence in sentences:
            if not positive_number(sentence.get("actualDurationSec")):
                errors.append(f"sentence {sentence.get('id')} actualDurationSec must be > 0")
            required(sentence, "audioPath", f"sentence {sentence.get('id')}", errors)

    if state_rank >= STATES.index("subtitle_timeline_locked"):
        if not cues:
            errors.append("timeline.subtitleCues must not be empty")
        cue_ids = unique_ids(cues, "timeline.subtitleCues", errors) if cues else set()
        cues_by_sentence: dict[str, list[dict[str, Any]]] = {}
        previous_start = -1.0
        for index, cue in enumerate(cues):
            sentence_id = cue.get("sentenceId")
            if sentence_id not in sentence_ids:
                errors.append(f"timeline.subtitleCues[{index}] references unknown sentence {sentence_id}")
            start = cue.get("startSec")
            end = cue.get("endSec")
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < 0 or end <= start:
                errors.append(f"timeline.subtitleCues[{index}] has invalid timing")
            elif start < previous_start:
                errors.append("timeline.subtitleCues must be ordered by startSec")
            else:
                previous_start = start
            required(cue, "text", f"timeline.subtitleCues[{index}]", errors)
            if ends_with_punctuation(cue.get("text")):
                errors.append(f"timeline.subtitleCues[{index}].text must not end with punctuation")
            cues_by_sentence.setdefault(str(sentence_id), []).append(cue)
        for sentence in sentences:
            expected_ids = sentence.get("subtitleCueIds", [])
            for cue_id in expected_ids:
                if cue_id not in cue_ids:
                    errors.append(f"sentence {sentence.get('id')} references unknown cue {cue_id}")
            joined = "".join(str(cue.get("text", "")) for cue in cues_by_sentence.get(str(sentence.get("id")), []))
            if normalized_text(joined) != normalized_text(sentence.get("displayText")):
                errors.append(f"subtitle cues do not reconstruct sentence {sentence.get('id')}")

    if state_rank >= STATES.index("visual_timeline_locked"):
        if not shots:
            errors.append("timeline.shots must not be empty")
        unique_ids(shots, "timeline.shots", errors) if shots else None
        covered_sentences: set[str] = set()
        for index, shot in enumerate(shots):
            start = shot.get("startSec")
            end = shot.get("endSec")
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < 0 or end <= start:
                errors.append(f"timeline.shots[{index}] has invalid timing")
            required(shot, "kind", f"timeline.shots[{index}]", errors)
            sentence_refs = shot.get("sentenceIds", [])
            if not sentence_refs:
                warnings.append(f"shot {shot.get('id', index)} has no sentenceIds")
            for sentence_id in sentence_refs:
                if sentence_id not in sentence_ids:
                    errors.append(f"shot {shot.get('id', index)} references unknown sentence {sentence_id}")
                covered_sentences.add(str(sentence_id))
            asset_id = shot.get("assetId")
            if asset_id:
                if asset_id not in asset_ids:
                    errors.append(f"shot {shot.get('id', index)} references unknown asset {asset_id}")
                else:
                    asset = next(item for item in assets if item.get("id") == asset_id)
                    if asset.get("semanticType") in {"loading", "error"} or asset.get("visualState") == "error":
                        errors.append(f"shot {shot.get('id', index)} uses forbidden loading/error asset {asset_id}")
        missing = sorted(sentence_ids - covered_sentences)
        if missing:
            errors.append(f"sentences without visual coverage: {', '.join(missing)}")

    if state_rank >= STATES.index("preview_approved"):
        if approvals.get("preview60") is not True or approvals.get("crossChapterFrames") is not True:
            errors.append("both preview approvals must be true")
        required(qa, "preview60Path", "qa", errors)
        required(qa, "crossChapterFramesPath", "qa", errors)

    if state_rank >= STATES.index("variants_rendered"):
        variants = data.get("variants") if isinstance(data.get("variants"), dict) else {}
        requested = project.get("requestedVariants", [])
        if not variants:
            errors.append("variants must not be empty")
        for name in requested:
            if name not in variants:
                errors.append(f"requested variant {name} is missing")
        for name, variant in variants.items():
            if variant.get("contentTimelineId") != timeline_id:
                errors.append(f"variant {name} does not reference timeline {timeline_id}")
            duplicate_keys = sorted(FORBIDDEN_VARIANT_KEYS.intersection(variant))
            if duplicate_keys:
                errors.append(f"variant {name} duplicates content keys: {', '.join(duplicate_keys)}")
            required(variant, "renderedPath", f"variants.{name}", errors)

    if state_rank >= STATES.index("qa_passed"):
        if qa.get("status") != "ok":
            errors.append("qa.status must be ok")
        required(qa, "manifestReportPath", "qa", errors)
        required(qa, "renderLockReportPath", "qa", errors)

    if state_rank >= STATES.index("delivered") and approvals.get("delivery") is not True:
        errors.append("approvals.delivery must be true")

    status = "error" if errors else "warning" if warnings else "ok"
    result = {
        "status": status,
        "manifest": str(args.manifest.resolve()),
        "state": state,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "sentences": len(sentences),
            "assets": len(assets),
            "subtitleCues": len(cues),
            "shots": len(shots),
        },
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
