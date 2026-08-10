#!/usr/bin/env python3
"""Validate the bundled NANOGrav residual and DMX observational product."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "observations" / "nanograv_11yr_residuals.json"
EXPECTED_COUNTS = {
    "J1713+0747": (789, 209),
    "J1909-3744": (451, 166),
    "B1937+21": (460, 165),
}
SOURCE_URL = "https://data.nanograv.org/static/data/res_dmx_nanograv_11y.tgz"


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def validate_ordered(rows: list[dict[str, object]], key: str, name: str) -> None:
    epochs = [float(row[key]) for row in rows]
    if epochs != sorted(epochs):
        raise ValueError(f"{name}: epochs are not ordered")


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    if payload.get("provenance", {}).get("sourceArchive") != SOURCE_URL:
        raise ValueError("NANOGrav official source archive provenance is missing")
    report = []
    for pulsar, (residual_count, dmx_count) in EXPECTED_COUNTS.items():
        product = payload.get("pulsars", {}).get(pulsar)
        if not product:
            raise ValueError(f"Missing configured pulsar: {pulsar}")
        residuals = product.get("residuals", [])
        dmx = product.get("dmx", [])
        if len(residuals) != residual_count or len(dmx) != dmx_count:
            raise ValueError(f"{pulsar}: unexpected row counts")
        validate_ordered(residuals, "decimalYear", pulsar)
        validate_ordered(dmx, "mjd", pulsar)
        for row in residuals:
            if not finite(row.get("residualMicroseconds")) or not finite(row.get("uncertaintyMicroseconds")):
                raise ValueError(f"{pulsar}: invalid residual row")
            if float(row["uncertaintyMicroseconds"]) <= 0:
                raise ValueError(f"{pulsar}: non-positive residual uncertainty")
        for row in dmx:
            if not finite(row.get("dmxPcCm3")) or not finite(row.get("uncertaintyPcCm3")):
                raise ValueError(f"{pulsar}: invalid DMX row")
            if float(row["uncertaintyPcCm3"]) <= 0:
                raise ValueError(f"{pulsar}: non-positive DMX uncertainty")
        report.append(f"{pulsar}={len(residuals)} residuals/{len(dmx)} DMX bins")
    print("Validated NANOGrav observational bundle: " + "; ".join(report))


if __name__ == "__main__":
    main()
