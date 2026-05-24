# Pulsar Timing Lab

Interactive browser laboratory for pulsar pulse folding, timing residuals, dispersion delay, and glitch signatures.

**Author:** Biswajit Jana

## Research Motivation

Pulsars are rapidly rotating neutron stars whose radio pulses can act as high-precision astrophysical clocks. Small deviations in pulse arrival times can encode spin-down, timing noise, orbital motion, interstellar dispersion, and sudden rotational glitches. This project provides an interactive, research-style visual laboratory for understanding how simplified pulsar timing effects appear in folded profiles, timing residuals, and radio frequency-time plots.

## Scientific Background

The lab models a pulsar as a rotating phase clock with a narrow emission beam. Observed pulse times of arrival are compared with a simplified timing model. A dispersion measure term demonstrates how the ionised interstellar medium delays lower radio frequencies more strongly than higher frequencies. A glitch term introduces a sudden fractional spin-frequency jump after a selected epoch.

This first version is an educational and exploratory simulator. It is not a replacement for timing packages such as TEMPO, TEMPO2, PINT, or enterprise-grade pulsar timing array pipelines.

## Core Model

The rotational phase is approximated as:

```text
N(t) = N0 + nu (t - t0) + 0.5 nudot (t - t0)^2
```

The dispersion delay between two observing frequencies is:

```text
Delta t_ms = 4.148808e3 DM (nu_low^-2 - nu_high^-2)
```

where `DM` is in `pc cm^-3` and frequency is in `MHz`.

Timing residuals are shown as:

```text
R = TOA_observed - TOA_model
```

The glitch model is represented as:

```text
nu -> nu + Delta nu
Delta nu / nu = glitch_ppm * 1e-6
```

If a frequency step is left unmodelled, the leading residual trend after the glitch epoch is approximated as:

```text
R_glitch ~= - (Delta nu / nu) (t - tg)
```

## Main Features

- Interactive folded pulse profile with pulse width control.
- Timing residual plot with spin-down, stochastic timing noise, and glitch signature.
- Frequency-time waterfall showing cold plasma dispersion delay.
- Sliders for period, pulse width, spin-down, duration, cadence, noise, DM, centre frequency, bandwidth, glitch epoch, and glitch size.
- Export of synthetic time-of-arrival data as CSV.
- Static HTML/CSS/JavaScript implementation suitable for GitHub Pages.

## Research Use Cases

- Teaching how pulse phase, TOAs, residuals, dispersion, and glitches connect in a timing workflow.
- Generating lightweight synthetic timing residuals for testing plotting, outlier handling, and residual diagnostics.
- Demonstrating why real pulsar timing requires barycentric corrections, propagation delays, clock standards, and fitted timing models.
- Serving as a front-end concept prototype before integrating a validated timing engine such as PINT or TEMPO2.

## Project Structure

```text
Pulsar Timing Lab/
  index.html
  README.md
  LICENSE
  assets/
    css/
      style.css
    js/
      app.js
  docs/
    equations.md
    validation.md
    image_prompt.md
```

## README Image Prompt

A README hero image prompt is provided in [`docs/image_prompt.md`](docs/image_prompt.md). It is written for generating a polished scientific visual that can be added later as a repository banner.

## Running Locally

Open `index.html` in a browser. No build step is required.

Optional Python data generation and validation:

```bash
python tools/generate_synthetic_toas.py
python tools/validate_model.py
```

## Validation Plan

- Set glitch size to zero and verify that the residual curve no longer contains a post-epoch step.
- Set dispersion measure to zero and verify that the waterfall pulse aligns vertically.
- Increase bandwidth at fixed DM and verify that the frequency-dependent delay increases.
- Increase timing noise and verify that RMS residuals increase.
- Confirm that exported CSV rows match the plotted synthetic residual points.

## Limitations

- Uses a simplified phase model and illustrative noise model.
- Does not include barycentric correction, binary orbital timing, Shapiro delay, Einstein delay, profile evolution, scintillation, calibration errors, or telescope/backend response.
- Glitch recovery is not yet modelled.
- The simulated data are synthetic and should not be interpreted as measurements of a real pulsar.

## Research References

- Edwards, Hobbs & Manchester, 2006, *TEMPO2, a new pulsar timing package. II: The timing model and precision estimates*.
- Hobbs, Edwards & Manchester, 2006, *TEMPO2, a new pulsar-timing package. I: An overview*.
- Lorimer & Kramer, 2005, *Handbook of Pulsar Astronomy*.
- Keith et al., 2013, work on dispersion-measure corrections in precision pulsar timing.

## Future Upgrades

- Add binary pulsar Roemer delay and orbital parameter controls.
- Add glitch recovery with exponential relaxation.
- Add period search and phase folding from generated photon/event streams.
- Add a Python notebook validating the browser model.
- Add real public pulsar catalogue examples with proper citations.
- Add mobile-optimised export and screenshot tools.

## Suggested GitHub Topics

`astrophysics`, `pulsars`, `neutron-stars`, `timing`, `signal-processing`, `radio-astronomy`, `scientific-visualisation`, `javascript`, `github-pages`, `simulation`
