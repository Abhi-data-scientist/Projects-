/**
 * AURA VISUALIZER ENGINE
 * Real-time Audio Reactive Visualizer with 5 Modes: AURA, WAVE, RADIAL, GRID, BAR
 * Matches futuristic monochrome + cyan glowing aesthetic.
 */

class VisualizerEngine {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.mode = 'AURA';
    this.analyser = null;
    this.animationId = null;
    this.time = 0;
    this.smoothVolume = 0;

    // High DPI scaling
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.width = rect.width;
    this.height = rect.height;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
  }

  setAnalyser(analyser) {
    this.analyser = analyser;
    if (analyser) {
      this.dataArray = new Uint8Array(analyser.frequencyBinCount);
      this.timeData  = new Uint8Array(analyser.fftSize);
    } else {
      this.dataArray = null;
      this.timeData  = null;
    }
  }

  setMode(mode) {
    this.mode = mode;
  }

  start() {
    if (!this.animationId) {
      this.animate();
    }
  }

  stop() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  getAudioMetrics() {
    if (!this.analyser || !this.dataArray) {
      this.smoothVolume += (0 - this.smoothVolume) * 0.1;
      return { volume: this.smoothVolume, freqData: null, timeData: null };
    }
    this.analyser.getByteFrequencyData(this.dataArray);
    this.analyser.getByteTimeDomainData(this.timeData);

    let sum = 0;
    const len = this.dataArray.length;
    for (let i = 0; i < len; i++) {
      sum += this.dataArray[i];
    }
    const rawVolume = sum / (len * 255);
    // Exponential smoothing for buttery visual dynamics
    this.smoothVolume += (rawVolume - this.smoothVolume) * 0.18;
    return {
      volume: this.smoothVolume,
      freqData: this.dataArray,
      timeData: this.timeData,
    };
  }

  getThemeColors() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
      isDark,
      primary: isDark ? '#22d3ee' : '#0891b2',
      secondary: isDark ? 'rgba(34, 211, 238, 0.45)' : 'rgba(8, 145, 178, 0.45)',
      dim: isDark ? 'rgba(34, 211, 238, 0.12)' : 'rgba(8, 145, 178, 0.12)',
      glow: isDark ? 'rgba(34, 211, 238, 0.35)' : 'rgba(8, 145, 178, 0.25)',
      gridDot: isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.15)',
    };
  }

  animate() {
    this.animationId = requestAnimationFrame(() => this.animate());
    this.time += 0.025;
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;
    ctx.clearRect(0, 0, w, h);

    const { volume, freqData, timeData } = this.getAudioMetrics();
    const colors = this.getThemeColors();

    switch (this.mode) {
      case 'AURA':
        this.renderAura(ctx, w, h, volume, freqData, colors);
        break;
      case 'WAVE':
        this.renderWave(ctx, w, h, volume, timeData, colors);
        break;
      case 'RADIAL':
        this.renderRadial(ctx, w, h, volume, freqData, colors);
        break;
      case 'GRID':
        this.renderGrid(ctx, w, h, volume, colors);
        break;
      case 'BAR':
        this.renderBars(ctx, w, h, volume, freqData, colors);
        break;
    }
  }

  // --------------------------------------------------------------------------
  // 1. AURA MODE (Exact match of uploaded screenshot visualizer)
  // --------------------------------------------------------------------------
  renderAura(ctx, w, h, vol, freq, colors) {
    const cx = w / 2;
    const cy = h / 2;
    const baseRadius = Math.min(w, h) * 0.26;
    const dynamicRadius = baseRadius + vol * 75;

    // Layer 1: Ambient Outer Cyan Glow Mist
    const gradient = ctx.createRadialGradient(cx, cy, baseRadius * 0.6, cx, cy, dynamicRadius * 1.6);
    gradient.addColorStop(0, 'transparent');
    gradient.addColorStop(0.65, colors.dim);
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(cx, cy, dynamicRadius * 1.6, 0, Math.PI * 2);
    ctx.fill();

    // Layer 2: Harmonic Fluid Ribbon Wave Ring
    ctx.save();
    ctx.shadowBlur = colors.isDark ? 32 : 16;
    ctx.shadowColor = colors.primary;

    const layers = [
      { alpha: 0.9, width: 4.5, freqOffset: 0, speedMult: 1.0, radOffset: 0 },
      { alpha: 0.55, width: 2.5, freqOffset: 12, speedMult: -0.75, radOffset: -6 },
      { alpha: 0.35, width: 2.0, freqOffset: 24, speedMult: 1.3, radOffset: 6 },
    ];

    layers.forEach((layer) => {
      ctx.beginPath();
      ctx.strokeStyle = colors.primary;
      ctx.lineWidth = layer.width;
      ctx.globalAlpha = layer.alpha;

      const segments = 120;
      for (let i = 0; i <= segments; i++) {
        const theta = (i / segments) * Math.PI * 2;
        // Harmonic undulating wave formula
        const freqAmp = freq ? (freq[(i + layer.freqOffset) % 64] / 255) * 45 : 0;
        const wave =
          Math.sin(theta * 4 + this.time * layer.speedMult) * (8 + vol * 30) +
          Math.cos(theta * 7 - this.time * 0.8) * (5 + vol * 20) +
          freqAmp;

        const r = dynamicRadius + layer.radOffset + wave;
        const x = cx + Math.cos(theta) * r;
        const y = cy + Math.sin(theta) * r;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.closePath();
      ctx.stroke();
    });

    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // 2. WAVE MODE (Sleek horizontal oscilloscope ribbon)
  // --------------------------------------------------------------------------
  renderWave(ctx, w, h, vol, timeData, colors) {
    const cy = h / 2;
    ctx.save();
    ctx.shadowBlur = colors.isDark ? 20 : 10;
    ctx.shadowColor = colors.primary;

    for (let layer = 0; layer < 3; layer++) {
      ctx.beginPath();
      ctx.strokeStyle = colors.primary;
      ctx.lineWidth = layer === 0 ? 3 : 1.5;
      ctx.globalAlpha = layer === 0 ? 0.9 : 0.45;

      const offset = (layer - 1) * 14;
      const step = w / 160;

      for (let x = 0; x <= w; x += step) {
        const idx = Math.floor((x / w) * (timeData ? timeData.length : 128));
        const val = timeData ? (timeData[idx] - 128) / 128 : 0;
        const idleWave = Math.sin((x / 60) + this.time * 2 + layer) * (6 + vol * 35);
        const y = cy + offset + val * (60 + vol * 120) + idleWave;

        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // 3. RADIAL MODE (Equalizer spikes in circular constellation)
  // --------------------------------------------------------------------------
  renderRadial(ctx, w, h, vol, freq, colors) {
    const cx = w / 2;
    const cy = h / 2;
    const baseRadius = Math.min(w, h) * 0.22;
    const count = 72;

    ctx.save();
    ctx.shadowBlur = colors.isDark ? 16 : 8;
    ctx.shadowColor = colors.primary;

    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const freqVal = freq ? freq[i % 64] / 255 : 0.1;
      const idle = Math.sin(this.time * 2 + i * 0.2) * 6;
      const spikeLen = 8 + freqVal * (60 + vol * 140) + idle;

      const x1 = cx + Math.cos(angle) * baseRadius;
      const y1 = cy + Math.sin(angle) * baseRadius;
      const x2 = cx + Math.cos(angle) * (baseRadius + spikeLen);
      const y2 = cy + Math.sin(angle) * (baseRadius + spikeLen);

      ctx.beginPath();
      ctx.strokeStyle = colors.primary;
      ctx.globalAlpha = 0.3 + freqVal * 0.7;
      ctx.lineWidth = 2.5;
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // 4. GRID MODE (Pulsing 3D-styled matrix)
  // --------------------------------------------------------------------------
  renderGrid(ctx, w, h, vol, colors) {
    const cols = 22;
    const rows = 14;
    const cellW = w / (cols + 1);
    const cellH = h / (rows + 1);

    ctx.save();
    for (let r = 1; r <= rows; r++) {
      for (let c = 1; c <= cols; c++) {
        const x = c * cellW;
        const y = r * cellH;
        const distFromCenter = Math.hypot(x - w / 2, y - h / 2) / (w * 0.4);
        const wave = Math.sin(distFromCenter * 6 - this.time * 3);
        const dotSize = Math.max(1.5, (1.8 + wave * 1.5 + vol * 5.5));

        ctx.fillStyle = distFromCenter < 0.65 ? colors.primary : colors.gridDot;
        ctx.globalAlpha = Math.max(0.2, 1 - distFromCenter * 0.9) * (0.4 + vol * 0.6);
        ctx.beginPath();
        ctx.arc(x, y, dotSize, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // 5. BAR MODE (Symmetrical spectrum equalizer bars)
  // --------------------------------------------------------------------------
  renderBars(ctx, w, h, vol, freq, colors) {
    const bars = 48;
    const barWidth = 6;
    const gap = 5;
    const totalW = bars * (barWidth + gap);
    const startX = (w - totalW) / 2;
    const cy = h / 2;

    ctx.save();
    ctx.shadowBlur = colors.isDark ? 14 : 6;
    ctx.shadowColor = colors.primary;

    for (let i = 0; i < bars; i++) {
      const freqIdx = Math.abs(i - bars / 2) * 2;
      const val = freq ? freq[freqIdx % 64] / 255 : 0.08;
      const idle = Math.sin(this.time * 3 + i * 0.3) * 6;
      const barHeight = Math.max(6, val * 160 + idle + vol * 60);

      const x = startX + i * (barWidth + gap);
      const y = cy - barHeight / 2;

      ctx.fillStyle = colors.primary;
      ctx.globalAlpha = 0.4 + val * 0.6;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barHeight, 3);
      ctx.fill();
    }
    ctx.restore();
  }
}

window.VisualizerEngine = VisualizerEngine;
