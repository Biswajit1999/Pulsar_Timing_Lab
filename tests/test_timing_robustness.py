import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from timing_robustness import weighted_trend, diagonal_excess_scatter, pair_structure_function


class TimingRobustnessTests(unittest.TestCase):
    def test_trend_recovers_injected_slope(self):
        t=np.linspace(55000,57000,80); y=0.7+2.5*(t-56000); s=np.linspace(.2,.8,len(t))
        fit=weighted_trend(t,y,s)
        self.assertAlmostEqual(fit['slope'],2.5,places=11)
        self.assertAlmostEqual(fit['chi2'],0,places=15)
    def test_trend_heteroscedastic_uncertainty(self):
        t=np.array([0.,1.,2.,3.]); s=np.array([.1,.2,.3,.4]); y=np.array([1.,2.,3.,4.])
        fit=weighted_trend(t,y,s)
        expected=1/np.sqrt(np.sum(((t-np.average(t,weights=1/s**2))/s)**2))
        self.assertAlmostEqual(fit['slope_sigma'],expected)
    def test_trend_translation_invariance(self):
        t=np.linspace(0,10,30); y=3+0.4*t+np.sin(t)*.01;s=np.ones(30)
        self.assertAlmostEqual(weighted_trend(t,y,s)['slope'],weighted_trend(t+60000,y,s)['slope'],places=11)
    def test_trend_rejects_degenerate_epochs(self):
        with self.assertRaises(ValueError): weighted_trend([1,1,1],[1,2,3],[1,1,1])
    def test_rejects_invalid_uncertainty(self):
        with self.assertRaises(ValueError): weighted_trend([1,2,3],[1,2,3],[1,0,1])
    def test_excess_scatter_zero_when_overestimated(self):
        out=diagonal_excess_scatter([1,2,1,2],[10]*4)
        self.assertEqual(out['extra_rms'],0)
    def test_excess_scatter_exact_equal_sigma(self):
        y=np.array([-3.,-1.,1.,3.]); s=np.ones(4)
        out=diagonal_excess_scatter(y,s)
        self.assertAlmostEqual(out['extra_rms'],np.sqrt(np.sum((y-np.mean(y))**2)/3-1),places=7)
        self.assertAlmostEqual(out['final_reduced_chi2'],1,places=7)
    def test_excess_scatter_invalid(self):
        with self.assertRaises(ValueError): diagonal_excess_scatter([1,2,3],[1,0,1])
    def test_structure_noise_subtraction(self):
        out=pair_structure_function([0,1,2],[0,1,2],[.1]*3,[0,1.5,3])
        self.assertEqual([b['pairs'] for b in out],[2,1])
        self.assertAlmostEqual(out[0]['noise_subtracted_mean_square'],.98)
        self.assertAlmostEqual(out[1]['noise_subtracted_mean_square'],3.98)
    def test_structure_empty_bins(self):
        out=pair_structure_function([0,1,2],[1,2,3],[.1]*3,[0,.5,1.5])
        self.assertIsNone(out[0]['noise_subtracted_mean_square'])
    def test_structure_invalid_edges(self):
        with self.assertRaises(ValueError): pair_structure_function([0,1,2],[0,1,2],[1]*3,[0,2,1])


if __name__ == '__main__': unittest.main()
