#!/usr/bin/env python3

import unittest

import numpy as np

from problem_blocked_replay_multiplicity import (
    FAMILIES,
    adjust_pvalues,
    canonical_null_histograms,
    empirical_pvalue,
)


class ProblemBlockedMultiplicityTests(unittest.TestCase):
    def test_bh_adjustment_matches_known_example(self) -> None:
        adjusted = adjust_pvalues([0.01, 0.04, 0.03], "BH")
        np.testing.assert_allclose(adjusted, [0.03, 0.04, 0.04])

    def test_by_is_never_less_conservative_than_bh(self) -> None:
        pvalues = [0.001, 0.01, 0.2, 0.8]
        bh = adjust_pvalues(pvalues, "BH")
        by = adjust_pvalues(pvalues, "BY")
        self.assertTrue(all(by_value >= bh_value for bh_value, by_value in zip(bh, by)))

    def test_degenerate_null_has_only_zero_effect(self) -> None:
        permutations = 1_000
        histograms = canonical_null_histograms(
            (0, 0, 0, 0, 0),
            wrong_count=3,
            permutations=permutations,
            seed=7,
            batch_size=100,
        )
        for family in FAMILIES:
            self.assertEqual(int(histograms[family].sum()), permutations)
            self.assertEqual(int(histograms[family][10]), permutations)

    def test_empirical_pvalue_uses_plus_one_correction(self) -> None:
        histogram = np.zeros(21, dtype=np.int64)
        histogram[10] = 1_000
        self.assertAlmostEqual(
            empirical_pvalue(histogram, observed=1, permutations=1_000),
            1.0 / 1_001.0,
        )


if __name__ == "__main__":
    unittest.main()
