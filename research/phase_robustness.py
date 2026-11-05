"""Independent synthetic pulsar timing sensitivity checks (no observational fit)."""
import numpy as np

def weighted_phase_fit(t, residual, sigma, period):
    """Fit offset, linear drift and sinusoid at a fixed trial period by WLS."""
    t, residual, sigma = map(lambda a: np.asarray(a, dtype=float), (t, residual, sigma))
    if t.ndim != 1 or residual.shape != t.shape or sigma.shape != t.shape or len(t) < 5:
        raise ValueError('matching one-dimensional arrays with at least five samples required')
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(residual)) and np.all(np.isfinite(sigma)) and np.all(sigma > 0) and period > 0):
        raise ValueError('invalid inputs')
    x = (t - np.mean(t)) / np.ptp(t) if np.ptp(t) > 0 else np.zeros_like(t)
    phase = 2 * np.pi * (t - t[0]) / period
    design = np.column_stack((np.ones(len(t)), x, np.sin(phase), np.cos(phase)))
    whitened = design / sigma[:, None]
    if np.linalg.matrix_rank(whitened) != 4:
        raise ValueError('rank-deficient sampling')
    coeff = np.linalg.lstsq(whitened, residual / sigma, rcond=None)[0]
    covariance = np.linalg.inv(whitened.T @ whitened)
    chi2 = np.sum(((residual - design @ coeff) / sigma) ** 2)
    return coeff, covariance, chi2

def chromatic_delay(dm, frequency_mhz, reference_mhz=np.inf):
    """Cold-plasma differential delay in seconds; DM in pc cm^-3, MHz frequencies."""
    f = np.asarray(frequency_mhz, dtype=float)
    if np.any(f <= 0) or np.any(~np.isfinite(f)) or reference_mhz <= 0:
        raise ValueError('frequencies must be positive')
    return 4.148808e3 * dm * (f**-2 - reference_mhz**-2)
