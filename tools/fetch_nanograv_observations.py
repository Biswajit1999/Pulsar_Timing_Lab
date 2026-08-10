#!/usr/bin/env python3
"""Build compact browser assets from the official NANOGrav 11-year residual release."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS = ROOT / "data" / "observations"
ARCHIVE_URL = "https://data.nanograv.org/static/data/res_dmx_nanograv_11y.tgz"
PULSARS = ["J1713+0747", "J1909-3744", "B1937+21"]


def download() -> bytes:
    request = Request(ARCHIVE_URL, headers={"User-Agent": "Pulsar-Timing-Lab observational asset builder/1.0"})
    with urlopen(request, timeout=90) as response:
        return response.read()


def read_member(archive: tarfile.TarFile, name: str) -> str:
    member = archive.extractfile(name)
    if member is None:
        raise ValueError(f"NANOGrav archive member not found: {name}")
    return member.read().decode("ascii", errors="replace")


def parse_residuals(text: str) -> list[dict[str, object]]:
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        columns = line.split()
        if len(columns) < 6:
            continue
        rows.append({
            "telescope": columns[0],
            "backend": columns[1],
            "band": columns[2],
            "decimalYear": round(float(columns[3]), 7),
            "residualMicroseconds": round(float(columns[4]), 9),
            "uncertaintyMicroseconds": round(float(columns[5]), 9),
        })
    return rows


def parse_dmx(text: str) -> list[dict[str, object]]:
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        columns = line.split()
        if len(columns) < 8:
            continue
        rows.append({
            "mjd": round(float(columns[0]), 4),
            "dmxPcCm3": float(columns[1]),
            "uncertaintyPcCm3": float(columns[2]),
            "mjdStart": round(float(columns[3]), 4),
            "mjdEnd": round(float(columns[4]), 4),
            "frequencyLowMHz": round(float(columns[5]), 2),
            "frequencyHighMHz": round(float(columns[6]), 2),
            "bin": columns[7],
        })
    return rows


def main() -> None:
    OBSERVATIONS.mkdir(parents=True, exist_ok=True)
    payload = download()
    sources = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        release_readme = read_member(archive, "README")
        for pulsar in PULSARS:
            residuals = parse_residuals(read_member(archive, f"res_ave/{pulsar}.ares"))
            dmx = parse_dmx(read_member(archive, f"dmx_vals/{pulsar}.dmx"))
            if not residuals or not dmx:
                raise ValueError(f"Missing numeric NANOGrav observations for {pulsar}")
            sources[pulsar] = {"residuals": residuals, "dmx": dmx}
            print(f"Parsed {pulsar}: {len(residuals)} daily residuals, {len(dmx)} DMX bins")

    dataset = {
        "dataset": "NANOGrav 11-year data set residuals & DM variations",
        "version": "1.0, 2018-June-07",
        "product": "Daily-average timing residuals and dispersion measure variations",
        "pulsars": sources,
        "provenance": {
            "sourceArchive": ARCHIVE_URL,
            "archiveBytes": len(payload),
            "residualMemberPattern": "res_ave/<pulsar>.ares",
            "dmxMemberPattern": "dmx_vals/<pulsar>.dmx",
            "processing": "ASCII values preserved in JSON; no fitting or model subtraction performed by this builder.",
            "releaseWarning": (
                "NANOGrav cautions that timing residual values depend on the fitted timing model; "
                "new astrophysical studies should re-fit standard and additional parameters together."
            ),
            "citation": (
                "Arzoumanian, Z. et al., 2018. The NANOGrav 11-year Data Set: "
                "High-precision timing of 45 Millisecond Pulsars. "
                "The Astrophysical Journal Supplement Series, 235, 37."
            ),
        },
        "releaseReadmeExcerpt": "\n".join(release_readme.splitlines()[:28]),
    }
    output = OBSERVATIONS / "nanograv_11yr_residuals.json"
    output.write_text(json.dumps(dataset, separators=(",", ":")), encoding="utf-8")
    (OBSERVATIONS / "nanograv_11yr_source_metadata.json").write_text(
        json.dumps(dataset["provenance"], indent=2), encoding="utf-8"
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
