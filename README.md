# Pulsar Timing Lab

**An observation-first browser instrument for NANOGrav timing residuals, dispersion-measure
variations and controlled pulsar perturbation experiments.**

Pulsar Timing Lab presents published NANOGrav 11-year data products before any generated
quantity. The primary plots are released daily-average timing residual samples and released
DMX values for selected millisecond pulsars. A deliberately separate simulation overlay adds
rotational phase, cold-plasma dispersion calculations, red/white timing noise and optional
frequency-step glitches without being confused for telescope data.

## Observational Data Product

The bundled observation asset is derived from the official NANOGrav archive:

```text
https://data.nanograv.org/static/data/res_dmx_nanograv_11y.tgz
```

The asset builder reads the archive members `res_ave/<pulsar>.ares` and
`dmx_vals/<pulsar>.dmx` for:

| Pulsar | Released residual samples | Released DMX bins |
| --- | ---: | ---: |
| J1713+0747 | 789 | 209 |
| J1909-3744 | 451 | 166 |
| B1937+21 | 460 | 165 |

No timing-model fit or subtraction is performed by this application. Released residual
values, uncertainties, telescope labels, backends and observing bands are preserved in the
JSON bundle and CSV export. Residual epochs are supplied by the release as decimal years; the
plot computes a fractional-calendar-year MJD only for its display axis and retains the
original decimal year for export. DMX epochs are plotted directly from the released MJD
values.

NANOGrav explicitly cautions that timing residuals depend on the fitted timing model. New
astrophysical inference must re-fit original pulse arrival times and timing-model parameters,
rather than treating these plotted residual values as model-independent measurements.

## Instrument Capabilities

- NANOGrav timing-residual display with reported uncertainty envelope and data playback cursor.
- NANOGrav DMX time series with reported uncertainties and native MJD epochs.
- Selection of three published high-precision pulsars from the bundled release product.
- Optional amber simulation overlay, off by default and visually distinguished from observations.
- Quadratic spin-phase model with editable period and frequency derivative.
- Cold-plasma band-delay calculator using explicit MHz/second units.
- Fourier-synthesised red timing-noise and independent white-noise injections.
- Optional sudden rotational glitch represented by a fractional frequency step.
- Worker-generated CSV export preserving observational columns and, when enabled, separate
  simulated-injection columns.
- Zero-build static deployment with a dedicated numerical Web Worker and Canvas rendering loop.

## Architecture

```text
Pulsar Timing Lab/
  index.html
  assets/
    css/style.css
    js/app.js                       Canvas rendering and data controls
    js/physicsWorker.js             Data loading and optional physical model
  data/observations/
    nanograv_11yr_residuals.json   Browser observation bundle
    nanograv_11yr_source_metadata.json
    res_dmx_nanograv_11y.tgz       Retrieved official source archive
  docs/
    equations.md
    validation.md
  tools/
    fetch_nanograv_observations.py
    generate_synthetic_toas.py
    validate_model.py
    validate_observations.py
```

All JSON loading, numerical arrays, stochastic generation, glitch calculation and export
assembly occur in `assets/js/physicsWorker.js`. The main thread performs input handling and
device-pixel-ratio-aware Canvas draws. It never invents a replacement data series if the
observation asset is unavailable.

## Optional Physics Overlay

The overlay is explicitly a comparison/injection model and is disabled on initial load.

### Rotational phase

```text
N(t) = N0 + nu (t - t0) + 0.5 nudot (t - t0)^2
```

Here `N` is rotational phase in cycles, `nu` is frequency in `Hz`, and `nudot` is in
`Hz s^-1`. The optional overlay is sampled at the released residual epochs.

### Sudden glitch

```text
Delta nu = nu (Delta nu / nu)
Delta N(t) = Delta nu (t - t_g),  t >= t_g
R_glitch(t) = -Delta N(t) / nu_model(t)
```

A positive frequency step produces negative post-event `O-C` residuals when the model omits
the event.

### Cold-plasma dispersion calculator

```text
Delta t = D DM (nu_low^-2 - nu_high^-2)
D = 4.148808e3 s MHz^2 pc^-1 cm^3
```

With receiver frequencies in `MHz` and `DM` in `pc cm^-3`, the result is calculated in
seconds and displayed in milliseconds. This calculator does not claim to reconstruct a
frequency-time observation absent from the NANOGrav residual/DMX release.

### Timing-noise injection

The optional red-noise series is a finite Fourier construction with modal amplitude scaling:

```text
A(k) proportional to k^(-gamma / 2)
```

It is normalised to the selected RMS before independent Gaussian white noise is added.

## Running The Instrument

Serve the directory over HTTP so that the browser can load the Worker and local data asset:

```bash
python -m http.server 8000
```

Open `http://localhost:8000/`. Once the observation JSON is present, operation does not
require network access or a build step.

To recreate the bundled observation JSON from the official archive:

```bash
python tools/fetch_nanograv_observations.py
```

This acquisition step requires internet access.

## CSV Export

With the simulation overlay disabled, `EXPORT DATA` contains:

```text
pulsar,decimal_year,display_mjd,telescope,backend,band,
released_residual_us,released_uncertainty_us
```

When the overlay is enabled, two clearly labelled columns are appended:

```text
simulated_injection_us,simulated_glitch_component_us
```

## Verification

Run the observation integrity check and the analytic model invariant tests:

```bash
python tools/validate_observations.py
python tools/generate_synthetic_toas.py
python tools/validate_model.py
```

The validation protocol is described in `docs/validation.md`. Passing these checks confirms
asset structure and declared numerical conventions; it is not a timing-solution fit.

## References

Arzoumanian, Z. et al. (2018) 'The NANOGrav 11-year data set: High-precision timing of 45
millisecond pulsars', *The Astrophysical Journal Supplement Series*, 235(2), p. 37.
doi: [10.3847/1538-4365/aab5b0](https://doi.org/10.3847/1538-4365/aab5b0).

Lorimer, D.R. and Kramer, M. (2005) *Handbook of Pulsar Astronomy*. Cambridge:
Cambridge University Press.

Hobbs, G.B., Edwards, R.T. and Manchester, R.N. (2006) 'TEMPO2, a new pulsar-timing
package-I. An overview', *Monthly Notices of the Royal Astronomical Society*, 369(2),
pp. 655-672.

## Licence

Application source is released under the MIT Licence; see `LICENSE`. The NANOGrav data
product retains its source-release attribution and provenance.
