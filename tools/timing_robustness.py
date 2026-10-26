"""Independent, descriptive diagnostics for published pulsar residual/DMX series.

No timing-model parameters are re-fitted. Results must not be used as PTA
GW significance or as independent physical DM trends without a noise model.
"""
from __future__ import annotations

import numpy as np


def _series(t, y, sigma):
    t, y, sigma = (np.asarray(v, dtype=float) for v in (t, y, sigma))
    if any(v.ndim != 1 for v in (t, y, sigma)) or not (len(t) == len(y) == len(sigma)):
        raise ValueError("t, y, sigma must be equally sized 1-D arrays")
    if len(t) < 3 or not all(np.isfinite(v).all() for v in (t, y, sigma)) or np.any(sigma <= 0):
        raise ValueError("at least three finite measurements with positive uncertainties required")
    return t, y, sigma


def weighted_trend(t, y, sigma):
    """Diagonal-error weighted intercept/slope, with fixed-error covariance.

    Time and slope share the input time unit. The returned intercept is at
    the weighted mean epoch, reducing covariance and cancellation.
    """
    t, y, sigma = _series(t, y, sigma)
    w = (sigma / np.min(sigma)) ** -2
    epoch = np.sum(w * t) / np.sum(w)
    dt = t - epoch
    sxx = np.sum(w * dt * dt)
    if not np.isfinite(sxx) or sxx <= 1e-20 * np.sum(w):
        raise ValueError("epochs have insufficient leverage")
    intercept = np.sum(w * y) / np.sum(w)
    slope = np.sum(w * dt * (y - intercept)) / sxx
    residual = y - intercept - slope * dt
    chi2 = np.sum((residual / sigma) ** 2)
    cov = np.diag([1 / np.sum(1 / sigma**2), 1 / np.sum((dt / sigma)**2)])
    return {"epoch": float(epoch), "intercept": float(intercept), "slope": float(slope),
            "intercept_sigma": float(np.sqrt(cov[0, 0])), "slope_sigma": float(np.sqrt(cov[1, 1])),
            "chi2": float(chi2), "dof": len(t)-2, "reduced_chi2": float(chi2/(len(t)-2))}


def diagonal_excess_scatter(y, sigma, *, tol=1e-10):
    """Non-negative extra *independent* RMS solving chi2(jitter)=n-1.

    Returns zero if formal errors already produce reduced chi2 <= 1.
    This is a descriptive error-floor diagnostic, not a red-noise model.
    """
    _, y, sigma = _series(np.arange(len(y)), y, sigma)
    def evaluate(jitter):
        w = 1.0 / (sigma*sigma + jitter*jitter)
        mean = np.sum(w*y)/np.sum(w)
        return float(np.sum(w*(y-mean)**2)/(len(y)-1)), float(mean)
    initial, mean = evaluate(0.0)
    if initial <= 1:
        return {"extra_rms": 0.0, "mean": mean, "initial_reduced_chi2": initial, "final_reduced_chi2": initial}
    hi = max(float(np.std(y)), float(np.max(sigma)), 1e-12)
    while evaluate(hi)[0] > 1:
        hi *= 2
        if not np.isfinite(hi):
            raise ArithmeticError("unable to bracket extra scatter")
    lo = 0.0
    for _ in range(100):
        mid = (lo + hi)/2
        if evaluate(mid)[0] > 1:
            lo = mid
        else:
            hi = mid
        if hi-lo <= tol*max(1.0, hi):
            break
    final, mean = evaluate(hi)
    return {"extra_rms": float(hi), "mean": mean,
            "initial_reduced_chi2": initial, "final_reduced_chi2": final}


def pair_structure_function(t, y, sigma, lag_edges, *, max_pairs=2_000_000):
    """Noise-subtracted pairwise squared differences in time-lag bins.

    Pairs use i<j; subtraction of sigma_i²+sigma_j² assumes independent
    quoted errors. Negative values are retained (never clipped to zero).
    """
    t, y, sigma = _series(t, y, sigma)
    edges = np.asarray(lag_edges, dtype=float)
    if edges.ndim != 1 or len(edges) < 2 or not np.all(np.isfinite(edges)) or edges[0] < 0 or np.any(np.diff(edges) <= 0):
        raise ValueError("lag edges must be increasing, finite and non-negative")
    if len(t)*(len(t)-1)//2 > max_pairs:
        raise ValueError("too many pairs; increase max_pairs explicitly")
    ii, jj = np.triu_indices(len(t), 1)
    lag = np.abs(t[jj]-t[ii])
    signal = (y[jj]-y[ii])**2 - sigma[ii]**2 - sigma[jj]**2
    which = np.searchsorted(edges, lag, side="right")-1
    which[lag == edges[-1]] = len(edges)-2
    return [{"lag_min": float(edges[k]), "lag_max": float(edges[k+1]),
             "pairs": int(np.sum(which == k)),
             "noise_subtracted_mean_square": (float(np.mean(signal[which == k])) if np.any(which == k) else None)}
            for k in range(len(edges)-1)]
