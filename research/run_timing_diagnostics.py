"""Run three diagnostics against the *existing* NANOGrav JSON; write separate outputs.

Usage: python tools_run.py [--input path] [--output directory]
"""
import argparse
import csv
import json
from pathlib import Path
from research.timing_diagnostics import residual_noise_summary, lag_structure_function, dmx_residual_association


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=Path("data/observations/nanograv_11yr_residuals.json"))
    parser.add_argument("--output",type=Path,default=Path("results/timing_diagnostics"))
    args=parser.parse_args()
    payload=json.loads(args.input.read_text(encoding="utf-8"))
    if "pulsars" not in payload or "sourceArchive" not in payload.get("provenance",{}):
        raise ValueError("Expected NANOGrav observational payload with provenance")
    args.output.mkdir(parents=True,exist_ok=True)
    summary={}
    for name,product in payload["pulsars"].items():
        rows=product["residuals"]
        noise=residual_noise_summary(rows)
        lags=lag_structure_function(rows,[0,1,7,30,90,180,365,730,1460,3650,6000])
        association=dmx_residual_association(rows,product["dmx"])
        summary[name]={"noise":noise,"dmx_association":association,"structure_function":lags}
        with (args.output/f"{name}_lag_structure.csv").open("w",newline="",encoding="utf-8") as h:
            writer=csv.DictWriter(h,fieldnames=list(lags[0]));writer.writeheader();writer.writerows(lags)
    (args.output/"summary.json").write_text(json.dumps({"source":payload["provenance"],"diagnostics":summary},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:{"n":v["noise"]["count"],"matched_dmx_bins":v["dmx_association"]["matched_dmx_bins"]} for k,v in summary.items()},indent=2))

if __name__=="__main__":main()
