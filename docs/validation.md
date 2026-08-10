# Validation Protocol

## Observation Asset Integrity

Run:

```bash
python tools/validate_observations.py
```

The validator checks that the compact bundle identifies the official NANOGrav archive, includes
the three configured pulsars, has finite residual and DMX values with positive uncertainties,
preserves ordered epochs and contains the expected sample counts.

## Analytic Overlay Checks

Run:

```bash
python tools/generate_synthetic_toas.py
python tools/validate_model.py
```

The independent model checks verify the quadratic rotational phase expression, zero-DM
collapse, linear scaling of dispersion delay with DM, explicit seconds-to-milliseconds unit
conversion and proportional isolated glitch residual response.

## Interactive Checks

| Manipulation | Expected instrument response |
| --- | --- |
| Load the application without enabling the overlay | Cyan NANOGrav residuals and DMX values appear; the profile panel states that the overlay is disabled. |
| Change `PULSAR` | The observed residual and DMX counts change to the selected release product. |
| Select `EXPORT DATA` with overlay off | CSV contains released residual values and uncertainties, with no simulated columns. |
| Enable `SIMULATION OVERLAY` | An amber injection trace and simulated pulse template appear without replacing the cyan observations. |
| Set overlay `DM` to zero | The model dispersion telemetry reports zero delay. |
| Enable a glitch and raise `DELTA NU / NU` | The amber post-event residual trend increases proportionally and the magenta model-event marker appears. |
| Select `RESEED MODEL` | Only the optional stochastic injection changes; NANOGrav products remain fixed. |

## Interpretation Boundary

Validation demonstrates preservation of the bundled release table and internal consistency of
the optional model. It does not validate an astrophysical timing solution. The NANOGrav release
itself cautions that timing residuals depend on the fitted timing model; publication analysis
requires refitting timing measurements with the required timing and noise parameters.
