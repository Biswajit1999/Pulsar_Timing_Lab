"""Generate a reproducible Pulsar Timing Lab reference TOA dataset."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

SECONDS_PER_DAY = 86400.0
DISPERSION_CONSTANT_SECONDS_MHZ2 = 4.148808e3


@dataclass(frozen=True)
class TimingModel:
    reference_mjd: float = 60400.0
    period_ms: float = 89.3
    nudot_hz_per_second: float = -15.6e-12
    span_days: float = 30.0
    cadence_hours: float = 12.0
    red_noise_rms_seconds: float = 240e-6
    red_spectral_index: float = 4.0
    white_noise_rms_seconds: float = 30e-6
    glitch_enabled: bool = True
    glitch_epoch_fraction: float = 0.58
    glitch_fractional_step: float = 0.025e-6

    @property
    def frequency_hz(self) -> float:
        return 1000.0 / self.period_ms

    @property
    def duration_seconds(self) -> float:
        return self.span_days * SECONDS_PER_DAY

    @property
    def glitch_seconds(self) -> float:
        return self.duration_seconds * self.glitch_epoch_fraction


def rotational_phase(time_seconds: float, model: TimingModel, include_glitch: bool) -> float:
    phase = (
        model.frequency_hz * time_seconds
        + 0.5 * model.nudot_hz_per_second * time_seconds**2
    )
    if include_glitch and model.glitch_enabled and time_seconds >= model.glitch_seconds:
        delta_frequency_hz = model.frequency_hz * model.glitch_fractional_step
        phase += delta_frequency_hz * (time_seconds - model.glitch_seconds)
    return phase


def instantaneous_model_frequency(time_seconds: float, model: TimingModel) -> float:
    return model.frequency_hz + model.nudot_hz_per_second * time_seconds


def dispersion_delay_seconds(dm: float, low_mhz: float, high_mhz: float) -> float:
    return DISPERSION_CONSTANT_SECONDS_MHZ2 * dm * (low_mhz**-2 - high_mhz**-2)


def red_noise_series(
    count: int,
    target_rms_seconds: float,
    spectral_index: float,
    generator: random.Random,
) -> list[float]:
    if target_rms_seconds == 0.0:
        return [0.0] * count
    harmonics = max(1, min(96, count // 2))
    cosine_weights: list[float] = []
    sine_weights: list[float] = []
    for harmonic in range(1, harmonics + 1):
        scale = harmonic ** (-spectral_index / 2.0)
        cosine_weights.append(generator.gauss(0.0, 1.0) * scale)
        sine_weights.append(generator.gauss(0.0, 1.0) * scale)

    values: list[float] = []
    for index in range(count):
        position = index / (count - 1)
        value = 0.0
        for harmonic in range(1, harmonics + 1):
            argument = 2.0 * math.pi * harmonic * position
            value += cosine_weights[harmonic - 1] * math.cos(argument)
            value += sine_weights[harmonic - 1] * math.sin(argument)
        values.append(value)

    mean = sum(values) / count
    centred = [value - mean for value in values]
    rms = math.sqrt(sum(value**2 for value in centred) / count)
    if rms == 0.0:
        return centred
    scale = target_rms_seconds / rms
    return [value * scale for value in centred]


def generate_toas(model: TimingModel = TimingModel(), seed: int = 48271) -> list[dict[str, float]]:
    generator = random.Random(seed)
    count = math.ceil(model.span_days * 24.0 / model.cadence_hours) + 1
    spacing_seconds = model.duration_seconds / (count - 1)
    red_noise = red_noise_series(
        count, model.red_noise_rms_seconds, model.red_spectral_index, generator
    )
    rows: list[dict[str, float]] = []

    for index in range(count):
        elapsed_seconds = index * spacing_seconds
        phase_model = rotational_phase(elapsed_seconds, model, include_glitch=False)
        phase_true = rotational_phase(elapsed_seconds, model, include_glitch=True)
        glitch_residual_seconds = -(
            phase_true - phase_model
        ) / instantaneous_model_frequency(elapsed_seconds, model)
        white_noise_seconds = generator.gauss(0.0, model.white_noise_rms_seconds)
        residual_seconds = (
            glitch_residual_seconds + red_noise[index] + white_noise_seconds
        )
        mjd_model = model.reference_mjd + elapsed_seconds / SECONDS_PER_DAY
        rows.append(
            {
                "mjd_model": mjd_model,
                "mjd_observed": mjd_model + residual_seconds / SECONDS_PER_DAY,
                "elapsed_seconds": elapsed_seconds,
                "residual_us": residual_seconds * 1e6,
                "glitch_residual_us": glitch_residual_seconds * 1e6,
                "red_noise_us": red_noise[index] * 1e6,
                "white_noise_us": white_noise_seconds * 1e6,
                "phase_model_cycles": phase_model,
                "phase_true_cycles": phase_true,
            }
        )
    return rows


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "data" / "synthetic_toas.csv"
    output.parent.mkdir(exist_ok=True)
    rows = generate_toas()
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    default_model = TimingModel()
    sweep_ms = dispersion_delay_seconds(67.9, 1200.0, 1600.0) * 1000.0
    print(
        f"Wrote {len(rows)} rows to {output}; default 1200-1600 MHz sweep "
        f"for DM=67.9 is {sweep_ms:.6f} ms"
    )


if __name__ == "__main__":
    main()
