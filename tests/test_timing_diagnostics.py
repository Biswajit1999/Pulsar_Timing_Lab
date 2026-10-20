"""Unit and scientific-contract tests; run: python -m unittest discover -s tests -v."""
import math
import unittest
from research.timing_diagnostics import (
    decimal_year_to_mjd, dmx_residual_association, lag_structure_function,
    residual_noise_summary,
)


def residual(t, y, s=1.0):
    return {"decimalYear": t, "residualMicroseconds": y, "uncertaintyMicroseconds": s}


class TimingDiagnosticsTests(unittest.TestCase):
    def test_weighted_scatter_constant(self):
        x = [residual(2000 + i, 2.0, .5) for i in range(3)]
        r = residual_noise_summary(x)
        self.assertAlmostEqual(r["weighted_mean_us"], 2.0)
        self.assertAlmostEqual(r["weighted_rms_us"], 0)
        self.assertAlmostEqual(r["reduced_chi2_descriptive"], 0)
        self.assertAlmostEqual(r["effective_weighted_count"], 3)

    def test_weighted_scatter_heteroscedastic(self):
        x = [residual(2000, 0, 1), residual(2001, 4, 2)]
        r = residual_noise_summary(x)
        self.assertAlmostEqual(r["weighted_mean_us"], .8)
        self.assertAlmostEqual(r["reduced_chi2_descriptive"], 3.2)

    def test_weighted_scatter_invalid_uncertainty(self):
        with self.assertRaises(ValueError):
            residual_noise_summary([residual(2000, 0, 0), residual(2001, 1)])

    def test_structure_function_known_pairs(self):
        x = [residual(2000, 0, .5), residual(2000 + 1/365.25, 2, .5), residual(2000 + 2/365.25, 4, .5)]
        r = lag_structure_function(x, [0, 1.5, 3.5])
        self.assertEqual([b["pairs"] for b in r], [2, 1])
        self.assertAlmostEqual(r[0]["raw_sf_us2"], 4)
        self.assertAlmostEqual(r[0]["noise_subtracted_sf_us2"], 3.5)
        self.assertAlmostEqual(r[1]["noise_subtracted_sf_us2"], 15.5)

    def test_structure_function_preserves_negative(self):
        x = [residual(2000, 0, 3), residual(2000 + 1/365.25, 0, 3)]
        self.assertAlmostEqual(lag_structure_function(x, [0, 2])[0]["noise_subtracted_sf_us2"], -18)

    def test_structure_function_empty_bin(self):
        x = [residual(2000, 0), residual(2001, 1)]
        self.assertIsNone(lag_structure_function(x, [0, 1])[0]["raw_sf_us2"])

    def test_decimal_year_leap_day(self):
        self.assertAlmostEqual(decimal_year_to_mjd(2000.5) - decimal_year_to_mjd(2000), 183)
        self.assertAlmostEqual(decimal_year_to_mjd(2001.5) - decimal_year_to_mjd(2001), 182.5)

    def test_dmx_matching_regression(self):
        years = [2000, 2001, 2002, 2003]
        dm = [.1, .2, .3, .4]
        residuals = [residual(y, 1 + 2*d, .1) for y,d in zip(years, dm)]
        windows = [{"mjdStart":decimal_year_to_mjd(y)-1,"mjdEnd":decimal_year_to_mjd(y)+1,"dmxPcCm3":d} for y,d in zip(years,dm)]
        result = dmx_residual_association(residuals, windows)
        self.assertEqual(result["matched_dmx_bins"], 4)
        self.assertAlmostEqual(result["slope_us_per_pc_cm3"], 2)
        self.assertAlmostEqual(result["intercept_us"], 1)

    def test_dmx_overlap_excluded(self):
        t=decimal_year_to_mjd(2000)
        windows=[{"mjdStart":t-1,"mjdEnd":t+1,"dmxPcCm3":i} for i in (0,1)]
        result=dmx_residual_association([residual(2000,0)],windows)
        self.assertEqual(result["ambiguous_residuals"],1)
        self.assertEqual(result["matched_residuals"],0)

    def test_dmx_no_extrapolation(self):
        t=decimal_year_to_mjd(2000)
        result=dmx_residual_association([residual(2001,0)], [{"mjdStart":t-1,"mjdEnd":t+1,"dmxPcCm3":.1}])
        self.assertEqual(result["unassigned_residuals"],1)
        self.assertIsNone(result["slope_us_per_pc_cm3"])

if __name__ == "__main__": unittest.main()
