"""Run conditional covariance, deletion and dispersion checks on retained DMX."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from timing_robustness import gls_trend, leave_block_out_trends, dmx_band_delay


def analyse(payload):
    report={"source":payload["provenance"]["sourceArchive"],
            "warning":"Timing-model-dependent DMX; correlated-noise amplitude and timescale are hypothetical sensitivity settings.",
            "pulsars":{}}
    for name,product in payload["pulsars"].items():
        rows=product["dmx"]
        t=np.array([x["mjd"] for x in rows],float)/365.25
        y=np.array([x["dmxPcCm3"] for x in rows],float)
        sigma=np.array([x["uncertaintyPcCm3"] for x in rows],float)
        assumed_rms=float(np.median(sigma))
        delays=[dmx_band_delay(x["dmxPcCm3"],x["uncertaintyPcCm3"],
                               x["frequencyLowMHz"],x["frequencyHighMHz"]) for x in rows]
        report["pulsars"][name]={"dmx_count":len(rows),
            "independent_error_trend_per_year":gls_trend(t,y,sigma),
            "assumed_exponential_covariance_trend_per_year":gls_trend(t,y,sigma,correlated_rms=assumed_rms,correlation_timescale=.5),
            "leave_one_year_block_out":leave_block_out_trends(t,y,sigma,block_width=1.,correlated_rms=assumed_rms,correlation_timescale=.5),
            "receiver_band_delay_median_abs_microseconds":float(np.median([abs(x["delay_seconds"])*1e6 for x in delays])),
            "receiver_band_sigma_median_microseconds":float(np.median([x["sigma_seconds"]*1e6 for x in delays]))}
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,default=Path(__file__).resolve().parents[1]/"data/observations/nanograv_11yr_residuals.json")
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=json.dumps(analyse(json.loads(a.data.read_text(encoding="utf-8"))),indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(result+"\n",encoding="utf-8")
    else: print(result)


if __name__=="__main__": main()
