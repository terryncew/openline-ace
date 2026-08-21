import unittest

from aca001.stats import paired_bootstrap_mean_ci


class StatsTests(unittest.TestCase):
    def test_deterministic_bootstrap(self):
        a = paired_bootstrap_mean_ci([1, 1, 0, 1] * 20, samples=1000, alpha=0.05, seed_material="x")
        b = paired_bootstrap_mean_ci([1, 1, 0, 1] * 20, samples=1000, alpha=0.05, seed_material="x")
        self.assertEqual(a, b)

    def test_zero_delta_is_exact(self):
        mean, low, high = paired_bootstrap_mean_ci([0] * 64, samples=1000, alpha=0.05, seed_material="zero")
        self.assertEqual((mean, low, high), (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
