import { Simulation } from './simulation.js';
import { Renderer } from '../lib/renderer.js';
import { UI } from './ui.js';
import { THEME } from './theme.js';

const canvas = document.getElementById('sim-canvas');
const sim = new Simulation();
const renderer = new Renderer(canvas, THEME);
const ui = new UI();

function syncSize() {
  sim.setCanvasSize(renderer.w, renderer.h);
}

let running = false;
let lastTime = 0;
let animId = null;

function drawKineticsChart(ctx, w, h, history, sim) {
  const padL = 44;
  const padR = 14;
  const padT = 22;
  const padB = 24;
  const chartW = w - padL - padR;
  const chartH = h - padT - padB;
  if (chartW <= 0 || chartH <= 0) return;

  // Panel background
  ctx.fillStyle = 'rgba(15, 15, 35, 0.82)';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(78, 205, 196, 0.35)';
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);

  // Title
  ctx.fillStyle = '#e8e8f0';
  ctx.font = '12px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('Conversion vs time', 8, 15);

  // Axes
  ctx.strokeStyle = 'rgba(255,255,255,0.2)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, h - padB);
  ctx.lineTo(w - padR, h - padB);
  ctx.stroke();

  // Y-axis label (0–100%)
  ctx.fillStyle = 'rgba(200,200,220,0.75)';
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText('100%', padL - 4, padT + 4);
  ctx.fillText('50%', padL - 4, padT + chartH / 2 + 3);
  ctx.fillText('0%', padL - 4, h - padB + 3);

  // Horizontal grid lines at 0, 50, 100
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  for (const pct of [50]) {
    const y = padT + chartH * (1 - pct / 100);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
  }

  // Determine time range for axes (keep expanding time domain)
  let tMax = 0;
  if (history.length > 1) {
    tMax = history[history.length - 1].t;
  }
  if (tMax < 1) tMax = 1;

  // X-axis label
  ctx.fillStyle = 'rgba(200,200,220,0.75)';
  ctx.textAlign = 'center';
  ctx.fillText('time (s)', padL + chartW / 2, h - 6);

  // Theoretical first-order curve: p(t) = 100 * (1 - exp(-k_eff * t))
  // Estimate k_eff from current data, or use a default
  let kEff = 0;
  if (history.length > 5) {
    // Fit by eye: pick the last p% point
    const last = history[history.length - 1];
    if (last.t > 0.5 && last.p > 0) {
      const frac = Math.min(0.99, last.p / 100);
      kEff = -Math.log(1 - frac) / last.t;
    }
  }
  if (kEff <= 0) kEff = 0.3;

  // Draw theoretical curve
  ctx.strokeStyle = 'rgba(255, 107, 107, 0.7)';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  const steps = 60;
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * tMax;
    const p = 100 * (1 - Math.exp(-kEff * t));
    const x = padL + (t / tMax) * chartW;
    const y = padT + chartH * (1 - p / 100);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.setLineDash([]);

  // Observed conversion curve
  if (history.length >= 2) {
    ctx.strokeStyle = '#4ecdc4';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < history.length; i++) {
      const t = history[i].t;
      const p = history[i].p;
      const x = padL + (t / tMax) * chartW;
      const y = padT + chartH * (1 - p / 100);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Current value marker
    const lastPt = history[history.length - 1];
    const lx = padL + (lastPt.t / tMax) * chartW;
    const ly = padT + chartH * (1 - lastPt.p / 100);
    ctx.fillStyle = '#4ecdc4';
    ctx.beginPath();
    ctx.arc(lx, ly, 3, 0, Math.PI * 2);
    ctx.fill();
  }

  // Legend
  ctx.textAlign = 'left';
  ctx.font = '10px sans-serif';
  ctx.fillStyle = '#4ecdc4';
  ctx.fillText('— observed', padL + 6, padT + 8);
  ctx.strokeStyle = 'rgba(255, 107, 107, 0.9)';
  ctx.beginPath();
  ctx.moveTo(padL + 6, padT + 14);
  ctx.lineTo(padL + 20, padT + 14);
  ctx.stroke();
  ctx.fillStyle = 'rgba(255, 107, 107, 0.9)';
  ctx.fillText('first-order model', padL + 24, padT + 16);
}

function drawChartOverlay(renderer, sim) {
  const chartW = 230;
  const chartH = 130;
  const margin = 12;
  const w = renderer.w;
  const ctx = renderer.ctx;

  const x = w - chartW - margin;
  const y = margin;

  ctx.save();
  ctx.translate(x, y);
  drawKineticsChart(ctx, chartW, chartH, sim.getConversionHistory(), sim);
  ctx.restore();
}

function renderLabJournal(sim) {
  const listEl = document.getElementById('lab-journal-list');
  if (!listEl) return;
  const log = sim.getEventLog();
  if (!log || log.length === 0) {
    listEl.innerHTML = '<li class="empty">waiting for events…</li>';
    return;
  }
  // Render in reverse chronological order (most recent at the top)
  const html = [];
  for (let i = log.length - 1; i >= 0; i--) {
    const ev = log[i];
    const time = ev.t.toFixed(2) + 's';
    html.push(`<li><span class="ev-time">${time}</span><span class="ev-${ev.kind}">${ev.text}</span></li>`);
  }
  listEl.innerHTML = html.join('');
}

function loop(timestamp) {
  if (!running) return;

  const dt = lastTime ? Math.min((timestamp - lastTime) / 1000, 0.1) : 0.016;
  lastTime = timestamp;

  syncSize();
  sim.tick(dt);

  if (sim.calloutEvent) {
    renderer.drawCallout(sim.calloutEvent.title, sim.calloutEvent.drawFn);
    renderer._scheduleCalloutClear();
    sim.calloutEvent = null;
  }

  const { particles, stats } = sim.getState();
  stats.time = sim.time;
  renderer.draw(particles);
  drawChartOverlay(renderer, sim);
  renderLabJournal(sim);
  ui.updateReadouts(stats);
  ui.updateStageBadges({ ...stats, totalMonomers: sim.params.monomerCount });

  animId = requestAnimationFrame(loop);
}

function play() {
  if (running) return;
  running = true;
  lastTime = 0;
  animId = requestAnimationFrame(loop);
}

function pause() {
  running = false;
  if (animId) cancelAnimationFrame(animId);
}

ui.on('play', play);
ui.on('pause', pause);
ui.on('reset', () => {
  pause();
  sim.reset();
  const { particles, stats } = sim.getState();
  stats.time = sim.time;
  syncSize();
  renderer.draw(particles);
  drawChartOverlay(renderer, sim);
  renderLabJournal(sim);
  ui.updateReadouts(stats);
  ui.updateStageBadges({ ...stats, totalMonomers: sim.params.monomerCount });
});
ui.on('paramChange', (params) => {
  sim.setParams(params);
});
ui.on('speedChange', (speed) => {
  sim.setParams({ speedMultiplier: speed });
});

syncSize();
sim.reset();
const { particles, stats } = sim.getState();
stats.time = sim.time;
renderer.draw(particles);
drawChartOverlay(renderer, sim);
renderLabJournal(sim);
ui.updateReadouts(stats);
