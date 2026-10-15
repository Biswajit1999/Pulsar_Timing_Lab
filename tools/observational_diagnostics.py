"""Descriptive diagnostics for the *released* NANOGrav 11-year products.

No timing-model refit, whitening, common-process inference or detection claim.
Pure standard-library implementation to match Pulsar Timing Lab's Python tools.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _validate(x, y, sigma, *, minimum=2):
    if len(x) != len(y) or len(y) != len(sigma) or len(y) < minimum:
        raise ValueError('incompatible series lengths')
    if not all(math.isfinite(v) for row in (x, y, sigma) for v in row):
        raise ValueError('non-finite data')
    if any(v <= 0 for v in sigma):
        raise ValueError('non-positive uncertainties')
    if any(x[i] > x[i + 1] for i in range(len(x) - 1)):
        raise ValueError('epochs must be ordered')


def weighted_residual_summary(epoch, residual_us, uncertainty_us):
    """Weighted scatter and chi-square about a fitted *constant*, not a timing fit.

    The formal chi-square reference assumes independent Gaussian errors; pulsar
    timing residuals can be correlated and inherit fitted timing parameters.
    """
    _validate(epoch, residual_us, uncertainty_us)
    w = [1 / s**2 for s in uncertainty_us]
    sw = sum(w)
    mean = sum(v * wi for v, wi in zip(residual_us, w)) / sw
    wrms = math.sqrt(sum(wi * (v - mean)**2 for v, wi in zip(residual_us, w)) / sw)
    chi2 = sum(((v - mean) / s)**2 for v, s in zip(residual_us, uncertainty_us))
    effective_n = sw**2 / sum(wi**2 for wi in w)
    return {'n': len(w), 'weighted_mean_us': mean, 'weighted_rms_us': wrms,
            'chi2_about_constant': chi2, 'reduced_chi2_independence_only': chi2 / (len(w)-1),
            'kish_effective_weight_count': effective_n}


def lag_structure_function(epoch, residual_us, uncertainty_us, lag_edges):
    """Unweighted pairwise D(tau) = mean[(r_j-r_i)^2], by epoch separation.

    The noise-subtracted column removes mean(sigma_i^2+sigma_j^2) only as a
    diagnostic. It may be negative and is not a PSD or gravitational-wave test.
    Pair estimates are correlated because observations recur across pairs.
    """
    _validate(epoch, residual_us, uncertainty_us)
    if len(lag_edges) < 2 or any(not math.isfinite(v) or v < 0 for v in lag_edges):
        raise ValueError('invalid lag edges')
    if any(a >= b for a, b in zip(lag_edges, lag_edges[1:])):
        raise ValueError('lag edges must be strictly increasing')
    sums = [0.0] * (len(lag_edges)-1)
    noises = sums.copy()
    counts = [0] * len(sums)
    for i in range(len(epoch)):
        for j in range(i+1, len(epoch)):
            lag = epoch[j] - epoch[i]
            for k in range(len(counts)):
                if lag_edges[k] <= lag < lag_edges[k+1]:
                    sums[k] += (residual_us[j]-residual_us[i])**2
                    noises[k] += uncertainty_us[i]**2 + uncertainty_us[j]**2
                    counts[k] += 1
                    break
    return [{'lag_start': lag_edges[k], 'lag_end': lag_edges[k+1],
             'pairs': counts[k],
             'mean_squared_difference_us2': sums[k]/counts[k] if counts[k] else None,
             'noise_subtracted_us2': (sums[k]-noises[k])/counts[k] if counts[k] else None}
            for k in range(len(counts))]


def weighted_dmx_trend(mjd, dmx, uncertainty):
    """Weighted straight-line descriptive DMX drift with formal 1-sigma error.

    DMX is a relative, fitted quantity; this is NOT an ISM trend detection.
    """
    _validate(mjd, dmx, uncertainty, minimum=3)
    weights = [1/s**2 for s in uncertainty]
    sw = sum(weights)
    t0 = sum(t*w for t, w in zip(mjd, weights))/sw
    mean = sum(y*w for y, w in zip(dmx, weights))/sw
    sxx = sum(w*(t-t0)**2 for t,w in zip(mjd,weights))
    if sxx <= 0:
        raise ValueError('no epoch leverage')
    slope = sum(w*(t-t0)*(y-mean) for t,y,w in zip(mjd,dmx,weights))/sxx
    chi2 = sum(((y-mean-slope*(t-t0))/s)**2 for t,y,s in zip(mjd,dmx,uncertainty))
    return {'reference_mjd': t0, 'dmx_at_reference_pc_cm3': mean,
            'slope_pc_cm3_per_day': slope, 'formal_slope_sigma_pc_cm3_per_day': math.sqrt(1/sxx),
            'reduced_chi2_independence_only': chi2/(len(mjd)-2), 'n': len(mjd)}


def analyze_product(payload):
    output = {}
    for name, obj in payload['pulsars'].items():
        r, d = obj['residuals'], obj['dmx']
        epoch = [float(x['decimalYear']) for x in r]
        y = [float(x['residualMicroseconds']) for x in r]
        s = [float(x['uncertaintyMicroseconds']) for x in r]
        t = [float(x['mjd']) for x in d]
        dm = [float(x['dmxPcCm3']) for x in d]
        se = [float(x['uncertaintyPcCm3']) for x in d]
        output[name] = {'weighted_residuals': weighted_residual_summary(epoch,y,s),
                        'structure_function_decimal_years': lag_structure_function(
                            epoch,y,s,[0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0, 20.0]),
                        'dmx_linear_diagnostic': weighted_dmx_trend(t,dm,se)}
    return {'source_provenance': payload.get('provenance',{}),
            'warning': 'Descriptive diagnostics only; no timing refit or gravitational-wave inference.',
            'pulsars': output}


def main():
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=root/'data/observations/nanograv_11yr_residuals.json')
    p.add_argument('--output', type=Path, default=root/'data/observations/nanograv_11yr_diagnostics.json')
    a = p.parse_args()
    report = analyze_product(json.loads(a.input.read_text(encoding='utf8')))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2)+'\n',encoding='utf8')
    print(f"Analysed {len(report['pulsars'])} released pulsar products -> {a.output}")


if __name__ == '__main__':
    main()
