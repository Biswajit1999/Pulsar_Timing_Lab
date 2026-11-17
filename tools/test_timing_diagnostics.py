import math
import unittest
from timing_diagnostics import weighted_mean, dmx_delay_us

class TestTiming(unittest.TestCase):
    def test_weighted(self):
        d=weighted_mean([1,3],[1,1]); self.assertEqual(d['mean_us'],2); self.assertEqual(d['chi2'],2)
        self.assertAlmostEqual(d['formal_se_us'],1/math.sqrt(2))
    def test_dispersion(self):
        delay,error=dmx_delay_us(0.01,0.002,1000,2000)
        self.assertAlmostEqual(delay,4.148808e9*0.01*(1e-6-2.5e-7))
        self.assertAlmostEqual(error,abs(delay)*0.2)
    def test_invalid(self):
        with self.assertRaises(ValueError): weighted_mean([1],[0])
        with self.assertRaises(ValueError): dmx_delay_us(1,1,0)

if __name__=='__main__': unittest.main()
