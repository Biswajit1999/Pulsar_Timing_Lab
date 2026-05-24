# Equations and Assumptions

## Rotational Phase

The simulator uses a truncated spin phase model:

```text
N(t) = N0 + nu (t - t0) + 0.5 nudot (t - t0)^2
```

where `nu` is the spin frequency and `nudot` is the frequency derivative. Higher-order spin terms are ignored in this first version.

## Pulse Profile

The folded pulse profile is represented using Gaussian components in rotational phase:

```text
I(phi) = A exp[-0.5 ((phi - phi0) / sigma)^2]
```

An interpulse component is added for visual structure. The plotted profile is synthetic.

## Dispersion Delay

Cold plasma dispersion is approximated as:

```text
Delta t_ms = 4.148808e3 DM (nu_low^-2 - nu_high^-2)
```

with `DM` in `pc cm^-3` and observing frequencies in `MHz`.

## Timing Residuals

Timing residuals are:

```text
R = TOA_observed - TOA_model
```

The lab combines simplified timing noise, spin-down curvature, and an unmodelled glitch term.

## Glitch Model

The glitch is represented as an instantaneous fractional frequency jump:

```text
Delta nu / nu = glitch_ppm * 1e-6
```

No exponential recovery term is included in version 1.

For an unmodelled instantaneous frequency jump, the leading residual after the glitch is:

```text
R_glitch ~= - (Delta nu / nu) (t - tg)
```

This sign convention follows the common residual definition `observed minus model`: pulses arriving early after an unmodelled spin-up produce negative residuals.
