# NANOGrav timing diagnostics

Run from the tools directory: `python -m unittest -v test_timing_diagnostics.py`.

The module computes a diagonal-error weighted residual mean and chi-square and converts published DMX offsets to differential cold-plasma delays with DM-only formal uncertainty. `load_release_diagnostics` reads the existing unchanged NANOGrav 11-year JSON bundle. No timing-model refit, detection significance or gravitational-wave inference is performed. Residual errors may be correlated; a diagonal-error chi-square is not a calibrated goodness-of-fit statistic in that case. DMX offsets are relative and not absolute DM. Frequency uncertainty and covariances are omitted. Synthetic tests only; observational interpretation requires original TOAs and timing models.

AI-assisted code preparation and testing were used; scientific interpretation and review remain the repository owner's responsibility.
