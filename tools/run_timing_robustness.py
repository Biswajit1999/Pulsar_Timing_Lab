"""Run descriptive diagnostics on the retained NANOGrav 11-year JSON asset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from timing_robustness import weighted_trend, diagonal_excess_scatter, pair_structure_function


def analyse(payload):
    report = {"source": payload["provenance"]["sourceArchive"], "note": "Released timing-model-dependent residuals; descriptive diagonal-error diagnostics only.", "pulsars": {}}
    for name, product in payload["pulsars"].items():
        r, d = product["residuals"], product["dmx"]
        if len(r) < 3 or len(d) < 3:
            continue
        residual = [x["residualMicroseconds"] for x in r]
        uncertainty = [x["uncertaintyMicroseconds"] for x in r]
        times = [x["decimalYear"] for x in r]
        dm = [x["dmxPcCm3"] for x in d]
        dmerr = [x["uncertaintyPcCm3"] for x in d]
        dm_year = [2000+(x["mjd"]-51544.5)/365.25 for x in d]  # approximate MJD-to-years for slopes only
        report["pulsars"][name] = {
            "residual_count": len(r), "dmx_count": len(d),
            "dmx_trend_per_approx_year": weighted_trend(dm_year, dm, dmerr),
            "residual_extra_white_rms_us": diagonal_excess_scatter(residual, uncertainty),
            "residual_structure_us2": pair_structure_function(times, residual, uncertainty, [0, .01, .1, .5, 1., 3., 10.]),
        }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1]/"data/observations/nanograv_11yr_residuals.json")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = analyse(json.loads(args.data.read_text(encoding="utf-8")))
    result = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result+"\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__": main()
