import copy
import json
import unittest
from pathlib import Path
from validate_motion_score import validate

class MotionScoreTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).parent.parent / "assets/motion-score.template.json").read_text(encoding="utf-8"))
    def rejected(self):
        self.assertTrue(validate(self.data)[0])
    def test_template(self):
        self.assertFalse(validate(self.data)[0])
    def test_bad_duration(self):
        self.data["durationSec"] = float("nan")
        self.rejected()
    def test_bool_not_number(self):
        self.data["fps"] = True
        self.rejected()
    def test_bad_time(self):
        self.data["actions"][0]["endSec"] = 11
        self.rejected()
    def test_overlap(self):
        self.data["actions"][0]["phases"][1]["startSec"] = 1.2
        self.rejected()
    def test_anchor_jump(self):
        self.data["transitions"][0]["incoming"]["x"] += 25
        self.rejected()
    def test_text_overlap(self):
        self.data["transitions"][0]["textInStartSec"] = 7.2
        self.rejected()
    def test_duplicate_id(self):
        self.data["transitions"][0]["id"] = self.data["actions"][0]["id"]
        self.rejected()
    def test_sample_outside(self):
        self.data["actions"][0]["reviewFramesSec"] = [0]
        self.rejected()
    def test_missing_identity(self):
        self.data["actions"][0]["objectId"] = ""
        self.rejected()
    def test_unknown_principle(self):
        self.data["actions"][0]["principles"] = ["make-it-cool"]
        self.rejected()
    def test_invalid_structure(self):
        self.assertTrue(validate([])[0])
        self.data["transitions"] = None
        self.rejected()
    def test_not_approval(self):
        errors, warnings = validate(self.data)
        self.assertFalse(errors)
        self.assertTrue(any("manually inspect" in x for x in warnings))

if __name__ == "__main__":
    unittest.main()
