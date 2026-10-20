"""Reproducible diagnostics for *released* NANOGrav 11-year timing products.

No timing model is fitted or subtracted here. These descriptive diagnostics are
not a PTA gravitational-wave likelihood or a re-estimate of pulsar parameters.
Uses only the Python standard library.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timedelta, timezone
import math
from statistics import median
from typing import Mapping, Sequence


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    return math.fsum(x * w for x, w in zip(values, weights)) / math.fsum(weights)


def residual_noise_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, float]:
    """Uncertainty-weighted scatter after estimating ONE descriptive offset.

    Chi-square assumes independent, correctly calibrated Gaussian uncertainties;
    it is *not* a formal goodness-of-fit test for correlated timing residuals.
    """
    if len(rows) < 2:
        raise ValueError("At least two residuals required")
    y = [_finite(r["residualMicroseconds"], "residual") for r in rows]
    s = [_finite(r["uncertaintyMicroseconds"], "uncertainty") for r in rows]
    if any(v <= 0 for v in s):
        raise ValueError("Uncertainties must be positive")
    w = [1 / (v * v) for v in s]
    mean = _weighted_mean(y, w)
    chi2 = math.fsum(wi * (yi - mean) ** 2 for yi, wi in zip(y, w))
    wrms = math.sqrt(chi2 / math.fsum(w))
    med = median(y)
    mad = median([abs(v - med) for v in y])
    return {
        "count": len(y), "weighted_mean_us": mean, "weighted_rms_us": wrms,
        "reduced_chi2_descriptive": chi2 / (len(y) - 1),
        "effective_weighted_count": math.fsum(w) ** 2 / math.fsum(t * t for t in w),
        "median_us": med, "mad_us": mad,
    }


def lag_structure_function(
    rows: Sequence[Mapping[str, object]],
    lag_edges_days: Sequence[float],
) -> list[dict[str, float | int | None]]:
    """Irregular-cadence pair structure function, with measurement-noise subtraction.

    Uses the 365.25-day Julian-year approximation for lag differences in the
    supplied decimal-year coordinate. Correlated TOA errors are not modelled.
    Negative noise-subtracted values are retained, not silently clipped.
    """
    edges = [_finite(v, "lag edge") for v in lag_edges_days]
    if len(edges) < 2 or edges[0] < 0 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError("Lag edges must be nonnegative and strictly increasing")
    data = []
    for r in rows:
        epoch = _finite(r["decimalYear"], "epoch")
        val = _finite(r["residualMicroseconds"], "residual")
        err = _finite(r["uncertaintyMicroseconds"], "uncertainty")
        if err <= 0:
            raise ValueError("Uncertainty must be positive")
        data.append((epoch, val, err))
    data.sort()
    nbin = len(edges) - 1
    counts = [0] * nbin
    raw = [0.0] * nbin
    corrected = [0.0] * nbin
    for i, (ti, yi, si) in enumerate(data):
        for tj, yj, sj in data[i + 1:]:
            lag = (tj - ti) * 365.25
            if lag >= edges[-1]:
                break
            if lag < edges[0]:
                continue
            k = bisect_right(edges, lag) - 1
            delta2 = (yj - yi) ** 2
            counts[k] += 1
            raw[k] += delta2
            corrected[k] += delta2 - si * si - sj * sj
    return [
        {"lag_low_days": edges[i], "lag_high_days": edges[i + 1],
         "pairs": counts[i],
         "raw_sf_us2": raw[i] / counts[i] if counts[i] else None,
         "noise_subtracted_sf_us2": corrected[i] / counts[i] if counts[i] else None}
        for i in range(nbin)
    ]


def decimal_year_to_mjd(decimal_year: float) -> float:
    """Calendar-aware conversion of fractional calendar year to UTC-like MJD.

    No leap-second/barycentric conversion is attempted; suitable for bin
    association, not precision pulse timing.
    """
    val = _finite(decimal_year, "decimal year")
    year = math.floor(val)
    if year < 1859 or year > 9998:
        raise ValueError("Calendar year outside supported range")
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    instant = start + (end - start) * (val - year)
    return (instant - datetime(1858, 11, 17, tzinfo=timezone.utc)).total_seconds() / 86400


def dmx_residual_association(
    residual_rows: Sequence[Mapping[str, object]],
    dmx_rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Bin-associate residuals with released DMX windows and compute WLS slope.

    No extrapolation/interpolation outside DMX windows. An overlapping TOA is
    counted only once, and overlaps are reported. Regression is descriptive:
    released residuals already depend on the fitted DMX timing model.
    """
    windows = []
    for row in dmx_rows:
        start = _finite(row["mjdStart"], "DMX start")
        stop = _finite(row["mjdEnd"], "DMX end")
        dm = _finite(row["dmxPcCm3"], "DMX")
        if stop < start:
            raise ValueError("DMX end precedes start")
        windows.append((start, stop, dm))
    groups: list[list[tuple[float, float]]] = [[] for _ in windows]
    unassigned = overlaps = 0
    for row in residual_rows:
        t = decimal_year_to_mjd(float(row["decimalYear"]))
        y = _finite(row["residualMicroseconds"], "residual")
        sigma = _finite(row["uncertaintyMicroseconds"], "uncertainty")
        if sigma <= 0:
            raise ValueError("Uncertainty must be positive")
        matching = [i for i, (lo, hi, _) in enumerate(windows) if lo <= t <= hi]
        if not matching:
            unassigned += 1
            continue
        if len(matching) > 1:
            overlaps += 1
            continue  # ambiguous association, do not arbitrarily pick a window
        groups[matching[0]].append((y, 1 / sigma**2))
    matched = []
    for (_, _, dm), rows in zip(windows, groups):
        if rows:
            y = _weighted_mean([v for v, _ in rows], [w for _, w in rows])
            matched.append((dm, y, math.fsum(w for _, w in rows), len(rows)))
    output: dict[str, object] = {
        "matched_dmx_bins": len(matched),
        "matched_residuals": sum(v[3] for v in matched),
        "unassigned_residuals": unassigned,
        "ambiguous_residuals": overlaps,
        "slope_us_per_pc_cm3": None,
        "intercept_us": None,
    }
    if len(matched) < 3:
        return output
    x = [v[0] for v in matched]
    y = [v[1] for v in matched]
    w = [v[2] for v in matched]
    xbar = _weighted_mean(x, w)
    ybar = _weighted_mean(y, w)
    sxx = math.fsum(wi * (xi - xbar) ** 2 for xi, wi in zip(x, w))
    if sxx <= 0:
        return output
    slope = math.fsum(wi * (xi - xbar) * (yi - ybar) for xi, yi, wi in zip(x, y, w)) / sxx
    output["slope_us_per_pc_cm3"] = slope
    output["intercept_us"] = ybar - slope * xbar
    return output
