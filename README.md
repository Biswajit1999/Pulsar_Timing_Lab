# Pulsar Timing Lab

**An observation-first browser instrument for NANOGrav timing residuals, dispersion-measure
variations and controlled pulsar perturbation experiments.**

Pulsar Timing Lab presents published NANOGrav 11-year data products before any generated
quantity. The primary plots are released daily-average timing residual samples and released
DMX values for selected millisecond pulsars. A deliberately separate simulation overlay adds
rotational phase, cold-plasma dispersion calculations, red/white timing noise and optional
frequency-step glitches without being confused for telescope data.

## Scientific Background

### Pulsars as rotating neutron stars

Pulsars are rapidly rotating, highly magnetised neutron stars left behind by the core collapse
of massive stars. Charged particles accelerated along the magnetic axis produce beamed radio
emission that sweeps past Earth once per rotation, like a lighthouse. Millisecond pulsars — the
class this lab focuses on — have been spun up by accretion in a binary system to rotation
periods of a few milliseconds and rotational stability that rivals atomic clocks, which is what
makes precision timing experiments possible in the first place.

### Pulse folding and times of arrival (TOAs)

A single rotation is far too faint to detect individually. Pulsar timing observations fold many
successive rotations, modulo the topocentric rotation period, into a high signal-to-noise
integrated pulse profile. Cross-correlating that profile against a standard template yields a
single time of arrival (TOA) for the observation, referenced to a fiducial point on the profile
and, after barycentring, to the Solar System barycentre. A timing campaign accumulates TOAs over
years, each with an estimated uncertainty set by profile signal-to-noise and pulse sharpness.

### The timing model and residuals

A timing model predicts the rotational phase of the pulsar at the epoch of every TOA, from a
spin frequency `nu`, its time derivatives, an astrometric position and, for binaries, orbital
parameters. Subtracting the nearest integer number of predicted rotations from each observed TOA
leaves a fractional-phase mismatch — the **timing residual** — usually reported as "observed
minus computed" (O−C) in microseconds. A well-fitted model produces residuals scattered around
zero at the level of the TOA uncertainties; structure remaining in the residuals (trends,
periodicities, steps) signals unmodelled physics: proper motion, orbital companions,
interstellar-medium variation, red spin noise, or glitches. This lab deliberately keeps the
NANOGrav-released residuals as the ground truth product and never re-fits or subtracts a new
model from them (see Observational Data Product below); it only shows what an *additional*
unmodelled effect would look like superimposed on that residual space.

### Dispersion delay across radio frequencies

Radio pulses travel through the ionised interstellar medium, a cold plasma that is dispersive:
lower radio frequencies are delayed more than higher ones. The delay between two observing
frequencies is proportional to the integrated electron column density along the line of sight,
the dispersion measure (DM), and to the inverse square of frequency. Because interstellar
electron density along the line of sight varies as the pulsar, its wind, and the Earth all move,
DM itself drifts over time; NANOGrav publishes this as a DMX time series — a set of DM offsets
estimated independently in short time bins. Left uncorrected, DM variation produces
frequency-dependent, non-stationary timing noise that masks other signals.

### Pulsar glitches

Some pulsars, especially young ones and a subset of millisecond pulsars, occasionally undergo a
**glitch**: a sudden, discontinuous increase in rotation frequency (`Delta nu / nu` typically
`1e-9` to `1e-6`), usually followed by a partial recovery over days to years. Glitches are
attributed to sudden angular-momentum transfer between the rigid crust and a more weakly coupled
superfluid interior. In an O−C residual series, an unmodelled glitch appears as a sudden
downward kink that grows approximately linearly with time after the glitch epoch, because the
timing model keeps predicting the pre-glitch spin-down while the star is now rotating faster.

### Pulsar timing arrays and gravitational waves

Millisecond pulsars are stable enough that a coordinated array of them — a Pulsar Timing Array
(PTA), of which NANOGrav is one — can be used as a Galaxy-scale gravitational-wave detector.
A long-wavelength gravitational wave passing through the Solar System and each pulsar's local
frame perturbs the light-travel time and imprints a correlated signature across every pulsar's
residuals, with an angular correlation pattern (the Hellings-Downs curve) that depends only on
the angle between pulsar pairs on the sky. Achieving that sensitivity depends on exactly the
ingredients this lab visualises separately: accurate timing-model subtraction, DM-variation
correction, and characterisation of intrinsic red and white timing noise, since all of these
must be modelled correctly before a shared gravitational-wave signal can be extracted from the
residuals of many pulsars.

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

## How It Works

The application is a static, zero-build page (`index.html`) with all numerical work isolated in
a Web Worker so the UI thread only ever handles input events and Canvas drawing:

