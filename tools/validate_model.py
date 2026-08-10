"""Validate the analytic invariants of the Pulsar Timing Lab numerical kernel."""

from __future__ import annotations

import csv
import math
from dataclasses import replace
from pathlib import Path

from generate_synthetic_toas import (
    DISPERSION_CONSTANT_SECONDS_MHZ2,
    TimingModel,
    dispersion_delay_seconds,
    generate_toas,
    rotational_phase,
)


def result(name: str, value: float, expected: float, passed: bool) -> dict[str, object]:
    return {"check": name, "value": value, "expected": expected, "passed": passed}


def main() -> None:
    model = TimingModel()
    evaluation_time = 12345.0
    phase_expected = (
        model.frequency_hz * evaluation_time
        + 0.5 * model.nudot_hz_per_second * evaluation_time**2
    )
    phase_value = rotational_phase(evaluation_time, model, include_glitch=False)

    zero_dm_seconds = dispersion_delay_seconds(0.0, 1200.0, 1600.0)
    finite_dm_seconds = dispersion_delay_seconds(67.9, 1200.0, 1600.0)
    doubled_dm_seconds = dispersion_delay_seconds(135.8, 1200.0, 1600.0)
    independently_derived_seconds = (
        DISPERSION_CONSTANT_SECONDS_MHZ2
        * 67.9
        * (1200.0**-2 - 1600.0**-2)
    )

    quiet_model = replace(
        model,
        glitch_enabled=False,
        red_noise_rms_seconds=0.0,
        white_noise_rms_seconds=0.0,
    )
    quiet_rows = generate_toas(quiet_model)
    maximum_quiet_residual = max(abs(row["residual_us"]) for row in quiet_rows)

    glitch_model = replace(
        model,
        red_noise_rms_seconds=0.0,
        white_noise_rms_seconds=0.0,
        glitch_fractional_step=0.025e-6,
    )
    double_glitch_model = replace(glitch_model, glitch_fractional_step=0.050e-6)
    glitch_last = generate_toas(glitch_model)[-1]["glitch_residual_us"]
    double_glitch_last = generate_toas(double_glitch_model)[-1]["glitch_residual_us"]
    glitch_ratio = double_glitch_last / glitch_last

    rows = [
        result(
            "quadratic_phase_cycles",
            phase_value,
            phase_expected,
            math.isclose(phase_value, phase_expected, rel_tol=0.0, abs_tol=1e-12),
        ),
        result(
            "zero_dm_delay_seconds",
            zero_dm_seconds,
            0.0,
            math.isclose(zero_dm_seconds, 0.0, rel_tol=0.0, abs_tol=1e-15),
        ),
        result(
            "dispersion_seconds_unit_convention",
            finite_dm_seconds,
            independently_derived_seconds,
            math.isclose(finite_dm_seconds, independently_derived_seconds, rel_tol=1e-15),
        ),
        result(
            "dm_linearity_ratio",
            doubled_dm_seconds / finite_dm_seconds,
            2.0,
            math.isclose(doubled_dm_seconds / finite_dm_seconds, 2.0, rel_tol=1e-14),
        ),
        result(
            "millisecond_display_conversion",
            finite_dm_seconds * 1000.0,
            independently_derived_seconds * 1000.0,
            math.isclose(
                finite_dm_seconds * 1000.0,
                independently_derived_seconds * 1000.0,
                rel_tol=1e-15,
            ),
        ),
        result(
            "quiet_model_zero_residual_us",
            maximum_quiet_residual,
            0.0,
            math.isclose(maximum_quiet_residual, 0.0, rel_tol=0.0, abs_tol=1e-12),
        ),
        result(
            "glitch_residual_step_scaling",
            glitch_ratio,
            2.0,
            math.isclose(glitch_ratio, 2.0, rel_tol=1e-12),
        ),
    ]

    output = Path(__file__).resolve().parents[1] / "data" / "validation_summary.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "value", "expected", "passed"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row["check"] for row in rows if not row["passed"]]
    if failed:
        raise SystemExit(f"Validation failed: {', '.join(str(name) for name in failed)}")
    print(f"Validated {len(rows)} invariants; wrote {output}")


if __name__ == "__main__":
    main()
