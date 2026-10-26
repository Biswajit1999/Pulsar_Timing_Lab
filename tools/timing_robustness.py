"""Correlated-noise and chromatic sensitivity diagnostics for NANOGrav DMX bins.

These are conditional sensitivity experiments on published timing-model-dependent
products, not independent timing solutions or physical DM detections.
"""
from __future__ import annotations

import numpy as np

DISPERSION_CONSTANT_S_MHZ2 = 4.148808e3


def _series(t, y, sigma):
    t, y, sigma = (np.asarray(v, dtype=float) for v in (t, y, sigma))
    if any(v.ndim != 1 for v in (t, y, sigma)) or not (len(t) == len(y) == len(sigma)):
        raise ValueError("t, y, sigma must be equally sized 1-D arrays")
    if len(t) < 3 or not all(np.isfinite(v).all() for v in (t, y, sigma)) or np.any(sigma <= 0):
        raise ValueError("at least three finite observations with positive errors required")
    return t, y, sigma


def gls_trend(t, y, sigma, *, correlated_rms=0.0, correlation_timescale=1.0):
    """GLS line fit with C_ij=sigma_i² delta_ij+a² exp(-|ti-tj|/tau).

    Amplitude a and timescale tau are declared sensitivity assumptions, not
    fitted noise parameters. Times and tau must use the same unit.
    """
    t, y, sigma = _series(t, y, sigma)
    if not np.isfinite(correlated_rms) or correlated_rms < 0 or not np.isfinite(correlation_timescale) or correlation_timescale <= 0:
        raise ValueError("invalid correlated-noise hyperparameters")
    epoch = float(np.mean(t))
    x = np.column_stack((np.ones(len(t)), t - epoch))
    covariance = np.diag(sigma**2)
    if correlated_rms > 0:
        covariance += correlated_rms**2 * np.exp(-np.abs(t[:, None]-t[None, :])/correlation_timescale)
    chol = np.linalg.cholesky(covariance)
    whitened_x = np.linalg.solve(chol, x)
    whitened_y = np.linalg.solve(chol, y)
    fisher = whitened_x.T @ whitened_x
    cov_beta = np.linalg.inv(fisher)
    beta = cov_beta @ (whitened_x.T @ whitened_y)
    chi2 = float(np.sum((whitened_y-whitened_x @ beta)**2))
    return {"epoch": epoch, "intercept": float(beta[0]), "slope": float(beta[1]),
            "slope_sigma_conditional": float(np.sqrt(cov_beta[1, 1])),
            "intercept_sigma_conditional": float(np.sqrt(cov_beta[0, 0])),
            "chi2": chi2, "dof": len(t)-2, "reduced_chi2": chi2/(len(t)-2),
            "assumed_correlated_rms": float(correlated_rms),
            "assumed_timescale": float(correlation_timescale)}


def leave_block_out_trends(t, y, sigma, *, block_width=1.0, correlated_rms=0.0, correlation_timescale=1.0):
    """Re-fit GLS after excluding each nonempty time block in turn.

    This is a deletion-sensitivity envelope, not a bootstrap confidence band.
    """
    t, y, sigma = _series(t, y, sigma)
    if not np.isfinite(block_width) or block_width <= 0:
        raise ValueError("block_width must be positive")
    blocks = np.floor((t-np.min(t))/block_width).astype(int)
    unique = np.unique(blocks)
    if len(unique) < 2:
        raise ValueError("at least two time blocks required")
    full = gls_trend(t, y, sigma, correlated_rms=correlated_rms, correlation_timescale=correlation_timescale)
    results = []
    for block in unique:
        keep = blocks != block
        if np.sum(keep) < 3 or np.ptp(t[keep]) < 1e-10:
            continue
        fit = gls_trend(t[keep], y[keep], sigma[keep], correlated_rms=correlated_rms,
                        correlation_timescale=correlation_timescale)
        results.append({"block_index": int(block), "removed": int(np.sum(~keep)), "slope": fit["slope"]})
    if not results:
        raise ValueError("no estimable leave-block-out fit")
    slopes = [v["slope"] for v in results]
    return {"full_slope": full["slope"], "block_width": float(block_width),
            "min_deleted_slope": float(min(slopes)), "max_deleted_slope": float(max(slopes)),
            "max_abs_slope_change": float(max(abs(s-full["slope"]) for s in slopes)),
            "deleted_blocks": results}


def dmx_band_delay(dmx_pc_cm3, dmx_sigma_pc_cm3, frequency_low_mhz, frequency_high_mhz):
    """Signed DMX delay and conditional 1-sigma across a receiver band (seconds)."""
    vals = (dmx_pc_cm3, dmx_sigma_pc_cm3, frequency_low_mhz, frequency_high_mhz)
    if not all(np.isfinite(v) for v in vals) or dmx_sigma_pc_cm3 < 0 or not (0 < frequency_low_mhz < frequency_high_mhz):
        raise ValueError("invalid DMX, uncertainty or band limits")
    factor = DISPERSION_CONSTANT_S_MHZ2 * (frequency_low_mhz**-2-frequency_high_mhz**-2)
    return {"delay_seconds": float(factor*dmx_pc_cm3),
            "sigma_seconds": float(factor*dmx_sigma_pc_cm3),
            "band_low_mhz": float(frequency_low_mhz), "band_high_mhz": float(frequency_high_mhz)}
