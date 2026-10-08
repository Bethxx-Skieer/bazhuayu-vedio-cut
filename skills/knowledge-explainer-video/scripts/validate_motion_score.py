"""Validate the optional motion score, never infer visual or playback approval."""
import json
import math
import sys
from pathlib import Path

PRINCIPLES = {
    "squash-stretch", "anticipation", "staging", "pose-to-pose",
    "follow-through", "slow-in-out", "arcs", "secondary-action",
    "timing", "exaggeration", "solid-drawing", "appeal",
}

def validate(data):
    errors, warnings = [], []
    def fail(message):
        errors.append(message)
    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    def bounds(item, label, duration):
        start, end = item.get("startSec"), item.get("endSec")
        if not number(start) or not number(end) or not 0 <= start < end <= duration:
            fail(f"{label}: invalid interval {start}..{end}")
            return None
        return start, end
    if not isinstance(data, dict):
        return ["Root must be an object"], []
    duration, fps = data.get("durationSec"), data.get("fps")
    if not number(duration) or duration <= 0 or not number(fps) or fps <= 0:
        return ["durationSec and fps must be positive finite numbers"], []
    if data.get("schemaVersion") != 1:
        fail("Unsupported schemaVersion")
    actions, transitions = data.get("actions", []), data.get("transitions", [])
    if not isinstance(actions, list) or not isinstance(transitions, list):
        return ["actions and transitions must be arrays"], []
    ids = set()
    for kind, entries in (("action", actions), ("transition", transitions)):
        for index, item in enumerate(entries):
            label = f"{kind}[{index}]"
            if not isinstance(item, dict):
                fail(f"{label}: must be an object")
                continue
            ident = item.get("id")
            if not isinstance(ident, str) or not ident.strip() or ident in ids:
                fail(f"{label}: missing or duplicate id")
            else:
                ids.add(ident)
            span = bounds(item, label, duration)
            if span is None:
                continue
            start, end = span
            samples = item.get("reviewFramesSec", [])
            if not isinstance(samples, list) or any(not number(x) or not start <= x <= end for x in samples):
                fail(f"{label}: review times must fall inside interval")
            elif len(samples) < 3:
                warnings.append(f"{label}: add start, intermediate and landing review frames")
            if kind == "action":
                for key in ("objectId", "intent", "result", "occlusion", "camera"):
                    if not isinstance(item.get(key), str) or not item[key].strip():
                        fail(f"{label}: {key} is required")
                cue = item.get("cue", {})
                if not isinstance(cue, dict) or not number(cue.get("timeSec")) or not 0 <= cue["timeSec"] <= duration or not cue.get("text"):
                    fail(f"{label}: cue must contain text and a valid actual-audio time")
                principles = item.get("principles", [])
                if not isinstance(principles, list) or not principles or any(not isinstance(x, str) or x not in PRINCIPLES for x in principles):
                    fail(f"{label}: choose known principles")
                phases = item.get("phases", [])
                if not isinstance(phases, list) or not phases:
                    fail(f"{label}: phases are required")
                    continue
                previous = start
                for phase in phases:
                    if not isinstance(phase, dict):
                        fail(f"{label}: phase must be an object")
                        continue
                    phase_span = bounds(phase, label + "/phase", duration)
                    if phase_span:
                        a, b = phase_span
                        if a < previous - 1e-6 or b > end or a < start:
                            fail(f"{label}: main phases overlap or exceed action")
                        if a > previous + 1 / fps:
                            warnings.append(f"{label}: unexplained gap in main action")
                        previous = b
                if previous < end - 1 / fps:
                    warnings.append(f"{label}: final part of action has no phase")
                if not any(isinstance(x, dict) and x.get("name") == "hold" for x in phases):
                    warnings.append(f"{label}: review whether result needs a reading hold")
            else:
                for key in ("fromScene", "toScene", "anchorId", "method", "direction", "ownership", "reason"):
                    if not isinstance(item.get(key), str) or not item[key].strip():
                        fail(f"{label}: {key} is required")
                h = item.get("handoffSec")
                if not number(h) or not start <= h <= end:
                    fail(f"{label}: invalid handoff time")
                old, new = item.get("textOutEndSec"), item.get("textInStartSec")
                if not number(old) or not number(new) or not start <= old <= new <= end:
                    fail(f"{label}: text must leave before replacement enters")
                a, b = item.get("outgoing", {}), item.get("incoming", {})
                if not isinstance(a, dict) or not isinstance(b, dict) or any(not number(side.get(k)) for side in (a, b) for k in ("x", "y", "scale", "rotation")):
                    fail(f"{label}: handoff transforms must be numeric")
                    continue
                if a["scale"] <= 0 or b["scale"] <= 0:
                    fail(f"{label}: scale must be positive")
                tolerances = [item.get("positionTolerancePx", 1), item.get("scaleTolerance", .001), item.get("rotationToleranceDeg", .1)]
                if any(not number(x) or x < 0 for x in tolerances):
                    fail(f"{label}: tolerances must be nonnegative")
                    continue
                gaps = [math.hypot(a["x"] - b["x"], a["y"] - b["y"]), abs(a["scale"] - b["scale"]), abs((a["rotation"] - b["rotation"] + 180) % 360 - 180)]
                if any(gap > tolerance for gap, tolerance in zip(gaps, tolerances)):
                    fail(f"{label}: discontinuous anchor geometry at handoff")
                warnings.append(f"{label}: manually inspect velocity, duplicate ownership and masks")
    if not actions:
        warnings.append("No complex actions recorded; cannot infer whole-film motion coverage")
    return errors, warnings

if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: validate_motion_score.py motion-score.json")
        document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
        errors, warnings = validate(document)
        print(json.dumps({"errors": errors, "reviewReminders": warnings,
                          "scope": "plan data only; not visual, audio or playback approval"}, ensure_ascii=False, indent=2))
        sys.exit(1 if errors else 0)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
