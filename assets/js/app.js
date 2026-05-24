const controls = {
  period: document.querySelector("#period"),
  width: document.querySelector("#width"),
  spindown: document.querySelector("#spindown"),
  duration: document.querySelector("#duration"),
  cadence: document.querySelector("#cadence"),
  noise: document.querySelector("#noise"),
  dm: document.querySelector("#dm"),
  freq: document.querySelector("#freq"),
  bandwidth: document.querySelector("#bandwidth"),
  glitchEpoch: document.querySelector("#glitchEpoch"),
  glitchSize: document.querySelector("#glitchSize"),
};

const outputs = {
  period: document.querySelector("#period-value"),
  width: document.querySelector("#width-value"),
  spindown: document.querySelector("#spindown-value"),
  duration: document.querySelector("#duration-value"),
  cadence: document.querySelector("#cadence-value"),
  noise: document.querySelector("#noise-value"),
  dm: document.querySelector("#dm-value"),
  freq: document.querySelector("#freq-value"),
  bandwidth: document.querySelector("#bandwidth-value"),
  glitchEpoch: document.querySelector("#glitch-epoch-value"),
  glitchSize: document.querySelector("#glitch-size-value"),
  summaryPeriod: document.querySelector("#summary-period"),
  summaryDm: document.querySelector("#summary-dm"),
  summaryRms: document.querySelector("#summary-rms"),
  summaryGlitch: document.querySelector("#summary-glitch"),
};

const canvases = {
  profile: document.querySelector("#profile-canvas"),
  residual: document.querySelector("#residual-canvas"),
  waterfall: document.querySelector("#waterfall-canvas"),
};

let latestToas = [];

function value(id) {
  return Number(controls[id].value);
}

function seededNoise(index, seed = 7) {
  const x = Math.sin(index * 127.1 + seed * 311.7) * 43758.5453;
  return (x - Math.floor(x)) * 2 - 1;
}

function gaussian(x, mu, sigma) {
  const dx = Math.min(Math.abs(x - mu), 1 - Math.abs(x - mu));
  return Math.exp(-0.5 * (dx / sigma) ** 2);
}

function resizeCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(320, canvas.clientWidth);
  const height = Math.max(240, Math.round(width * Number(canvas.height) / Number(canvas.width)));
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width, height };
}

function drawFrame(ctx, width, height, titleX = "x", titleY = "y") {
  const pad = { left: 54, right: 18, top: 22, bottom: 42 };
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#11141b";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(255,255,255,0.09)";
  ctx.lineWidth = 1;

  for (let i = 0; i <= 5; i += 1) {
    const y = pad.top + (height - pad.top - pad.bottom) * i / 5;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
  }

  ctx.fillStyle = "#aab4c3";
  ctx.font = "12px system-ui";
  ctx.fillText(titleY, 12, pad.top + 6);
  ctx.fillText(titleX, width - 78, height - 12);
  return pad;
}

