"""Independent diagnostics for released pulsar timing residuals (not TOA refitting)."""
from __future__ import annotations
import math


def weighted_mean(residual_us, sigma_us):
    """Diagonal-error weighted mean, formal standard error and chi-square."""
    if len(residual_us) != len(sigma_us) or not residual_us:
        raise ValueError('Nonempty, equal-length arrays required')
    if any(not math.isfinite(x) for x in residual_us) or any(not math.isfinite(s) or s <= 0 for s in sigma_us):
        raise ValueError('Finite residuals and positive finite errors required')
    w = [1 / s**2 for s in sigma_us]
    total = math.fsum(w)
    mean = math.fsum(x * wi for x, wi in zip(residual_us, w)) / total
    return {'mean_us': mean, 'formal_se_us': math.sqrt(1 / total),
            'chi2': math.fsum(wi * (x - mean)**2 for x, wi in zip(residual_us, w)),
            'dof': len(w) - 1}


def dmx_delay_us(dmx_pc_cm3, sigma_dm, frequency_mhz, reference_mhz=math.inf):
    """Cold-plasma differential delay, with DM-only propagated uncertainty.

    K = 4.148808e3 MHz^2 pc^-1 cm^3 s. Reference infinity is allowed.
    """
    if not all(math.isfinite(v) for v in (dmx_pc_cm3, sigma_dm, frequency_mhz)) or sigma_dm < 0 or frequency_mhz <= 0:
        raise ValueError('Invalid DM, uncertainty or observing frequency')
    if reference_mhz != math.inf and (not math.isfinite(reference_mhz) or reference_mhz <= 0):
        raise ValueError('Invalid reference frequency')
    coefficient = 4.148808e9 * (1 / frequency_mhz**2 - (0 if math.isinf(reference_mhz) else 1 / reference_mhz**2))
    return coefficient * dmx_pc_cm3, abs(coefficient) * sigma_dm


def load_release_diagnostics(path):
    """Read unchanged NANOGrav bundle; descriptive statistics only."""
    import json
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    if 'nanograv' not in data.get('provenance', {}).get('sourceArchive', '').lower():
        raise ValueError('Unexpected release provenance')
    result = {}
    for name, series in data['pulsars'].items():
        rows = series['residuals']
        result[name] = weighted_mean([r['residualMicroseconds'] for r in rows],
                                     [r['uncertaintyMicroseconds'] for r in rows])
        result[name]['n_residuals'] = len(rows)
        result[name]['n_dmx'] = len(series['dmx'])
    return result
