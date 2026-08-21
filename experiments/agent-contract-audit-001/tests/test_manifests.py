import unittest

from aca001.conformance import run_conformance
from aca001.manifests import reduce_supported


class ManifestTests(unittest.TestCase):
    def test_only_supported_fixture_emits_manifest(self):
        result = run_conformance()
        manifests = reduce_supported(result["candidates"], result["audit"]["grades"])
        self.assertEqual([m["candidate_id"] for m in manifests], ["validated-artifact-binding"])
        self.assertFalse(manifests[0]["compiler_eligible"])
        self.assertEqual(manifests[0]["policy_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
