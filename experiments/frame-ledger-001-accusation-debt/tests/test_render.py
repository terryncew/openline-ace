import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("render", ROOT / "src" / "render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT / "data" / "cases.json").read_text())[0]

    def test_explicit_revocation_marks_accusation_withdrawn(self):
        prompt = render.render_case(self.case, "explicit_revocation")
        self.assertIn("[A] STANDING: WITHDRAWN", prompt)
        self.assertIn("[E1] STANDING: ACTIVE", prompt)
        self.assertIn("[R] STANDING: ACTIVE", prompt)

    def test_defense_arms_change_tone_not_case_evidence(self):
        calm = render.render_case(self.case, "calm_defense")
        angry = render.render_case(self.case, "angry_defense")
        for eid, text in self.case["evidence"]:
            self.assertIn(text, calm)
            self.assertIn(text, angry)
        self.assertIn(self.case["calm_defense"], calm)
        self.assertIn(self.case["angry_defense"], angry)

    def test_seeded_render_is_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            a = pathlib.Path(td) / "a.jsonl"
            b = pathlib.Path(td) / "b.jsonl"
            cmd = [sys.executable, str(ROOT / "src" / "render.py"), "--seed", "42"]
            subprocess.check_call(cmd + ["--out", str(a)])
            subprocess.check_call(cmd + ["--out", str(b)])
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