1. **Load.** `assets/js/physicsWorker.js` reads the pre-built observation bundle
   (`data/observations/nanograv_11yr_residuals.json`), which was produced offline from the
   official NANOGrav `.tgz` archive by `tools/fetch_nanograv_observations.py`. Released
   residuals and DMX values are never regenerated or altered client-side.
2. **Select and play back.** Choosing a `PULSAR` swaps in that pulsar's released residual and
   DMX arrays. The `PLAYBACK` control steps a cursor through the released records at a
   configurable rate purely for visual pacing; it does not change the underlying values.
3. **Optional overlay.** If `SIMULATION OVERLAY` is enabled, the worker evaluates the
   rotational-phase ephemeris, the cold-plasma dispersion calculator, the Fourier red-noise
   generator, independent white noise, and (if `INJECT EVENT` is on) a sudden frequency-step
   glitch, all sampled at the same epochs as the displayed released residuals. These amber
   values are computed independently and drawn as a separate trace/template — they are never
   blended into or used to replace the cyan released data.
4. **Render.** The main thread (`assets/js/app.js`) draws the released residuals, released DMX
   series, and (if enabled) the overlay trace and simulated pulse template on
   device-pixel-ratio-aware `<canvas>` elements, and updates the telemetry readouts.
5. **Export.** `EXPORT DATA` asks the worker to assemble a CSV of the currently displayed
   released columns, with simulated-injection columns appended only when the overlay is active
   (see CSV Export below).

Offline, `tools/generate_synthetic_toas.py` and `tools/validate_model.py` provide an independent,
pure-Python reimplementation of the same rotational-phase, dispersion and noise equations used in
the worker, so the analytic model can be checked without a browser; `tools/validate_observations.py`
checks the integrity of the bundled release asset itself.

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
  data/
    synthetic_toas.csv             Reproducible offline reference TOA set
    validation_summary.csv         Output of the analytic validation checks
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

## Math Appendix

Symbols follow `docs/equations.md`; all times below are elapsed seconds `tau` from a reference
epoch unless stated otherwise.

**Rotational phase ephemeris** (quadratic spin-down, no proper acceleration term):

```text
N_model(tau) = N0 + nu * tau + 0.5 * nudot * tau^2
nu = 1 / (period_ms * 1e-3)                      [Hz]
nu_model(tau) = nu + nudot * tau                  [Hz]
```

**Instantaneous glitch injection** for glitch epoch `tau_g` and fractional step
`g = Delta nu / nu`:

```text
Delta nu = nu * g
Delta N(tau) = 0                                   for tau <  tau_g
Delta N(tau) = Delta nu * (tau - tau_g)             for tau >= tau_g
R_glitch(tau) = -Delta N(tau) / nu_model(tau)       [seconds]
```

The residual is negative after the glitch because the timing model under-predicts the true
rotation count once the star is spinning faster than the model assumes.

**Cold-plasma dispersion delay** between two receiver-band edges in MHz:

```text
Delta t = D * DM * (nu_low^-2 - nu_high^-2)         [seconds]
D = 4.148808e3                                      [s MHz^2 pc^-1 cm^3]
```

**Decimal-year to display-MJD conversion** used only for the residual plot axis:

```text
MJD_display = MJD(UTC year start) + fraction_of_calendar_year * days_in_year
```

**Red timing-noise synthesis**, a finite Fourier series with `k = 1 .. K` harmonics whose
coefficient variance falls off as a power law in harmonic number (spectral index `gamma`):

```text
r(i) = sum_k [ a_k * cos(2*pi*k*i / (n-1)) + b_k * sin(2*pi*k*i / (n-1)) ]
std(a_k), std(b_k)  proportional to  k^(-gamma / 2)
```

The finite-sample mean is removed and the series is linearly rescaled so its RMS equals the
requested value before independent zero-mean Gaussian white noise is added.

## References

Arzoumanian, Z. et al. (2018) 'The NANOGrav 11-year data set: High-precision timing of 45
millisecond pulsars', *The Astrophysical Journal Supplement Series*, 235(2), p. 37.
doi: [10.3847/1538-4365/aab5b0](https://doi.org/10.3847/1538-4365/aab5b0).

Lorimer, D.R. and Kramer, M. (2005) *Handbook of Pulsar Astronomy*. Cambridge:
Cambridge University Press.

Hobbs, G.B., Edwards, R.T. and Manchester, R.N. (2006) 'TEMPO2, a new pulsar-timing
package-I. An overview', *Monthly Notices of the Royal Astronomical Society*, 369(2),
pp. 655-672.

Hellings, R.W. and Downs, G.S. (1983) 'Upper limits on the isotropic gravitational radiation
background from pulsar timing analysis', *The Astrophysical Journal Letters*, 265, pp. L39-L42.

## Licence

Application source is released under the MIT Licence; see `LICENSE`. The NANOGrav data
product retains its source-release attribution and provenance.
