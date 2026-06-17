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

function loop(timestamp) {
  if (!running) return;

  const dt = lastTime ? Math.min((timestamp - lastTime) / 1000, 0.1) : 0.016;
  lastTime = timestamp;

  syncSize();
  sim.tick(dt);

  const { particles, stats, dpHistory } = sim.getState();
  stats.time = sim.time;

  // Draw Carothers chart as the persistent callout
  if (dpHistory && dpHistory.length > 1) {
    renderer.drawCallout('DP vs Conversion', (ctx, w, h) => {
      const pad = { top: 14, bottom: 16, left: 20, right: 8 };
      const plotW = w - pad.left - pad.right;
      const plotH = h - pad.top - pad.bottom;

      // Background
      ctx.fillStyle = 'rgba(0,0,0,0.3)';
      ctx.fillRect(0, 0, w, h);

      // Find max DP for log scaling
      let maxDP = 2;
      for (const d of dpHistory) {
        if (d.dpTheory > maxDP) maxDP = d.dpTheory;
        if (d.dpActual > maxDP) maxDP = d.dpActual;
      }
      const logMax = Math.log10(maxDP);

      // Axes
      ctx.strokeStyle = 'rgba(255,255,255,0.15)';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, h - pad.bottom);
      ctx.lineTo(w - pad.right, h - pad.bottom);
      ctx.stroke();

      // Grid lines
      for (let i = 0; i <= 4; i++) {
        const x = pad.left + (i / 4) * plotW;
        ctx.beginPath();
        ctx.moveTo(x, pad.top);
        ctx.lineTo(x, h - pad.bottom);
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.stroke();
      }

      // Theoretical curve (teal)
      ctx.strokeStyle = 'rgba(78,205,196,0.7)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      let first = true;
      for (const d of dpHistory) {
        const x = pad.left + d.p * plotW;
        const yLog = d.dpTheory > 0 ? Math.log10(d.dpTheory) / logMax : 0;
        const y = h - pad.bottom - yLog * plotH;
        if (first) { ctx.moveTo(x, y); first = false; }
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Actual curve (copper)
      ctx.strokeStyle = 'rgba(217,119,66,0.8)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      first = true;
      for (const d of dpHistory) {
        const x = pad.left + d.p * plotW;
        const yLog = d.dpActual > 0 ? Math.log10(d.dpActual) / logMax : 0;
        const y = h - pad.bottom - yLog * plotH;
        if (first) { ctx.moveTo(x, y); first = false; }
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Axis labels
      ctx.fillStyle = 'rgba(255,255,255,0.3)';
      ctx.font = '6px sans-serif';
      ctx.fillText('p=0', pad.left, h - 2);
      ctx.fillText('p=1', w - pad.right - 8, h - 2);

      // Legend
      ctx.fillStyle = 'rgba(78,205,196,0.7)';
      ctx.fillRect(w - 48, 2, 6, 6);
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.font = '5px sans-serif';
      ctx.fillText('theory', w - 40, 7);
      ctx.fillStyle = 'rgba(217,119,66,0.8)';
      ctx.fillRect(w - 48, 10, 6, 6);
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.fillText('actual', w - 40, 15);

      // Current values
      const latest = dpHistory[dpHistory.length - 1];
      ctx.fillStyle = 'rgba(255,255,255,0.5)';
      ctx.font = '6px sans-serif';
      ctx.fillText(`p=${latest.p.toFixed(2)} DP=${latest.dpActual.toFixed(1)}`, pad.left, h - 5);
    });
  }

  // Bond callout event: temporarily override the title (chart stays)
  if (sim.calloutEvent) {
    document.getElementById('callout-title').textContent = sim.calloutEvent.title;
    renderer._scheduleCalloutClear();
    sim.calloutEvent = null;
  }

  renderer.draw(particles);
  ui.updateReadouts(stats);
  ui.updateStageBadges(stats);

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
  const initTotal = sim.params.monomerACount + sim.params.monomerBCount;
  ui.setInitTotal(initTotal);
  stats.time = sim.time;
  syncSize();
  renderer.draw(particles);
  ui.updateReadouts(stats);
  ui.updateStageBadges(stats);
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
const initTotal = sim.params.monomerACount + sim.params.monomerBCount;
ui.setInitTotal(initTotal);
stats.time = sim.time;
renderer.draw(particles);
ui.updateReadouts(stats);
