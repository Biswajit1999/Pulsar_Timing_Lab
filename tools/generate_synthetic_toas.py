"""Generate synthetic pulsar time-of-arrival residuals for Pulsar Timing Lab."""

from __future__ import annotations

import csv
import math
from pathlib import Path


def deterministic_noise(index: int, seed: int = 11) -> float:
    x = math.sin(index * 127.1 + seed * 311.7) * 43758.5453
    return (x - math.floor(x)) * 2.0 - 1.0


def generate_toas(
    period_ms: float = 33.0,
    duration_h: float = 3.0,
    cadence_min: float = 6.0,
    noise_ms: float = 0.06,
    glitch_epoch_fraction: float = 0.55,
    glitch_ppm: float = 3.0,
) -> list[dict[str, float]]:
    period_s = period_ms / 1000.0
    nu = 1.0 / period_s
    pdot = 4.2e-13
    nudot = -pdot / period_s**2
    duration_s = duration_h * 3600.0
    glitch_time = duration_s * glitch_epoch_fraction
    count = int((duration_h * 60.0) / cadence_min) + 1
    rows: list[dict[str, float]] = []

    for index in range(count):
        time_s = index * cadence_min * 60.0
        post_glitch = max(0.0, time_s - glitch_time)
        residual_ms = -(glitch_ppm * 1e-6 * post_glitch) * 1000.0
        residual_ms += -0.5 * (nudot / nu) * time_s**2 * 1000.0
        residual_ms += noise_ms * math.sin(index * 0.55) + noise_ms * deterministic_noise(index)
        rows.append(
            {
                "time_hours": time_s / 3600.0,
                "toa_seconds": time_s + residual_ms / 1000.0,
                "residual_ms": residual_ms,
            }
        )

    return rows


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "data" / "synthetic_toas.csv"
    output.parent.mkdir(exist_ok=True)
    rows = generate_toas()
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_hours", "toa_seconds", "residual_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
