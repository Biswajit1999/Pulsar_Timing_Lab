# NANOGrav 11-year: residual and DMX diagnostics

Three **descriptive**, offline Python analyses using the already-bundled NANOGrav 11-year residual/DMX JSON:

1. **Uncertainty-weighted residual scatter** — inverse-variance mean, WRMS, effective sample size, median/MAD and a *descriptive* reduced chi-square. Correlations and timing-model fitting invalidate a naïve independent-Gaussian p-value.
2. **Irregular-lag structure function** — pairwise residual differences in user-specified lag bins, with the sum of quoted variances subtracted. Negative noise-corrected values are intentionally retained. Pairs are not statistically independent; the 365.25-day decimal-year conversion is approximate.
3. **Residual–DMX association** — converts decimal calendar years to approximate MJD, matches only residuals inside released DMX windows, excludes overlapping ambiguous assignments and reports matched/unmatched counts. A weighted regression of per-window residual means on released DMX is a *diagnostic*, not a dispersion-law measurement: the published residuals already depend on a fitted timing model including DMX.

Run from the repository root:

```sh
python -m unittest discover -s tests -p 'test_timing_diagnostics.py' -v
python -m research.run_timing_diagnostics --output results/timing_diagnostics
```

The script does not edit observational assets, does not invent observations and does not refit pulse arrival times. The NANOGrav release explicitly cautions that inference of new physical parameters requires jointly refitting the timing model. Original provenance remains in the generated summary.

**Data:** NANOGrav 11-year residual/DMX release, Arzoumanian et al. (2018), ApJS 235, 37. Source archive listed in `data/observations/nanograv_11yr_residuals.json`.
