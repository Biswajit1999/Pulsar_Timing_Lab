"""Validate simplified pulsar timing relationships used by the browser lab."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from generate_synthetic_toas import generate_toas


def dispersion_delay_ms(dm: float, low_mhz: float, high_mhz: float) -> float:
    return 4.148808e3 * dm * (low_mhz**-2 - high_mhz**-2)


def main() -> None:
    zero_dm = dispersion_delay_ms(0.0, 1250.0, 1550.0)
    finite_dm = dispersion_delay_ms(56.0, 1250.0, 1550.0)
    finite_dm_double = dispersion_delay_ms(112.0, 1250.0, 1550.0)

    no_glitch = generate_toas(glitch_ppm=0.0)
    glitch = generate_toas(glitch_ppm=3.0, noise_ms=0.0)
    glitch_double = generate_toas(glitch_ppm=6.0, noise_ms=0.0)
    late_index = -1
    glitch_ratio = abs(glitch_double[late_index]["residual_ms"] / glitch[late_index]["residual_ms"])

    output = Path(__file__).resolve().parents[1] / "data" / "validation_summary.csv"
    rows = [
        {"check": "zero_dm_delay_ms", "value": zero_dm, "expected": 0.0, "passed": math.isclose(zero_dm, 0.0, abs_tol=1e-12)},
        {"check": "dm_linearity_ratio", "value": finite_dm_double / finite_dm, "expected": 2.0, "passed": math.isclose(finite_dm_double / finite_dm, 2.0, rel_tol=1e-12)},
        {"check": "zero_glitch_rows", "value": len(no_glitch), "expected": 31, "passed": len(no_glitch) == 31},
        {"check": "glitch_residual_scaling", "value": glitch_ratio, "expected": 2.0, "passed": math.isclose(glitch_ratio, 2.0, rel_tol=1e-9)},
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "value", "expected", "passed"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
