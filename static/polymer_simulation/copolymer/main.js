import { Simulation } from './simulation.js';
import { Renderer } from '../lib/renderer.js';
import { UI } from './ui.js';
import { THEME } from './theme.js';

const canvas = document.getElementById('sim-canvas');
const diagramCanvas = document.getElementById('diagram-canvas');
const diagramCtx = diagramCanvas.getContext('2d');
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

  if (sim.calloutEvent) {
    renderer.drawCallout(sim.calloutEvent.title, sim.calloutEvent.drawFn);
    renderer._scheduleCalloutClear();
    sim.calloutEvent = null;
  }

  const { particles, stats } = sim.getState();
  stats.time = sim.time;
  renderer.draw(particles);
  ui.updateReadouts(stats);
  drawDiagram(stats, sim.params);

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
  ui.updateReadouts(stats);
  drawDiagram(stats, sim.params);
});
ui.on('paramChange', (params) => {
  sim.setParams(params);
  const { stats } = sim.getState();
  stats.time = sim.time;
  drawDiagram(stats, sim.params);
});
ui.on('speedChange', (speed) => {
  sim.setParams({ speedMultiplier: speed });
});

syncSize();
sim.reset();
const { particles, stats } = sim.getState();
stats.time = sim.time;
renderer.draw(particles);
ui.updateReadouts(stats);
drawDiagram(stats, sim.params);

function drawDiagram(stats, params) {
  const ctx = diagramCtx;
  const W = diagramCanvas.width;
  const H = diagramCanvas.height;
  const pad = { l: 36, r: 10, t: 16, b: 28 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = '#0d1b2a';
  ctx.fillRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = 'rgba(255,255,255,0.07)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const x = pad.l + (i / 4) * plotW;
    const y = pad.t + (i / 4) * plotH;
    ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
  }

  // Mayo-Lewis curve
  const r1 = params.r1;
  const r2 = params.r2;
  ctx.beginPath();
  ctx.strokeStyle = '#ff9f43';
  ctx.lineWidth = 2;
  for (let i = 0; i <= 200; i++) {
    const f1 = i / 200;
    const f2 = 1 - f1;
    const denom = r1 * f1 * f1 + 2 * f1 * f2 + r2 * f2 * f2;
    const F1 = denom > 0 ? (r1 * f1 * f1 + f1 * f2) / denom : 0;
    const px = pad.l + f1 * plotW;
    const py = pad.t + (1 - F1) * plotH;
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.stroke();

  // Diagonal (ideal, r1=r2=1)
  ctx.beginPath();
  ctx.strokeStyle = 'rgba(255,255,255,0.25)';
  ctx.setLineDash([3, 3]);
  ctx.lineWidth = 1;
  ctx.moveTo(pad.l, H - pad.b);
  ctx.lineTo(W - pad.r, pad.t);
  ctx.stroke();
  ctx.setLineDash([]);

  // Current feed f1
  const freeA = stats.freeMonomerA;
  const freeB = stats.freeMonomerB;
  const total = freeA + freeB;
  const f1_feed = total > 0 ? freeA / total : params.monomerACount / (params.monomerACount + params.monomerBCount);
  const F1_inst = stats.instantaneousF1;

  const px = pad.l + f1_feed * plotW;
  const py = pad.t + (1 - F1_inst) * plotH;

  // Crosshair
  ctx.strokeStyle = 'rgba(77,166,255,0.3)';
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 2]);
  ctx.beginPath(); ctx.moveTo(px, pad.t); ctx.lineTo(px, H - pad.b); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(pad.l, py); ctx.lineTo(W - pad.r, py); ctx.stroke();
  ctx.setLineDash([]);

  // Point
  const r = Math.max(4, Math.min(7, 4 + stats.conversion / 50));
  ctx.beginPath();
  ctx.arc(px, py, r, 0, Math.PI * 2);
  ctx.fillStyle = '#4da6ff';
  ctx.fill();
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Axes labels
  ctx.fillStyle = 'rgba(255,255,255,0.5)';
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('f1 (feed)', pad.l + plotW / 2, H - 4);
  ctx.save();
  ctx.translate(10, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('F1 (copolymer)', 0, 0);
  ctx.restore();

  // Tick labels
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.font = '8px sans-serif';
  ctx.textAlign = 'center';
  for (let i = 0; i <= 4; i++) {
    const v = (i / 4).toFixed(1);
    ctx.fillText(v, pad.l + (i / 4) * plotW, H - pad.b + 10);
    ctx.textAlign = 'right';
    ctx.fillText(v, pad.l - 4, pad.t + (1 - i / 4) * plotH + 3);
    ctx.textAlign = 'center';
  }

  // r values annotation
  ctx.fillStyle = 'rgba(255,159,67,0.7)';
  ctx.font = '8px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(`r1=${r1.toFixed(2)}  r2=${r2.toFixed(2)}`, W - pad.r - 2, pad.t + 10);
}
