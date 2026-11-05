import unittest
import numpy as np
from phase_robustness import weighted_phase_fit, chromatic_delay

class TestTiming(unittest.TestCase):
    def test_exact_recovery(self):
        t = np.linspace(0, 40, 100)
        x = (t - t.mean()) / np.ptp(t)
        y = 2 + .3*x + .7*np.sin(2*np.pi*t/9) - .2*np.cos(2*np.pi*t/9)
        c, cov, chi2 = weighted_phase_fit(t,y,np.full(len(t),.1),9)
        np.testing.assert_allclose(c,[2,.3,.7,-.2],atol=1e-12)
        self.assertLess(chi2,1e-20)
        self.assertTrue(np.all(np.linalg.eigvalsh(cov)>0))
    def test_sigma_scaling(self):
        t=np.linspace(0,40,80); y=np.sin(2*np.pi*t/8)
        a=weighted_phase_fit(t,y,np.ones(len(t)),8)[1]
        b=weighted_phase_fit(t,y,2*np.ones(len(t)),8)[1]
        np.testing.assert_allclose(b,4*a)
    def test_dispersion_scaling(self):
        self.assertAlmostEqual(chromatic_delay(1,500)/chromatic_delay(1,1000),4)
        self.assertAlmostEqual(chromatic_delay(1,500,1000),chromatic_delay(1,500)-chromatic_delay(1,1000))
    def test_rank_guard(self):
        with self.assertRaises(ValueError):
            weighted_phase_fit(np.zeros(10),np.zeros(10),np.ones(10),3)
if __name__=='__main__': unittest.main()
