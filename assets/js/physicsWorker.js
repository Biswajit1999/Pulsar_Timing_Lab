"use strict";

const OBSERVATION_URL = "../../data/observations/nanograv_11yr_residuals.json";
const DISPERSION_CONSTANT_SECONDS_MHZ2 = 4.148808e3;
const SECONDS_PER_DAY = 86400;
const PROFILE_BINS = 384;
const AVAILABLE_PULSARS = new Set(["J1713+0747", "J1909-3744", "B1937+21"]);

const runtime = {
  datasetPromise: null,
  product: null,
  playing: true,
  progress: 0,
  lastPlaybackTime: performance.now(),
  playbackTimer: null,
  latestRequestId: 0,
};

self.addEventListener("message", (event) => {
  const message = event.data;
  switch (message.type) {
    case "configure":
      runtime.latestRequestId = message.requestId;
      solveProducts(message);
      break;
    case "setPlayback":
      runtime.playing = Boolean(message.playing);
      runtime.lastPlaybackTime = performance.now();
      ensurePlaybackTimer();
      publishPlayback();
      break;
    case "exportCsv":
      exportCsv();
      break;
    default:
      self.postMessage({ type: "warning", message: `Unrecognised worker command: ${message.type}` });
  }
});

async function solveProducts(message) {
  const start = performance.now();
  try {
    const dataset = await loadDataset();
    if (message.requestId !== runtime.latestRequestId) {
      return;
    }
    const parameters = sanitiseParameters(message.parameters);
    const source = dataset.pulsars[parameters.pulsar];
    if (!source) {
      throw new Error(`Pulsar is absent from the local NANOGrav bundle: ${parameters.pulsar}`);
    }
    const observed = buildObservedResiduals(source.residuals);
    const dmx = buildDmxProduct(source.dmx);
    const random = createRandom(Number(message.seed) >>> 0);
    const model = parameters.modelOverlay ? buildInjectionModel(observed.mjd, parameters, random) : null;
    const profile = parameters.modelOverlay ? calculateProfile(parameters) : null;
    const telemetry = calculateTelemetry(parameters, observed, dmx, model, start);
    runtime.product = {
      dataset,
      parameters,
      source,
      observed,
      dmx,
      model,
      profile,
      telemetry,
    };
    runtime.progress = 0;
    runtime.lastPlaybackTime = performance.now();
    postProduct(message.requestId);
    ensurePlaybackTimer();
    publishPlayback();
  } catch (error) {
    self.postMessage({
      type: "dataError",
      requestId: message.requestId,
      message: error instanceof Error ? error.message : String(error),
    });
  }
}

