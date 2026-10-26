import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from timing_robustness import gls_trend,leave_block_out_trends,dmx_band_delay

class TimingRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.t=np.linspace(0,9,40)
        self.y=.02+.003*self.t
        self.s=np.linspace(.001,.002,40)
    def test_gls_exact_slope(self):
        fit=gls_trend(self.t,self.y,self.s)
        self.assertAlmostEqual(fit['slope'],.003,places=12)
        self.assertLess(fit['chi2'],1e-20)
    def test_gls_correlated_slope_exact(self):
        fit=gls_trend(self.t,self.y,self.s,correlated_rms=.002,correlation_timescale=1)
        self.assertAlmostEqual(fit['slope'],.003,places=12)
    def test_correlated_noise_inflates_slope_sigma(self):
        independent=gls_trend(self.t,self.y,self.s)
        correlated=gls_trend(self.t,self.y,self.s,correlated_rms=.003,correlation_timescale=2)
        self.assertGreater(correlated['slope_sigma_conditional'],independent['slope_sigma_conditional'])
    def test_gls_time_translation(self):
        a=gls_trend(self.t,self.y,self.s,correlated_rms=.001)
        b=gls_trend(self.t+60000,self.y,self.s,correlated_rms=.001)
        self.assertAlmostEqual(a['slope'],b['slope'],places=11)
    def test_gls_bad_sigma(self):
        with self.assertRaises(ValueError): gls_trend([0,1,2],[0,1,2],[1,0,1])
    def test_gls_bad_hyperparameters(self):
        with self.assertRaises(ValueError): gls_trend(self.t,self.y,self.s,correlated_rms=-1)
    def test_block_deletion_exact_linear(self):
        result=leave_block_out_trends(self.t,self.y,self.s,block_width=2)
        self.assertEqual(len(result['deleted_blocks']),5)
        self.assertLess(result['max_abs_slope_change'],1e-12)
    def test_block_deletion_detects_outlier_block(self):
        y=self.y.copy();y[self.t<2]+=.01
        result=leave_block_out_trends(self.t,y,self.s,block_width=2)
        self.assertGreater(result['max_abs_slope_change'],1e-4)
    def test_block_width_invalid(self):
        with self.assertRaises(ValueError): leave_block_out_trends(self.t,self.y,self.s,block_width=0)
    def test_band_delay_zero_dm(self):
        self.assertEqual(dmx_band_delay(0,.01,400,800)['delay_seconds'],0)
    def test_band_delay_scaling(self):
        a=dmx_band_delay(.001,.0001,400,800)
        b=dmx_band_delay(.002,.0002,400,800)
        self.assertAlmostEqual(b['delay_seconds']/a['delay_seconds'],2)
        self.assertAlmostEqual(b['sigma_seconds']/a['sigma_seconds'],2)
    def test_band_delay_sign_and_validation(self):
        self.assertLess(dmx_band_delay(-.01,.001,400,800)['delay_seconds'],0)
        with self.assertRaises(ValueError): dmx_band_delay(.01,.001,800,400)

if __name__=='__main__':unittest.main()
