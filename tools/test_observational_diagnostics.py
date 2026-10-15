"""Deterministic unit tests for released-data descriptive diagnostics."""
import math
import unittest
from observational_diagnostics import (
    weighted_residual_summary, lag_structure_function, weighted_dmx_trend,
    analyze_product,
)


class TestDiagnostics(unittest.TestCase):
    def test_weighted_constant(self):
        r = weighted_residual_summary([0,1,2], [1,2,3], [1,1,1])
        self.assertAlmostEqual(r['weighted_mean_us'], 2)
        self.assertAlmostEqual(r['chi2_about_constant'], 2)
        self.assertAlmostEqual(r['kish_effective_weight_count'], 3)

    def test_weight_rescaling(self):
        a = weighted_residual_summary([0,1,2], [1,2,3], [1,1,1])
        b = weighted_residual_summary([0,1,2], [1,2,3], [2,2,2])
        self.assertAlmostEqual(a['weighted_rms_us'], b['weighted_rms_us'])
        self.assertAlmostEqual(a['chi2_about_constant'], 4*b['chi2_about_constant'])

    def test_structure_function(self):
        x = lag_structure_function([0,1,2], [0,1,2], [0.1]*3, [0,1.5,3])
        self.assertEqual([v['pairs'] for v in x], [2,1])
        self.assertAlmostEqual(x[0]['mean_squared_difference_us2'], 1)
        self.assertAlmostEqual(x[1]['mean_squared_difference_us2'], 4)

    def test_empty_lag_bin(self):
        r = lag_structure_function([0,2], [0,1], [1,1], [0,1,3])
        self.assertIsNone(r[0]['mean_squared_difference_us2'])
        self.assertEqual(r[1]['pairs'], 1)

    def test_linear_dmx(self):
        t = [50000.,50001.,50002.,50003.]
        d = [0.2 + 0.03*(v-50000) for v in t]
        r = weighted_dmx_trend(t,d,[0.01]*4)
        self.assertAlmostEqual(r['slope_pc_cm3_per_day'],0.03)
        self.assertAlmostEqual(r['reduced_chi2_independence_only'],0,places=20)

    def test_no_leverage(self):
        with self.assertRaises(ValueError):
            weighted_dmx_trend([1,1,1],[1,2,3],[1,1,1])

    def test_reject_invalid(self):
        with self.assertRaises(ValueError):
            weighted_residual_summary([0,1],[1,2],[1,0])
        with self.assertRaises(ValueError):
            lag_structure_function([0,1],[0,1],[1,1],[0,2,1])

    def test_end_to_end_fixture(self):
        r = [{'decimalYear':2000.+i,'residualMicroseconds':float(i),
              'uncertaintyMicroseconds':1.} for i in range(4)]
        d = [{'mjd':50000.+i,'dmxPcCm3':0.01*i,
              'uncertaintyPcCm3':0.001} for i in range(4)]
        out = analyze_product({'provenance':{'sourceArchive':'fixture'},
                               'pulsars':{'PSR-TEST':{'residuals':r,'dmx':d}}})
        self.assertEqual(out['pulsars']['PSR-TEST']['weighted_residuals']['n'],4)
        self.assertAlmostEqual(out['pulsars']['PSR-TEST']['dmx_linear_diagnostic']['slope_pc_cm3_per_day'],0.01)


if __name__ == '__main__':
    unittest.main()
