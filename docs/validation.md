# Validation Notes

## Internal Consistency Checks

1. **Zero dispersion**

   Set `Dispersion measure = 0`. The frequency-time sweep should collapse into a nearly vertical pulse because there is no cold plasma delay.

2. **Bandwidth scaling**

   Increase bandwidth while keeping centre frequency and DM fixed. The low-frequency edge should arrive later relative to the high-frequency edge.

3. **Zero glitch**

   Set `Frequency jump = 0 ppm`. The residual plot should no longer show the post-glitch systematic drift.

4. **Noise scaling**

   Increase `Timing noise`. The RMS residual summary should increase.

5. **CSV export**

   Export synthetic TOAs and confirm that the `residual_ms` values correspond to the plotted timing residuals.

6. **Unmodelled glitch scaling**

   Doubling the frequency jump should double the post-glitch residual slope because `R_glitch ~= -(Delta nu / nu)(t - tg)`.

## Scientific Scope

The simulator is intended for conceptual exploration and portfolio demonstration. It should not be used for pulsar parameter inference or publication-grade timing analysis without replacing the simplified model with a validated timing engine.