function plotLine(canvas, points, options) {
  const { ctx, width, height } = resizeCanvas(canvas);
  const pad = drawFrame(ctx, width, height, options.xLabel, options.yLabel);
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const xMin = options.xMin ?? Math.min(...xs);
  const xMax = options.xMax ?? Math.max(...xs);
  const yMin = options.yMin ?? Math.min(...ys);
  const yMax = options.yMax ?? Math.max(...ys);
  const spanY = yMax - yMin || 1;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const px = (x) => pad.left + ((x - xMin) / (xMax - xMin || 1)) * plotW;
  const py = (y) => pad.top + (1 - (y - yMin) / spanY) * plotH;

  if (options.thresholds) {
    for (const threshold of options.thresholds) {
      const y = py(threshold.value);
      ctx.strokeStyle = threshold.color;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(width - pad.right, y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  ctx.strokeStyle = options.color || "#5bd8ff";
  ctx.lineWidth = 2.3;
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(px(point.x), py(point.y));
    else ctx.lineTo(px(point.x), py(point.y));
  });
  ctx.stroke();

  if (options.scatter) {
    ctx.fillStyle = options.dotColor || "#f4b247";
    points.forEach((point) => {
      ctx.beginPath();
      ctx.arc(px(point.x), py(point.y), 3, 0, Math.PI * 2);
      ctx.fill();
    });
  }
}

function drawWaterfall(model) {
  const { ctx, width, height } = resizeCanvas(canvases.waterfall);
  const pad = drawFrame(ctx, width, height, "time delay (ms)", "radio frequency");
  const rows = 44;
  const cols = 170;
  const fLow = model.freq - model.bandwidth / 2;
  const fHigh = model.freq + model.bandwidth / 2;
  const fRef = fHigh;
  const delaySpan = Math.max(3, dispersionDelay(model.dm, fLow, fRef) * 1.12);
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  for (let r = 0; r < rows; r += 1) {
    const frac = r / (rows - 1);
    const freq = fHigh - frac * (fHigh - fLow);
    const delay = dispersionDelay(model.dm, freq, fRef);
    for (let c = 0; c < cols; c += 1) {
      const time = c / (cols - 1) * delaySpan;
      const pulse = Math.exp(-0.5 * ((time - delay) / Math.max(0.18, delaySpan * 0.018)) ** 2);
      const texture = 0.08 + 0.09 * seededNoise(r * cols + c, 2);
      const intensity = Math.max(0, Math.min(1, pulse + texture));
      const color = heatColor(intensity);
      ctx.fillStyle = color;
      ctx.fillRect(
        pad.left + c * plotW / cols,
        pad.top + r * plotH / rows,
        plotW / cols + 1,
        plotH / rows + 1
      );
    }
  }

  ctx.fillStyle = "#aab4c3";
  ctx.font = "12px system-ui";
  ctx.fillText(`${Math.round(fHigh)} MHz`, pad.left + 6, pad.top + 16);
  ctx.fillText(`${Math.round(fLow)} MHz`, pad.left + 6, height - pad.bottom - 8);
  ctx.fillText(`0`, pad.left, height - 18);
  ctx.fillText(`${delaySpan.toFixed(1)} ms`, width - 92, height - 18);
}

function heatColor(t) {
  const r = Math.round(18 + 237 * t);
  const g = Math.round(36 + 154 * Math.max(0, t - 0.15));
  const b = Math.round(54 + 115 * (1 - t));
  return `rgb(${r}, ${g}, ${b})`;
}

function dispersionDelay(dm, nuMHz, refMHz) {
  return 4.148808e3 * dm * (nuMHz ** -2 - refMHz ** -2);
}

function simulate() {
  const model = {
    periodMs: value("period"),
    widthPct: value("width"),
    spindownRaw: value("spindown"),
    durationH: value("duration"),
    cadenceMin: value("cadence"),
    noiseMs: value("noise"),
    dm: value("dm"),
    freq: value("freq"),
    bandwidth: value("bandwidth"),
    glitchEpochPct: value("glitchEpoch"),
    glitchPpm: value("glitchSize"),
  };

  model.periodSec = model.periodMs / 1000;
  model.nu = 1 / model.periodSec;
  model.pdot = model.spindownRaw * 1e-14;
  model.nudot = -model.pdot / model.periodSec ** 2;
  model.durationSec = model.durationH * 3600;
  model.glitchTime = model.durationSec * model.glitchEpochPct / 100;

  updateLabels(model);
  const profile = makeProfile(model);
  const residuals = makeResiduals(model);
  latestToas = residuals;

  plotLine(canvases.profile, profile, {
    xLabel: "phase",
    yLabel: "intensity",
    xMin: 0,
    xMax: 1,
    yMin: -0.05,
    yMax: 1.2,
    color: "#5bd8ff",
  });

  const maxResidual = Math.max(0.2, ...residuals.map((p) => Math.abs(p.y))) * 1.2;
  plotLine(canvases.residual, residuals, {
    xLabel: "time (h)",
    yLabel: "residual (ms)",
    yMin: -maxResidual,
    yMax: maxResidual,
    color: "#f4b247",
    dotColor: "#ff6f91",
    scatter: true,
    thresholds: [
      { value: 0, color: "rgba(255,255,255,0.35)" },
    ],
  });

  drawWaterfall(model);
}

function makeProfile(model) {
  const bins = 64;
  const sigma = model.widthPct / 100;
  const points = [];

  for (let i = 0; i <= bins; i += 1) {
    const phase = i / bins;
    const mainPulse = gaussian(phase, 0.26, sigma);
    const interpulse = 0.36 * gaussian(phase, 0.72, sigma * 1.5);
    const baseline = 0.035 * Math.sin(phase * Math.PI * 6);
    const noise = 0.018 * seededNoise(i, 5);
    points.push({ x: phase, y: Math.max(0, mainPulse + interpulse + baseline + noise) });
  }

  return points;
}

function makeResiduals(model) {
  const count = Math.max(8, Math.floor((model.durationH * 60) / model.cadenceMin) + 1);
  const residuals = [];
  const glitchFractional = model.glitchPpm * 1e-6;

  for (let i = 0; i < count; i += 1) {
    const t = i * model.cadenceMin * 60;
    const postGlitchTime = Math.max(0, t - model.glitchTime);
    const unmodelledGlitchCycles = model.nu * glitchFractional * postGlitchTime;
    const glitchResidualMs = -unmodelledGlitchCycles * model.periodMs;
    const spinCurveMs = -0.5 * (model.nudot / model.nu) * t ** 2 * 1000;
    const redNoiseMs = model.noiseMs * 0.7 * Math.sin(i * 0.55) + model.noiseMs * seededNoise(i, 11);
    residuals.push({
      x: t / 3600,
      y: glitchResidualMs + spinCurveMs + redNoiseMs,
      toaSeconds: t + (glitchResidualMs + spinCurveMs + redNoiseMs) / 1000,
    });
  }

  return residuals;
}

function updateLabels(model) {
  outputs.period.textContent = `${model.periodMs.toFixed(1)} ms`;
  outputs.width.textContent = `${model.widthPct.toFixed(1)}%`;
  outputs.spindown.textContent = `${(model.spindownRaw / 10).toFixed(1)}e-13 s/s`;
  outputs.duration.textContent = `${model.durationH.toFixed(1)} h`;
  outputs.cadence.textContent = `${model.cadenceMin.toFixed(1)} min`;
  outputs.noise.textContent = `${model.noiseMs.toFixed(3)} ms`;
  outputs.dm.textContent = `${model.dm.toFixed(0)} pc cm^-3`;
  outputs.freq.textContent = `${model.freq.toFixed(0)} MHz`;
  outputs.bandwidth.textContent = `${model.bandwidth.toFixed(0)} MHz`;
  outputs.glitchEpoch.textContent = `${model.glitchEpochPct.toFixed(0)}%`;
  outputs.glitchSize.textContent = `${model.glitchPpm.toFixed(1)} ppm`;

  const fLow = model.freq - model.bandwidth / 2;
  const fHigh = model.freq + model.bandwidth / 2;
  const dmDelay = Math.max(0, dispersionDelay(model.dm, fLow, fHigh));
  const residuals = makeResiduals(model);
  const rms = Math.sqrt(residuals.reduce((sum, point) => sum + point.y ** 2, 0) / residuals.length);

  outputs.summaryPeriod.textContent = `${model.periodMs.toFixed(1)} ms`;
  outputs.summaryDm.textContent = `${dmDelay.toFixed(2)} ms`;
  outputs.summaryRms.textContent = `${rms.toFixed(3)} ms`;
  outputs.summaryGlitch.textContent = `${model.glitchPpm.toFixed(3)} ppm`;
}

function exportToas() {
  const rows = ["time_hours,toa_seconds,residual_ms"];
  latestToas.forEach((point) => {
    rows.push(`${point.x.toFixed(6)},${point.toaSeconds.toFixed(9)},${point.y.toFixed(6)}`);
  });
  const blob = new Blob([rows.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "synthetic_pulsar_toas.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function resetControls() {
  const defaults = {
    period: 33,
    width: 4.5,
    spindown: 42,
    duration: 3,
    cadence: 6,
    noise: 0.06,
    dm: 56,
    freq: 1400,
    bandwidth: 300,
    glitchEpoch: 55,
    glitchSize: 3,
  };
  Object.entries(defaults).forEach(([key, defaultValue]) => {
    controls[key].value = String(defaultValue);
  });
  simulate();
}

Object.values(controls).forEach((control) => control.addEventListener("input", simulate));
document.querySelector("#reset-button").addEventListener("click", resetControls);
document.querySelector("#export-button").addEventListener("click", exportToas);
window.addEventListener("resize", simulate);

simulate();
