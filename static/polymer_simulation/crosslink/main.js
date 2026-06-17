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

// ── Crosslink bridge rendering ──

function drawCrosslinks(ctx, crosslinks, particles) {
  for (const link of crosslinks) {
    const chainA = particles.find(p =>
      (p.type === 'chainRadical' || p.type === 'deadChain') && p.chainId === link.aChainId);
    const chainB = particles.find(p =>
      (p.type === 'chainRadical' || p.type === 'deadChain') && p.chainId === link.bChainId);
    if (!chainA || !chainB) continue;
    const segA = chainA.segments[link.aSegIdx];
    const segB = chainB.segments[link.bSegIdx];
    if (!segA || !segB) continue;

    const dist = Math.hypot(segB.x - segA.x, segB.y - segA.y);

    ctx.save();

    // Outer glow
    ctx.strokeStyle = 'rgba(255, 51, 136, 0.3)';
    ctx.lineWidth = 6;
    ctx.shadowColor = 'rgba(255, 51, 136, 0.9)';
    ctx.shadowBlur = 14;
    ctx.beginPath();
    ctx.moveTo(segA.x, segA.y);
    ctx.lineTo(segB.x, segB.y);
    ctx.stroke();

    // Bright core line
    const grad = ctx.createLinearGradient(segA.x, segA.y, segB.x, segB.y);
    grad.addColorStop(0, 'rgba(255, 51, 136, 0.6)');
    grad.addColorStop(0.5, 'rgba(255, 100, 180, 1.0)');
    grad.addColorStop(1, 'rgba(255, 51, 136, 0.6)');

    ctx.strokeStyle = grad;
    ctx.lineWidth = 3;
    ctx.shadowColor = 'rgba(255, 51, 136, 0.7)';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    ctx.moveTo(segA.x, segA.y);
    ctx.lineTo(segB.x, segB.y);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Endpoint markers on crosslinked AA — pulsing hot pink
    ctx.fillStyle = '#ff4499';
    ctx.shadowColor = 'rgba(255, 51, 136, 0.9)';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    ctx.arc(segA.x, segA.y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(segB.x, segB.y, 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }
}

// ── Highlight crosslinked AA segments so they're visible ──

function drawCrosslinkedSegments(ctx, particles) {
  ctx.save();
  for (const p of particles) {
    if ((p.type !== 'chainRadical' && p.type !== 'deadChain') || !p.segments) continue;
    for (const seg of p.segments) {
      if (!seg.isCrosslinked) continue;
      // Glow
      const grad = ctx.createRadialGradient(seg.x, seg.y, 0, seg.x, seg.y, 7);
      grad.addColorStop(0, 'rgba(255, 51, 136, 0.9)');
      grad.addColorStop(0.4, 'rgba(255, 51, 136, 0.4)');
      grad.addColorStop(1, 'rgba(255, 51, 136, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(seg.x, seg.y, 7, 0, Math.PI * 2);
      ctx.fill();

      // Solid core
      ctx.fillStyle = '#ff4499';
      ctx.beginPath();
      ctx.arc(seg.x, seg.y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.restore();
}

// ── Crosslink density vs conversion diagram ──

function drawDiagram(stats, sim) {
  const ctx = diagramCtx;
  const w = diagramCanvas.width;
  const h = diagramCanvas.height;
  const padL = 28, padR = 10, padT = 18, padB = 22;
  const chartW = w - padL - padR;
  const chartH = h - padT - padB;
  if (chartW <= 0 || chartH <= 0) return;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#0d1b2a';
  ctx.fillRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = 'rgba(255,255,255,0.06)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const x = padL + (i / 4) * chartW;
    ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, h - padB); ctx.stroke();
    const y = padT + (i / 4) * chartH;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
  }

  // Axes
  ctx.strokeStyle = 'rgba(255,255,255,0.25)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT); ctx.lineTo(padL, h - padB); ctx.lineTo(w - padR, h - padB);
  ctx.stroke();

  // Axis labels
  ctx.fillStyle = 'rgba(200,200,220,0.6)';
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Conversion (%)', padL + chartW / 2, h - 2);
  ctx.save();
  ctx.translate(8, padT + chartH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('XL Density (%)', 0, 0);
  ctx.restore();

  // Y-axis ticks
  ctx.fillStyle = 'rgba(200,200,220,0.5)';
  ctx.textAlign = 'right';
  const maxDensity = Math.max(10, Math.ceil((stats.crosslinkDensity || 5) / 10) * 10);
  for (let d = 0; d <= maxDensity; d += Math.max(5, Math.floor(maxDensity / 4))) {
    const y = padT + chartH * (1 - d / maxDensity);
    ctx.fillText(d + '%', padL - 4, y + 3);
  }

  // Plot XL density history
  const xlHistory = sim.getXLHistory();
  if (xlHistory.length >= 2) {
    // Curve: crosslink density vs conversion
    ctx.strokeStyle = '#ff4499';
    ctx.lineWidth = 2;
    ctx.shadowColor = 'rgba(255, 68, 153, 0.5)';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    for (let i = 0; i < xlHistory.length; i++) {
      const p = xlHistory[i];
      const x = padL + (p.conversion / 100) * chartW;
      const y = padT + chartH * (1 - p.density / maxDensity);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Current point
    const last = xlHistory[xlHistory.length - 1];
    const lx = padL + (last.conversion / 100) * chartW;
    const ly = padT + chartH * (1 - last.density / maxDensity);
    ctx.fillStyle = '#ff4499';
    ctx.beginPath();
    ctx.arc(lx, ly, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }

  // Gel point marker (horizontal dashed line at gelation density)
  if (stats.gelPointReached) {
    const gelDensity = xlHistory.length > 0
      ? xlHistory[xlHistory.length - 1].density
      : 5;
    const gelY = padT + chartH * (1 - gelDensity / maxDensity);
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(padL, gelY);
    ctx.lineTo(w - padR, gelY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#fff';
    ctx.font = '8px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('GEL', w - padR - 22, gelY - 4);
  }

  // Current values annotation
  ctx.fillStyle = 'rgba(255,255,255,0.7)';
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(`p=${stats.conversion}%  XL=${stats.crosslinkDensity.toFixed(1)}%`, padL + 2, padT - 4);
}

// ── Lab journal ──

function renderLabJournal(sim) {
  const listEl = document.getElementById('lab-journal-list');
  if (!listEl) return;
  const log = sim.getEventLog();
  if (!log || log.length === 0) {
    listEl.innerHTML = '<li class="empty">waiting for events…</li>';
    return;
  }
  const html = [];
  for (let i = log.length - 1; i >= Math.max(0, log.length - 6); i--) {
    const ev = log[i];
    const time = ev.t.toFixed(2) + 's';
    html.push(`<li><span class="ev-time">${time}</span><span class="ev-${ev.kind}">${ev.text}</span></li>`);
  }
  listEl.innerHTML = html.join('');
}

// ── Main loop ──

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

  const { particles, stats, crosslinks } = sim.getState();
  stats.time = sim.time;

  renderer.draw(particles);
  drawCrosslinkedSegments(renderer.ctx, particles);
  drawCrosslinks(renderer.ctx, crosslinks, particles);
  drawDiagram(stats, sim);
  renderLabJournal(sim);
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
  const { particles, stats, crosslinks } = sim.getState();
  stats.time = sim.time;
  syncSize();
  renderer.draw(particles);
  drawCrosslinkedSegments(renderer.ctx, particles);
  drawCrosslinks(renderer.ctx, crosslinks, particles);
  drawDiagram(stats, sim);
  renderLabJournal(sim);
  ui.updateReadouts(stats);
  ui.updateStageBadges(stats);
});

ui.on('paramChange', (params) => sim.setParams(params));
ui.on('speedChange', (speed) => sim.setParams({ speedMultiplier: speed }));

syncSize();
sim.reset();
const { particles, stats, crosslinks } = sim.getState();
stats.time = sim.time;
renderer.draw(particles);
drawCrosslinkedSegments(renderer.ctx, particles);
drawCrosslinks(renderer.ctx, crosslinks, particles);
drawDiagram(stats, sim);
renderLabJournal(sim);
ui.updateReadouts(stats);
