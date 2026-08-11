(() => {
  "use strict";

  const DEFAULTS = Object.freeze({
    pulsar: "J1713+0747",
    playbackRate: 24,
    modelOverlay: false,
    periodMs: 4.57,
    nudotScale: -0.4,
    pulseWidthMs: 0.25,
    dm: 15.99,
    centreFrequencyMHz: 1400,
    bandwidthMHz: 800,
    redNoiseUs: 0.3,
    redSpectralIndex: 4,
    whiteNoiseUs: 0.05,
    glitchEnabled: false,
    glitchEpochFraction: 58,
    glitchPpm: 0.001,
  });

  const controls = Object.fromEntries(
    Object.keys(DEFAULTS).map((id) => [id, document.getElementById(id)])
  );
  const outputs = {
    playbackRate: document.getElementById("playbackRate-value"),
    modelOverlay: document.getElementById("modelOverlay-value"),
    periodMs: document.getElementById("periodMs-value"),
    nudotScale: document.getElementById("nudotScale-value"),
    pulseWidthMs: document.getElementById("pulseWidthMs-value"),
    dm: document.getElementById("dm-value"),
    centreFrequencyMHz: document.getElementById("centreFrequencyMHz-value"),
    bandwidthMHz: document.getElementById("bandwidthMHz-value"),
    redNoiseUs: document.getElementById("redNoiseUs-value"),
    redSpectralIndex: document.getElementById("redSpectralIndex-value"),
    whiteNoiseUs: document.getElementById("whiteNoiseUs-value"),
    glitchEpochFraction: document.getElementById("glitchEpochFraction-value"),
    glitchPpm: document.getElementById("glitchPpm-value"),
  };
  const readouts = {
    utc: document.getElementById("utc-clock"),
    engineIndicator: document.getElementById("engine-indicator"),
    engineState: document.getElementById("engine-state"),
    frameRate: document.getElementById("frame-rate"),
    cursorMjd: document.getElementById("cursor-mjd"),
    frequency: document.getElementById("frequency-readout"),
    nudot: document.getElementById("nudot-readout"),
    dispersion: document.getElementById("dispersion-readout"),
    frequencyBand: document.getElementById("frequency-band-readout"),
    rms: document.getElementById("rms-readout"),
    toaCount: document.getElementById("toa-count-readout"),
    glitch: document.getElementById("glitch-readout"),
    deltaFrequency: document.getElementById("delta-frequency-readout"),
    compute: document.getElementById("compute-readout"),
    residualCursor: document.getElementById("residual-cursor"),
    residualExtrema: document.getElementById("residual-extrema"),
    dmx: document.getElementById("waterfall-readout"),
    ptaValue: document.getElementById("pta-value-note"),
    status: document.getElementById("status-message"),
    events: document.getElementById("event-log"),
  };
  const buttons = {
    play: document.getElementById("play-button"),
    reseed: document.getElementById("reseed-button"),
    export: document.getElementById("export-button"),
    reset: document.getElementById("reset-button"),
  };
  const modelParameters = document.getElementById("model-parameters");

  class CanvasSurface {
    constructor(id) {
      this.canvas = document.getElementById(id);
      this.context = this.canvas.getContext("2d", { alpha: false, desynchronized: true });
      this.width = 0;
      this.height = 0;
      this.ratio = 1;
    }

    prepare() {
      const bounds = this.canvas.getBoundingClientRect();
      const width = Math.max(10, Math.round(bounds.width));
      const height = Math.max(10, Math.round(bounds.height));
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      if (width !== this.width || height !== this.height || ratio !== this.ratio) {
        this.width = width;
        this.height = height;
        this.ratio = ratio;
        this.canvas.width = Math.round(width * ratio);
        this.canvas.height = Math.round(height * ratio);
      }
      this.context.setTransform(ratio, 0, 0, ratio, 0, 0);
      this.context.fillStyle = "#171a21";
      this.context.fillRect(0, 0, width, height);
      return { ctx: this.context, width, height };
    }
  }

  const surfaces = {
    residual: new CanvasSurface("residual-canvas"),
    dmx: new CanvasSurface("waterfall-canvas"),
    profile: new CanvasSurface("profile-canvas"),
  };

  const state = {
    worker: null,
    requestId: 0,
    seed: 48271,
    snapshot: null,
    playing: true,
    playback: null,
    debounce: 0,
    events: [],
    renderTime: performance.now(),
    frameCounter: 0,
    frameWindowStart: performance.now(),
  };

  function numericValue(id) {
    return Number(controls[id].value);
  }

  function parameterPayload() {
    return {
      pulsar: controls.pulsar.value,
      playbackRecordsPerSecond: numericValue("playbackRate"),
      modelOverlay: controls.modelOverlay.checked,
      periodMs: numericValue("periodMs"),
      nudotHzPerSecond: numericValue("nudotScale") * 1e-15,
      pulseWidthMs: numericValue("pulseWidthMs"),
      dispersionMeasure: numericValue("dm"),
      centreFrequencyMHz: numericValue("centreFrequencyMHz"),
      bandwidthMHz: numericValue("bandwidthMHz"),
      redNoiseRmsSeconds: numericValue("redNoiseUs") * 1e-6,
      redSpectralIndex: numericValue("redSpectralIndex"),
      whiteNoiseRmsSeconds: numericValue("whiteNoiseUs") * 1e-6,
      glitchEnabled: controls.glitchEnabled.checked,
      glitchEpochFraction: numericValue("glitchEpochFraction") / 100,
      glitchFractionalStep: numericValue("glitchPpm") * 1e-6,
    };
  }

  function formatInputLabels() {
    outputs.playbackRate.textContent = `${numericValue("playbackRate").toFixed(0)} records/s`;
    outputs.modelOverlay.textContent = controls.modelOverlay.checked ? "ON" : "OFF";
    outputs.periodMs.textContent = `${numericValue("periodMs").toFixed(3)} ms`;
    outputs.nudotScale.textContent = `${numericValue("nudotScale").toFixed(2)} x10^-15 Hz/s`;
    outputs.pulseWidthMs.textContent = `${numericValue("pulseWidthMs").toFixed(2)} ms`;
    outputs.dm.textContent = `${numericValue("dm").toFixed(2)} pc cm^-3`;
    outputs.centreFrequencyMHz.textContent = `${numericValue("centreFrequencyMHz").toFixed(0)} MHz`;
    outputs.bandwidthMHz.textContent = `${numericValue("bandwidthMHz").toFixed(0)} MHz`;
    outputs.redNoiseUs.textContent = `${numericValue("redNoiseUs").toFixed(2)} us`;
    outputs.redSpectralIndex.textContent = numericValue("redSpectralIndex").toFixed(1);
    outputs.whiteNoiseUs.textContent = `${numericValue("whiteNoiseUs").toFixed(2)} us`;
    outputs.glitchEpochFraction.textContent = `${numericValue("glitchEpochFraction").toFixed(0)}%`;
    outputs.glitchPpm.textContent = `${numericValue("glitchPpm").toFixed(4)} ppm`;
    modelParameters.classList.toggle("inactive", !controls.modelOverlay.checked);
  }

  function setEngineState(label, style, message) {
    readouts.engineState.textContent = label;
    readouts.engineIndicator.className = `indicator ${style}`;
    if (message) {
      readouts.status.textContent = message;
    }
  }

  function addEvent(message) {
    const stamp = new Date().toISOString().slice(11, 19);
    state.events.unshift(`${stamp}  ${message}`);
    state.events.length = Math.min(state.events.length, 8);
    readouts.events.replaceChildren(
      ...state.events.map((text) => {
        const item = document.createElement("li");
        item.textContent = text;
        return item;
      })
    );
  }

  function configure(immediate = false) {
    formatInputLabels();
    if (!state.worker) {
      return;
    }
    clearTimeout(state.debounce);
    const dispatch = () => {
      state.requestId += 1;
      setEngineState("LOADING", "computing", "LOADING NANOGRAV RELEASE PRODUCTS / COMPUTING VIEW");
      state.worker.postMessage({
        type: "configure",
        requestId: state.requestId,
        seed: state.seed,
        parameters: parameterPayload(),
      });
    };
    if (immediate) {
      dispatch();
    } else {
      state.debounce = window.setTimeout(dispatch, 35);
    }
  }

  function updateTelemetry(telemetry) {
    readouts.frequency.textContent = telemetry.pulsar;
    readouts.nudot.textContent = "NANOGRAV 11Y / RELEASED";
    readouts.dispersion.textContent =
      `${(telemetry.dmxMinimum * 1000).toFixed(3)} to ${(telemetry.dmxMaximum * 1000).toFixed(3)}`;
    readouts.frequencyBand.textContent = `x10^-3 PC CM^-3 / ${telemetry.dmxCount} DMX BINS`;
    readouts.rms.textContent = formatResidual(telemetry.observedRmsUs);
    if (readouts.ptaValue && telemetry.ptaValueClassification) {
      readouts.ptaValue.textContent = `PTA value: ${telemetry.ptaValueClassification}`;
    }
    const spanYears = (telemetry.lastMjd - telemetry.firstMjd) / 365.25;
    readouts.toaCount.textContent = `${telemetry.residualCount} SAMPLES / ${spanYears.toFixed(2)} YR`;
    if (telemetry.modelOverlay) {
      readouts.glitch.textContent = telemetry.glitchEnabled ? `MJD ${telemetry.glitchMjd.toFixed(2)}` : "MODEL ON";
      readouts.deltaFrequency.textContent = telemetry.glitchEnabled
        ? `DELTA NU ${telemetry.deltaFrequencyHz.toExponential(3)} HZ`
        : `NU ${telemetry.spinFrequencyHz.toFixed(5)} HZ / NO GLITCH`;
    } else {
      readouts.glitch.textContent = "OFF";
      readouts.deltaFrequency.textContent = "RELEASED DATA ONLY";
    }
    readouts.compute.textContent = `${telemetry.computeMilliseconds.toFixed(2)} ms`;
    readouts.residualExtrema.textContent =
      `RANGE: ${formatResidual(telemetry.minimumResidualUs)} TO ${formatResidual(telemetry.maximumResidualUs)}`;
    readouts.dmx.textContent =
      `${telemetry.dmxCount} BINS / ${(telemetry.dmxMinimum * 1000).toFixed(3)} TO ` +
      `${(telemetry.dmxMaximum * 1000).toFixed(3)} x10^-3`;
  }

  function handleWorkerMessage(event) {
    const message = event.data;
    if (message.type === "products") {
      if (message.requestId !== state.requestId) {
        return;
      }
      state.snapshot = message;
      updateTelemetry(message.telemetry);
      setEngineState("ONLINE", "ready", "NANOGRAV OBSERVATIONS LOADED / PRODUCTS CURRENT");
      const overlay = message.telemetry.modelOverlay ? " / MODEL OVERLAY ON" : "";
      addEvent(
        `${message.metadata.pulsar}: ${message.telemetry.residualCount} residuals + ` +
        `${message.telemetry.dmxCount} DMX bins${overlay}`
      );
      return;
    }
    if (message.type === "playback") {
      state.playback = message;
      readouts.cursorMjd.textContent = message.mjd.toFixed(4);
      readouts.residualCursor.textContent =
        `CURSOR: MJD ${message.mjd.toFixed(4)} / RELEASED ${formatResidual(message.residualUs)}`;
      return;
    }
    if (message.type === "csv") {
      downloadCsv(message.content, message.filename);
      addEvent(`Exported ${message.rowCount} released residual samples`);
      return;
    }
    if (message.type === "dataError") {
      if (message.requestId !== state.requestId) {
        return;
      }
      setEngineState("FAILED", "error", "NANOGRAV DATA UNAVAILABLE / SERVE PROJECT OVER HTTP");
      addEvent(`Data load failed: ${message.message}`);
      return;
    }
    if (message.type === "warning") {
      addEvent(message.message);
    }
  }

  function downloadCsv(content, filename) {
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function formatResidual(valueUs) {
    const magnitude = Math.abs(valueUs);
    if (magnitude >= 1000000) {
      return `${(valueUs / 1000000).toFixed(3)} s`;
    }
    if (magnitude >= 1000) {
      return `${(valueUs / 1000).toFixed(3)} ms`;
    }
    return `${valueUs.toFixed(3)} us`;
  }

  function abbreviatedResidual(valueUs) {
    const magnitude = Math.abs(valueUs);
    if (magnitude >= 1000000) {
      return `${(valueUs / 1000000).toFixed(1)}s`;
    }
    if (magnitude >= 1000) {
      return `${(valueUs / 1000).toFixed(1)}ms`;
    }
    return `${valueUs.toFixed(1)}us`;
  }

  function chartBounds(ctx, width, height, xTicks, yTicks, xLabel, yLabel) {
    const margins = { left: 70, top: 16, right: 18, bottom: 41 };
    const plotWidth = Math.max(1, width - margins.left - margins.right);
    const plotHeight = Math.max(1, height - margins.top - margins.bottom);
    ctx.strokeStyle = "rgba(85, 113, 142, 0.22)";
    ctx.lineWidth = 1;
    for (let index = 0; index <= xTicks; index += 1) {
      const x = margins.left + plotWidth * index / xTicks;
      ctx.beginPath();
      ctx.moveTo(x + 0.5, margins.top);
      ctx.lineTo(x + 0.5, margins.top + plotHeight);
      ctx.stroke();
    }
    for (let index = 0; index <= yTicks; index += 1) {
      const y = margins.top + plotHeight * index / yTicks;
      ctx.beginPath();
      ctx.moveTo(margins.left, y + 0.5);
      ctx.lineTo(margins.left + plotWidth, y + 0.5);
      ctx.stroke();
    }
    ctx.fillStyle = "#8b93a3";
    ctx.font = '11px "Roboto Mono", "Cascadia Mono", Consolas, monospace';
    ctx.fillText(yLabel, 10, margins.top + 8);
    ctx.textAlign = "right";
    ctx.fillText(xLabel, width - margins.right, height - 8);
    ctx.textAlign = "left";
    return { ...margins, plotWidth, plotHeight };
  }

  function writeAxisTicks(ctx, box, xMin, xMax, yMin, yMax, xTicks, yTicks, formatX, formatY) {
    ctx.fillStyle = "#8b93a3";
    ctx.font = '10px "Roboto Mono", "Cascadia Mono", Consolas, monospace';
    for (let index = 0; index <= xTicks; index += 1) {
      const ratio = index / xTicks;
      const x = box.left + ratio * box.plotWidth;
      ctx.textAlign = index === 0 ? "left" : index === xTicks ? "right" : "center";
      ctx.fillText(formatX(xMin + ratio * (xMax - xMin)), x, box.top + box.plotHeight + 19);
    }
    ctx.textAlign = "right";
    for (let index = 0; index <= yTicks; index += 1) {
      const ratio = index / yTicks;
      const y = box.top + ratio * box.plotHeight;
      ctx.fillText(formatY(yMax - ratio * (yMax - yMin)), box.left - 9, y + 3);
    }
    ctx.textAlign = "left";
  }

  function plotPath(ctx, xValues, yValues, coordinate, stroke, width, dash = []) {
    if (!yValues || !yValues.length) {
      return;
    }
    ctx.strokeStyle = stroke;
    ctx.lineWidth = width;
    ctx.setLineDash(dash);
    ctx.beginPath();
    for (let index = 0; index < xValues.length; index += 1) {
      const x = coordinate.x(xValues[index]);
      const y = coordinate.y(yValues[index]);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function drawUncertaintyBand(ctx, xValues, values, uncertainties, coordinate, fill) {
    ctx.fillStyle = fill;
    ctx.beginPath();
    for (let index = 0; index < values.length; index += 1) {
      const x = coordinate.x(xValues[index]);
      const y = coordinate.y(values[index] + uncertainties[index]);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    for (let index = values.length - 1; index >= 0; index -= 1) {
      ctx.lineTo(coordinate.x(xValues[index]), coordinate.y(values[index] - uncertainties[index]));
    }
    ctx.closePath();
    ctx.fill();
  }

  function drawResiduals() {
    const { ctx, width, height } = surfaces.residual.prepare();
    if (!state.snapshot) {
      drawWaiting(ctx, width, height, "AWAITING NANOGRAV RESIDUALS");
      return;
    }
    const data = state.snapshot.residuals;
    const telemetry = state.snapshot.telemetry;
    const xMin = data.mjd[0];
    const xMax = data.mjd[data.mjd.length - 1];
    const yLimit = Math.max(
      Math.abs(telemetry.minimumResidualUs),
      Math.abs(telemetry.maximumResidualUs),
      0.01
    ) * 1.1;
    const box = chartBounds(ctx, width, height, 5, 5, "DISPLAY MJD", "US");
    const coordinate = {
      x: (value) => box.left + (value - xMin) / (xMax - xMin || 1) * box.plotWidth,
      y: (value) => box.top + (yLimit - value) / (2 * yLimit) * box.plotHeight,
    };
    writeAxisTicks(ctx, box, xMin, xMax, -yLimit, yLimit, 5, 5,
      (value) => value.toFixed(0), abbreviatedResidual);
    ctx.strokeStyle = "rgba(220, 231, 239, 0.42)";
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(box.left, coordinate.y(0));
    ctx.lineTo(box.left + box.plotWidth, coordinate.y(0));
    ctx.stroke();
    ctx.setLineDash([]);

    drawUncertaintyBand(ctx, data.mjd, data.residualUs, data.uncertaintyUs, coordinate, "rgba(48, 214, 229, 0.09)");
    if (data.modelResidualUs) {
      plotPath(ctx, data.mjd, data.modelResidualUs, coordinate, "#f2b866", 1.5);
      if (telemetry.glitchEnabled) {
        const eventX = coordinate.x(telemetry.glitchMjd);
        ctx.strokeStyle = "#e8778a";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 4]);
        ctx.beginPath();
        ctx.moveTo(eventX, box.top);
        ctx.lineTo(eventX, box.top + box.plotHeight);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "#e8778a";
        ctx.font = '10px "Roboto Mono", Consolas, monospace';
        ctx.fillText("MODEL GLITCH", Math.min(eventX + 5, width - 110), box.top + 13);
      }
    }
    plotPath(ctx, data.mjd, data.residualUs, coordinate, "#d1a256", 1.25);
    const markerStride = Math.max(1, Math.ceil(data.mjd.length / 230));
    ctx.fillStyle = "#d1a256";
    for (let index = 0; index < data.mjd.length; index += markerStride) {
      ctx.beginPath();
      ctx.arc(coordinate.x(data.mjd[index]), coordinate.y(data.residualUs[index]), 1.55, 0, Math.PI * 2);
      ctx.fill();
    }
    if (state.playback) {
      const cursorX = coordinate.x(state.playback.mjd);
      const cursorY = coordinate.y(state.playback.residualUs);
      ctx.strokeStyle = "rgba(76, 224, 162, 0.8)";
      ctx.beginPath();
      ctx.moveTo(cursorX, box.top);
      ctx.lineTo(cursorX, box.top + box.plotHeight);
      ctx.stroke();
      ctx.fillStyle = "#6fcf97";
      ctx.beginPath();
      ctx.arc(cursorX, cursorY, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawDmx() {
    const { ctx, width, height } = surfaces.dmx.prepare();
    if (!state.snapshot) {
      drawWaiting(ctx, width, height, "AWAITING NANOGRAV DMX PRODUCT");
      return;
    }
    const data = state.snapshot.dmx;
    const values = new Float64Array(data.value.length);
    const uncertainty = new Float64Array(data.uncertainty.length);
    let yMin = Infinity;
    let yMax = -Infinity;
    for (let index = 0; index < data.value.length; index += 1) {
      values[index] = data.value[index] * 1000;
      uncertainty[index] = data.uncertainty[index] * 1000;
      yMin = Math.min(yMin, values[index] - uncertainty[index]);
      yMax = Math.max(yMax, values[index] + uncertainty[index]);
    }
    const padding = Math.max(0.02, (yMax - yMin) * 0.1);
    yMin -= padding;
    yMax += padding;
    const xMin = data.mjd[0];
    const xMax = data.mjd[data.mjd.length - 1];
    const box = chartBounds(ctx, width, height, 5, 5, "MJD", "DMX x10^-3");
    const coordinate = {
      x: (value) => box.left + (value - xMin) / (xMax - xMin || 1) * box.plotWidth,
      y: (value) => box.top + (yMax - value) / (yMax - yMin || 1) * box.plotHeight,
    };
    writeAxisTicks(ctx, box, xMin, xMax, yMin, yMax, 5, 5,
      (value) => value.toFixed(0), (value) => value.toFixed(2));
    if (yMin <= 0 && yMax >= 0) {
      ctx.strokeStyle = "rgba(220, 231, 239, 0.38)";
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(box.left, coordinate.y(0));
      ctx.lineTo(box.left + box.plotWidth, coordinate.y(0));
      ctx.stroke();
      ctx.setLineDash([]);
    }
    drawUncertaintyBand(ctx, data.mjd, values, uncertainty, coordinate, "rgba(48, 214, 229, 0.12)");
    plotPath(ctx, data.mjd, values, coordinate, "#d1a256", 1.65);
    ctx.fillStyle = "#d1a256";
    const markerStride = Math.max(1, Math.ceil(values.length / 180));
    for (let index = 0; index < values.length; index += markerStride) {
      ctx.beginPath();
      ctx.arc(coordinate.x(data.mjd[index]), coordinate.y(values[index]), 1.8, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawProfile() {
    const { ctx, width, height } = surfaces.profile.prepare();
    if (!state.snapshot || !state.snapshot.profile) {
      drawWaiting(ctx, width, height, "ENABLE SIMULATION OVERLAY");
      return;
    }
    const profile = state.snapshot.profile;
    const box = chartBounds(ctx, width, height, 4, 4, "PHASE", "I");
    const coordinate = {
      x: (value) => box.left + value * box.plotWidth,
      y: (value) => box.top + (1.08 - value) / 1.08 * box.plotHeight,
    };
    writeAxisTicks(ctx, box, 0, 1, 0, 1, 4, 4,
      (value) => value.toFixed(2), (value) => value.toFixed(2));
    ctx.fillStyle = "rgba(255, 182, 77, 0.12)";
    ctx.beginPath();
    ctx.moveTo(coordinate.x(0), coordinate.y(0));
    for (let index = 0; index < profile.phase.length; index += 1) {
      ctx.lineTo(coordinate.x(profile.phase[index]), coordinate.y(profile.intensity[index]));
    }
    ctx.lineTo(coordinate.x(1), coordinate.y(0));
    ctx.closePath();
    ctx.fill();
    plotPath(ctx, profile.phase, profile.intensity, coordinate, "#f2b866", 1.7);
  }

  function drawWaiting(ctx, width, height, message) {
    ctx.fillStyle = "#8b93a3";
    ctx.font = '12px "Roboto Mono", Consolas, monospace';
    ctx.textAlign = "center";
    ctx.fillText(message, width / 2, height / 2);
    ctx.textAlign = "left";
  }

  function render(timestamp) {
    state.renderTime = timestamp;
    state.frameCounter += 1;
    if (timestamp - state.frameWindowStart >= 1000) {
      const fps = state.frameCounter * 1000 / (timestamp - state.frameWindowStart);
      readouts.frameRate.textContent = `${fps.toFixed(0)} fps`;
      state.frameCounter = 0;
      state.frameWindowStart = timestamp;
    }
    drawResiduals();
    drawDmx();
    drawProfile();
    window.requestAnimationFrame(render);
  }

  function resetControls() {
    for (const [id, defaultValue] of Object.entries(DEFAULTS)) {
      if (controls[id].type === "checkbox") {
        controls[id].checked = defaultValue;
      } else {
        controls[id].value = String(defaultValue);
      }
    }
    state.seed = 48271;
    addEvent("Data view and optional model controls restored");
    configure(true);
  }

  function updateClock() {
    readouts.utc.textContent = new Date().toISOString().slice(11, 19);
  }

  function initialiseWorker() {
    if (!window.Worker) {
      setEngineState("FAILED", "error", "WEB WORKERS ARE NOT SUPPORTED BY THIS BROWSER");
      return;
    }
    try {
      state.worker = new Worker("assets/js/physicsWorker.js");
    } catch (error) {
      setEngineState("FAILED", "error", "SERVE THIS DIRECTORY OVER HTTP TO ENABLE THE WORKER");
      addEvent(`Worker creation failed: ${error.message}`);
      return;
    }
    state.worker.addEventListener("message", handleWorkerMessage);
    state.worker.addEventListener("error", (error) => {
      setEngineState("FAILED", "error", "WORKER ERROR / CHECK CONSOLE");
      addEvent(`Worker error: ${error.message || "unknown failure"}`);
    });
    state.worker.postMessage({ type: "setPlayback", playing: true });
    configure(true);
  }

  for (const control of Object.values(controls)) {
    control.addEventListener("input", () => configure(false));
    control.addEventListener("change", () => configure(true));
  }

  buttons.play.addEventListener("click", () => {
    state.playing = !state.playing;
    buttons.play.textContent = state.playing ? "PAUSE STREAM" : "RESUME STREAM";
    buttons.play.classList.toggle("paused", !state.playing);
    buttons.play.setAttribute("aria-pressed", String(state.playing));
    if (state.worker) {
      state.worker.postMessage({ type: "setPlayback", playing: state.playing });
    }
    addEvent(state.playing ? "Released-product cursor resumed" : "Released-product cursor paused");
  });

  buttons.reseed.addEventListener("click", () => {
    state.seed = (state.seed * 1664525 + 1013904223) >>> 0;
    addEvent(controls.modelOverlay.checked
      ? `Optional stochastic injection reseeded / ${state.seed}`
      : "Model seed updated; enable simulation overlay to display it");
    configure(true);
  });

  buttons.export.addEventListener("click", () => {
    if (state.worker && state.snapshot) {
      state.worker.postMessage({ type: "exportCsv" });
    }
  });

  buttons.reset.addEventListener("click", resetControls);
  window.addEventListener("resize", () => {
    drawResiduals();
    drawDmx();
    drawProfile();
  });

  formatInputLabels();
  updateClock();
  window.setInterval(updateClock, 1000);
  initialiseWorker();
  window.requestAnimationFrame(render);
})();
