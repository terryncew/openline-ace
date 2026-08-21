from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rcdl006.environment import MANUFACTURED_OPERATORS, NATIVE_OPERATORS, NUISANCE_OPERATORS
from rcdl006.fixtures import EXPERIMENT_ROOT, heldout_tasks, load_fixtures
from rcdl006.model import Split
from rcdl006.upstream import verify_upstream


class FixtureTests(unittest.TestCase):
    def test_fixture_counts_and_splits(self) -> None:
        fixtures = load_fixtures()
        self.assertEqual(len(fixtures.by_split(Split.DEVELOPMENT)), 6)
        self.assertEqual(len(fixtures.by_split(Split.EVALUATION)), 6)

    def test_active_and_sham_energy_are_equal(self) -> None:
        self.assertTrue(all(item.active_energy == item.sham_energy for item in load_fixtures().proposals))

    def test_mechanism_operators_are_wholly_held_out(self) -> None:
        fixtures = load_fixtures()
        dev = {layer for item in fixtures.by_split(Split.DEVELOPMENT) for layer in item.layers}
        final = {layer for item in fixtures.by_split(Split.EVALUATION) for layer in item.layers}
        self.assertFalse(dev & final)

    def test_evaluation_uses_compositions(self) -> None:
        fixtures = load_fixtures()
        self.assertTrue(all(len(item.layers) == 2 for item in fixtures.by_split(Split.EVALUATION)))

    def test_proposal_public_view_hides_operator_and_id(self) -> None:
        public = load_fixtures().proposals[0].public_view()
        self.assertEqual(set(public), {"candidate_clause", "proposal_digest"})

    def test_oracle_covers_each_mechanism_class(self) -> None:
        fixtures = load_fixtures()
        observed = {entry.standing.value for entry in fixtures.oracle.values()}
        self.assertEqual(observed, {"SUPPORTED_NATIVE", "REJECTED_IMPOSED", "REJECTED_NUISANCE"})

    def test_operator_sets_do_not_overlap(self) -> None:
        self.assertFalse(NATIVE_OPERATORS & MANUFACTURED_OPERATORS)
        self.assertFalse(NATIVE_OPERATORS & NUISANCE_OPERATORS)
        self.assertFalse(MANUFACTURED_OPERATORS & NUISANCE_OPERATORS)

    def test_heldout_tasks_are_deterministic_and_distinct(self) -> None:
        first = heldout_tasks()
        self.assertEqual(first, heldout_tasks())
        self.assertEqual(len({item.task_id for item in first}), 16)
        self.assertTrue(all(item.correct_patch != item.alternate_patch for item in first))

    def test_proposal_digest_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(EXPERIMENT_ROOT / "experiment_config.json", root)
            shutil.copytree(EXPERIMENT_ROOT / "references", root / "references")
            path = root / "references" / "frozen-proposals.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["proposals"][0]["candidate_clause"] += " tamper"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                load_fixtures(root)

    def test_upstream_source_surface_is_pinned(self) -> None:
        result = verify_upstream()
        self.assertTrue(result["verified"])
        self.assertEqual(result["source_files"], 5)

    def test_wrong_upstream_commit_is_rejected(self) -> None:
        source = EXPERIMENT_ROOT / "references" / "envharness-upstream.json"
        document = json.loads(source.read_text(encoding="utf-8"))
        document["commit"] = "0" * 40
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upstream.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "git commit"):
                verify_upstream(path)


if __name__ == "__main__":
    unittest.main()