function loadDataset() {
  if (!runtime.datasetPromise) {
    runtime.datasetPromise = fetch(OBSERVATION_URL)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`NANOGrav data request failed with HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((dataset) => {
        if (!dataset.pulsars || !dataset.provenance) {
          throw new Error("NANOGrav observational bundle is malformed");
        }
        return dataset;
      });
  }
  return runtime.datasetPromise;
}

function sanitiseParameters(input) {
  const periodMs = clamp(numberOr(input.periodMs, 4.57), 0.1, 10000);
  const centreFrequencyMHz = clamp(numberOr(input.centreFrequencyMHz, 1400), 30, 10000);
  const requestedBandwidthMHz = clamp(numberOr(input.bandwidthMHz, 800), 0.01, 10000);
  const frequencyLowMHz = Math.max(20, centreFrequencyMHz - requestedBandwidthMHz / 2);
  const frequencyHighMHz = Math.max(frequencyLowMHz + 0.01, centreFrequencyMHz + requestedBandwidthMHz / 2);
  const selectedPulsar = AVAILABLE_PULSARS.has(input.pulsar) ? input.pulsar : "J1713+0747";
  return {
    pulsar: selectedPulsar,
    modelOverlay: Boolean(input.modelOverlay),
    playbackRecordsPerSecond: clamp(numberOr(input.playbackRecordsPerSecond, 24), 1, 10000),
    periodMs,
    periodSeconds: periodMs / 1000,
    frequencyHz: 1000 / periodMs,
    nudotHzPerSecond: clamp(numberOr(input.nudotHzPerSecond, -0.4e-15), -1, 1),
    pulseWidthMs: clamp(numberOr(input.pulseWidthMs, 0.25), 0.001, periodMs * 2),
    dispersionMeasure: clamp(numberOr(input.dispersionMeasure, 15.99), 0, 100000),
    frequencyLowMHz,
    frequencyHighMHz,
    redNoiseRmsSeconds: clamp(numberOr(input.redNoiseRmsSeconds, 0.3e-6), 0, 10),
    redSpectralIndex: clamp(numberOr(input.redSpectralIndex, 4), 0, 12),
    whiteNoiseRmsSeconds: clamp(numberOr(input.whiteNoiseRmsSeconds, 0.05e-6), 0, 10),
    glitchEnabled: Boolean(input.glitchEnabled),
    glitchEpochFraction: clamp(numberOr(input.glitchEpochFraction, 0.58), 0, 1),
    glitchFractionalStep: clamp(numberOr(input.glitchFractionalStep, 0.001e-6), -0.1, 0.1),
  };
}

function buildObservedResiduals(rows) {
  const count = rows.length;
  const decimalYear = new Float64Array(count);
  const mjd = new Float64Array(count);
  const residualUs = new Float64Array(count);
  const uncertaintyUs = new Float64Array(count);
  for (let index = 0; index < count; index += 1) {
    decimalYear[index] = rows[index].decimalYear;
    mjd[index] = decimalYearToMjd(rows[index].decimalYear);
    residualUs[index] = rows[index].residualMicroseconds;
    uncertaintyUs[index] = rows[index].uncertaintyMicroseconds;
  }
  return { decimalYear, mjd, residualUs, uncertaintyUs };
}

function buildDmxProduct(rows) {
  const count = rows.length;
  const mjd = new Float64Array(count);
  const value = new Float64Array(count);
  const uncertainty = new Float64Array(count);
  const frequencyLowMHz = new Float64Array(count);
  const frequencyHighMHz = new Float64Array(count);
  for (let index = 0; index < count; index += 1) {
    mjd[index] = rows[index].mjd;
    value[index] = rows[index].dmxPcCm3;
    uncertainty[index] = rows[index].uncertaintyPcCm3;
    frequencyLowMHz[index] = rows[index].frequencyLowMHz;
    frequencyHighMHz[index] = rows[index].frequencyHighMHz;
  }
  return { mjd, value, uncertainty, frequencyLowMHz, frequencyHighMHz };
}

function decimalYearToMjd(decimalYear) {
  const year = Math.floor(decimalYear);
  const fraction = decimalYear - year;
  const yearStart = Date.UTC(year, 0, 1);
  const nextYear = Date.UTC(year + 1, 0, 1);
  return (yearStart + fraction * (nextYear - yearStart)) / 86400000 + 40587;
}

function buildInjectionModel(mjd, parameters, random) {
  const count = mjd.length;
  const startMjd = mjd[0];
  const durationSeconds = Math.max(1, (mjd[count - 1] - startMjd) * SECONDS_PER_DAY);
  const elapsedSeconds = new Float64Array(count);
  const injectionResidualUs = new Float64Array(count);
  const glitchResidualUs = new Float64Array(count);
  const redNoiseUs = new Float64Array(count);
  const whiteNoiseUs = new Float64Array(count);
  const redSeconds = synthesiseRedNoise(
    count,
    parameters.redNoiseRmsSeconds,
    parameters.redSpectralIndex,
    random
  );
  for (let index = 0; index < count; index += 1) {
    const elapsed = (mjd[index] - startMjd) * SECONDS_PER_DAY;
    const glitch = glitchResidualSeconds(elapsed, durationSeconds, parameters);
    const white = parameters.whiteNoiseRmsSeconds * gaussianRandom(random);
    elapsedSeconds[index] = elapsed;
    glitchResidualUs[index] = glitch * 1e6;
    redNoiseUs[index] = redSeconds[index] * 1e6;
    whiteNoiseUs[index] = white * 1e6;
    injectionResidualUs[index] = (glitch + redSeconds[index] + white) * 1e6;
  }
  return {
    elapsedSeconds,
    injectionResidualUs,
    glitchResidualUs,
    redNoiseUs,
    whiteNoiseUs,
    startMjd,
    durationSeconds,
    glitchMjd: startMjd + durationSeconds * parameters.glitchEpochFraction / SECONDS_PER_DAY,
  };
}

function glitchResidualSeconds(elapsedSeconds, durationSeconds, parameters) {
  if (!parameters.glitchEnabled) {
    return 0;
  }
  const eventSeconds = durationSeconds * parameters.glitchEpochFraction;
  const afterEvent = Math.max(0, elapsedSeconds - eventSeconds);
  const modelFrequency = Math.max(
    1e-12,
    parameters.frequencyHz + parameters.nudotHzPerSecond * elapsedSeconds
  );
  const deltaFrequency = parameters.frequencyHz * parameters.glitchFractionalStep;
  return -(deltaFrequency * afterEvent) / modelFrequency;
}

function synthesiseRedNoise(count, targetRmsSeconds, spectralIndex, random) {
  const series = new Float64Array(count);
  if (targetRmsSeconds === 0 || count < 2) {
    return series;
  }
  const harmonics = Math.max(1, Math.min(96, Math.floor(count / 2)));
  const cosineWeights = new Float64Array(harmonics);
  const sineWeights = new Float64Array(harmonics);
  for (let harmonic = 1; harmonic <= harmonics; harmonic += 1) {
    const amplitudeScale = harmonic ** (-spectralIndex / 2);
    cosineWeights[harmonic - 1] = gaussianRandom(random) * amplitudeScale;
    sineWeights[harmonic - 1] = gaussianRandom(random) * amplitudeScale;
  }
  let mean = 0;
  for (let index = 0; index < count; index += 1) {
    const position = index / Math.max(1, count - 1);
    let value = 0;
    for (let harmonic = 1; harmonic <= harmonics; harmonic += 1) {
      const argument = 2 * Math.PI * harmonic * position;
      value +=
        cosineWeights[harmonic - 1] * Math.cos(argument) +
        sineWeights[harmonic - 1] * Math.sin(argument);
    }
    series[index] = value;
    mean += value;
  }
  mean /= count;
  let variance = 0;
  for (let index = 0; index < count; index += 1) {
    series[index] -= mean;
    variance += series[index] * series[index];
  }
  const rms = Math.sqrt(variance / count);
  if (!rms) {
    return series;
  }
  const scale = targetRmsSeconds / rms;
  for (let index = 0; index < count; index += 1) {
    series[index] *= scale;
  }
  return series;
}

function calculateProfile(parameters) {
  const phase = new Float32Array(PROFILE_BINS + 1);
  const intensity = new Float32Array(PROFILE_BINS + 1);
  const fwhmPhase = Math.min(0.48, parameters.pulseWidthMs / parameters.periodMs);
  const sigma = Math.max(0.001, fwhmPhase / (2 * Math.sqrt(2 * Math.log(2))));
  let maximum = 0;
  for (let index = 0; index <= PROFILE_BINS; index += 1) {
    const valuePhase = index / PROFILE_BINS;
    const mainPulse = wrappedGaussian(valuePhase, 0.29, sigma);
    const interpulse = 0.19 * wrappedGaussian(valuePhase, 0.67, sigma * 1.55);
    const bridge = 0.025 * wrappedGaussian(valuePhase, 0.46, sigma * 3.4);
    const value = mainPulse + interpulse + bridge;
    phase[index] = valuePhase;
    intensity[index] = value;
    maximum = Math.max(maximum, value);
  }
  for (let index = 0; index < intensity.length; index += 1) {
    intensity[index] /= maximum || 1;
  }
  return { phase, intensity };
}

function wrappedGaussian(value, centre, sigma) {
  const separation = Math.abs(value - centre);
  const wrapped = Math.min(separation, 1 - separation);
  return Math.exp(-0.5 * (wrapped / sigma) ** 2);
}

function calculateTelemetry(parameters, observed, dmx, model, startTime) {
  let residualSumSquares = 0;
  let minimumResidualUs = Infinity;
  let maximumResidualUs = -Infinity;
  let dmxMinimum = Infinity;
  let dmxMaximum = -Infinity;
  for (let index = 0; index < observed.residualUs.length; index += 1) {
    const residual = observed.residualUs[index];
    residualSumSquares += residual * residual;
    minimumResidualUs = Math.min(minimumResidualUs, residual - observed.uncertaintyUs[index]);
    maximumResidualUs = Math.max(maximumResidualUs, residual + observed.uncertaintyUs[index]);
  }
  for (let index = 0; index < dmx.value.length; index += 1) {
    dmxMinimum = Math.min(dmxMinimum, dmx.value[index]);
    dmxMaximum = Math.max(dmxMaximum, dmx.value[index]);
  }
  if (model) {
    for (const value of model.injectionResidualUs) {
      minimumResidualUs = Math.min(minimumResidualUs, value);
      maximumResidualUs = Math.max(maximumResidualUs, value);
    }
  }
  const dispersionSweepMs = dispersionDelaySeconds(
    parameters.dispersionMeasure,
    parameters.frequencyLowMHz,
    parameters.frequencyHighMHz
  ) * 1000;
  return {
    pulsar: parameters.pulsar,
    residualCount: observed.residualUs.length,
    dmxCount: dmx.value.length,
    firstMjd: observed.mjd[0],
    lastMjd: observed.mjd[observed.mjd.length - 1],
    observedRmsUs: Math.sqrt(residualSumSquares / observed.residualUs.length),
    minimumResidualUs,
    maximumResidualUs,
    dmxMinimum,
    dmxMaximum,
    modelOverlay: Boolean(model),
    spinFrequencyHz: parameters.frequencyHz,
    nudotHzPerSecond: parameters.nudotHzPerSecond,
    dispersionSweepMs,
    frequencyLowMHz: parameters.frequencyLowMHz,
    frequencyHighMHz: parameters.frequencyHighMHz,
    glitchEnabled: Boolean(model && parameters.glitchEnabled),
    glitchMjd: model ? model.glitchMjd : null,
    deltaFrequencyHz: parameters.frequencyHz * parameters.glitchFractionalStep,
    computeMilliseconds: performance.now() - startTime,
  };
}

function dispersionDelaySeconds(dispersionMeasure, lowFrequencyMHz, highFrequencyMHz) {
  return DISPERSION_CONSTANT_SECONDS_MHZ2 *
    dispersionMeasure *
    (lowFrequencyMHz ** -2 - highFrequencyMHz ** -2);
}

function postProduct(requestId) {
  const product = runtime.product;
  const message = {
    type: "products",
    requestId,
    metadata: {
      dataset: product.dataset.dataset,
      version: product.dataset.version,
      pulsar: product.parameters.pulsar,
      sourceArchive: product.dataset.provenance.sourceArchive,
    },
    telemetry: product.telemetry,
    residuals: {
      decimalYear: product.observed.decimalYear.slice(),
      mjd: product.observed.mjd.slice(),
      residualUs: product.observed.residualUs.slice(),
      uncertaintyUs: product.observed.uncertaintyUs.slice(),
      modelResidualUs: product.model ? product.model.injectionResidualUs.slice() : null,
      glitchResidualUs: product.model ? product.model.glitchResidualUs.slice() : null,
    },
    dmx: {
      mjd: product.dmx.mjd.slice(),
      value: product.dmx.value.slice(),
      uncertainty: product.dmx.uncertainty.slice(),
    },
    profile: product.profile ? {
      phase: product.profile.phase.slice(),
      intensity: product.profile.intensity.slice(),
    } : null,
  };
  const transferable = [
    message.residuals.decimalYear.buffer,
    message.residuals.mjd.buffer,
    message.residuals.residualUs.buffer,
    message.residuals.uncertaintyUs.buffer,
    message.dmx.mjd.buffer,
    message.dmx.value.buffer,
    message.dmx.uncertainty.buffer,
  ];
  if (message.residuals.modelResidualUs) {
    transferable.push(message.residuals.modelResidualUs.buffer, message.residuals.glitchResidualUs.buffer);
  }
  if (message.profile) {
    transferable.push(message.profile.phase.buffer, message.profile.intensity.buffer);
  }
  self.postMessage(message, transferable);
}

function ensurePlaybackTimer() {
  if (runtime.playbackTimer === null) {
    runtime.playbackTimer = self.setInterval(publishPlayback, 40);
  }
}

function publishPlayback() {
  const product = runtime.product;
  if (!product) {
    return;
  }
  const now = performance.now();
  const elapsedSeconds = Math.max(0, (now - runtime.lastPlaybackTime) / 1000);
  runtime.lastPlaybackTime = now;
  const finalIndex = product.observed.mjd.length - 1;
  if (runtime.playing) {
    const advance = elapsedSeconds * product.parameters.playbackRecordsPerSecond / Math.max(1, finalIndex);
    runtime.progress = (runtime.progress + advance) % 1;
  }
  const position = runtime.progress * finalIndex;
  const lower = Math.floor(position);
  const upper = Math.min(finalIndex, lower + 1);
  const fraction = position - lower;
  self.postMessage({
    type: "playback",
    progress: runtime.progress,
    mjd: interpolate(product.observed.mjd[lower], product.observed.mjd[upper], fraction),
    residualUs: interpolate(product.observed.residualUs[lower], product.observed.residualUs[upper], fraction),
  });
}

function exportCsv() {
  const product = runtime.product;
  if (!product) {
    self.postMessage({ type: "warning", message: "No NANOGrav product is available for export" });
    return;
  }
  const modelEnabled = Boolean(product.model);
  const columns = [
    "pulsar",
    "decimal_year",
    "display_mjd",
    "telescope",
    "backend",
    "band",
    "released_residual_us",
    "released_uncertainty_us",
  ];
  if (modelEnabled) {
    columns.push("simulated_injection_us", "simulated_glitch_component_us");
  }
  const rows = [columns.join(",")];
  for (let index = 0; index < product.source.residuals.length; index += 1) {
    const source = product.source.residuals[index];
    const values = [
      csvText(product.parameters.pulsar),
      Number(source.decimalYear).toFixed(7),
      product.observed.mjd[index].toFixed(7),
      csvText(source.telescope),
      csvText(source.backend),
      csvText(source.band),
      Number(source.residualMicroseconds).toFixed(9),
      Number(source.uncertaintyMicroseconds).toFixed(9),
    ];
    if (modelEnabled) {
      values.push(
        product.model.injectionResidualUs[index].toFixed(9),
        product.model.glitchResidualUs[index].toFixed(9)
      );
    }
    rows.push(values.join(","));
  }
  self.postMessage({
    type: "csv",
    content: `${rows.join("\n")}\n`,
    filename: `nanograv_11yr_${product.parameters.pulsar.replace("+", "p")}_residuals.csv`,
    rowCount: product.source.residuals.length,
  });
}

function csvText(value) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function createRandom(seed) {
  let state = seed || 0x9e3779b9;
  const uniform = () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
  uniform.spareGaussian = null;
  return uniform;
}

function gaussianRandom(random) {
  if (random.spareGaussian !== null) {
    const spare = random.spareGaussian;
    random.spareGaussian = null;
    return spare;
  }
  let first = 0;
  let second = 0;
  while (first <= Number.EPSILON) {
    first = random();
    second = random();
  }
  const magnitude = Math.sqrt(-2 * Math.log(first));
  const angle = 2 * Math.PI * second;
  random.spareGaussian = magnitude * Math.sin(angle);
  return magnitude * Math.cos(angle);
}

function interpolate(start, end, fraction) {
  return start + (end - start) * fraction;
}

function numberOr(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}
