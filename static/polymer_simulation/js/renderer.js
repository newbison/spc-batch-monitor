// DEPRECATED: use lib/renderer.js instead. This file kept for backward compat with js/bundle.js.
const COLORS = {
  initiator: '#ffd93d',
  primaryRadical: '#ff6b6b',
  monomer: '#777',
  chainRadical: '#4ecdc4',
  deadChain: '#555',
  bond: 'rgba(255,255,255,0.3)',
  bg: '#0f0f23',
};

const RADII = {
  initiator: 7,
  primaryRadical: 4,
  monomer: 5,
  chainRadical: 6,
  deadChain: 5,
};

const GLOW_COLORS = {
  primaryRadical: 'rgba(255,107,107,0.6)',
  chainRadical: 'rgba(78,205,196,0.6)',
};

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.resize();
    this._resizeHandler = () => this.resize();
    window.addEventListener('resize', this._resizeHandler);
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * devicePixelRatio;
    this.canvas.height = rect.height * devicePixelRatio;
    this.ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    this.w = rect.width;
    this.h = rect.height;
  }

  draw(particles) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);

    // Background
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, this.w, this.h);

    // Subtle grid
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 1;
    const gridSize = 40;
    for (let x = 0; x < this.w; x += gridSize) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.h); ctx.stroke();
    }
    for (let y = 0; y < this.h; y += gridSize) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(this.w, y); ctx.stroke();
    }

    // Draw bonds between chain segments
    for (const p of particles) {
      if ((p.type === 'chainRadical' || p.type === 'deadChain') && p.segments?.length > 1) {
        for (let i = 0; i < p.segments.length - 1; i++) {
          const a = p.segments[i];
          const b = p.segments[i + 1];
          const alpha = p.type === 'chainRadical' ? 0.4 : 0.2;
          ctx.strokeStyle = p.type === 'chainRadical'
            ? `rgba(78,205,196,${alpha})`
            : `rgba(150,150,150,${alpha})`;
          ctx.lineWidth = p.type === 'chainRadical' ? 2.5 : 1.5;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    // Draw particles
    for (const p of particles) {
      const pos = p.type === 'chainRadical' || p.type === 'deadChain'
        ? p.segments[p.segments.length - 1]  // draw head
        : p;

      // Glow for radicals
      if (p.type === 'primaryRadical' || p.type === 'chainRadical') {
        const glowColor = p.type === 'primaryRadical'
          ? GLOW_COLORS.primaryRadical
          : GLOW_COLORS.chainRadical;
        const grad = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, RADII[p.type] * 3);
        grad.addColorStop(0, glowColor);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, RADII[p.type] * 3, 0, Math.PI * 2);
        ctx.fill();
      }

      // Body
      ctx.fillStyle = COLORS[p.type];
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, RADII[p.type], 0, Math.PI * 2);
      ctx.fill();

      // Draw chain body segments
      if ((p.type === 'chainRadical' || p.type === 'deadChain') && p.segments?.length > 1) {
        for (let i = 0; i < p.segments.length - 1; i++) {
          const seg = p.segments[i];
          const color = p.type === 'chainRadical' ? COLORS.chainRadical : COLORS.deadChain;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(seg.x, seg.y, 3, 0, Math.PI * 2);
          ctx.fill();
        }
        // Head with distinct color
        const head = p.segments[p.segments.length - 1];
        ctx.fillStyle = p.type === 'chainRadical' ? COLORS.chainRadical : COLORS.deadChain;
        ctx.beginPath();
        ctx.arc(head.x, head.y, RADII[p.type], 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  drawCallout(event) {
    const calloutEl = document.getElementById('callout');
    const titleEl = document.getElementById('callout-title');
    const calloutCanvas = document.getElementById('callout-canvas');
    const ctx = calloutCanvas.getContext('2d');

    if (!event) {
      calloutEl.classList.add('hidden');
      return;
    }

    calloutEl.classList.remove('hidden');
    ctx.clearRect(0, 0, calloutCanvas.width, calloutCanvas.height);

    const w = calloutCanvas.width;
    const h = calloutCanvas.height;

    if (event.type === 'initiation') {
      titleEl.textContent = 'Initiation: I₂ → 2 I•';
      const cx = w / 2, cy = h / 2;
      ctx.fillStyle = 'rgba(255,217,61,0.4)';
      ctx.beginPath(); ctx.arc(cx - 8, cy, 7, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(cx + 8, cy, 7, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(cx - 8, cy); ctx.lineTo(cx + 8, cy); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#ff6b6b';
      ctx.beginPath(); ctx.arc(cx - 22, cy, 5, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(cx + 22, cy, 5, 0, Math.PI * 2); ctx.fill();
      [cx - 22, cx + 22].forEach(rx => {
        const grad = ctx.createRadialGradient(rx, cy, 0, rx, cy, 10);
        grad.addColorStop(0, 'rgba(255,107,107,0.5)'); grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(rx, cy, 10, 0, Math.PI * 2); ctx.fill();
      });
      ctx.fillStyle = '#fff';
      ctx.font = '12px sans-serif';
      ctx.fillText('→', cx - 4, cy + 20);
    }

    if (event.type === 'propagation' || event.type === 'firstPropagation') {
      titleEl.textContent = event.type === 'firstPropagation'
        ? 'Initiation: R• + M → RM•'
        : `Propagation: chain + M (n=${event.chainLen || '?'})`;
      const cx = w / 2, cy = h / 2;
      ctx.fillStyle = '#777';
      ctx.beginPath(); ctx.arc(cx + 25, cy, 8, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#aaa'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(cx + 25, cy, 8, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = '#4ecdc4';
      ctx.beginPath(); ctx.arc(cx - 15, cy, 7, 0, Math.PI * 2); ctx.fill();
      const grad = ctx.createRadialGradient(cx - 15, cy, 0, cx - 15, cy, 12);
      grad.addColorStop(0, 'rgba(78,205,196,0.5)'); grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(cx - 15, cy, 12, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.font = '16px sans-serif';
      ctx.fillText('→', cx + 2, cy + 5);
      ctx.fillStyle = '#4ecdc4';
      ctx.beginPath(); ctx.arc(cx + 50, cy, 8, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#4ecdc4'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(cx + 50, cy - 8); ctx.lineTo(cx + 50, cy + 8); ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = '9px sans-serif';
      ctx.fillText('n+1', cx + 42, cy - 12);
    }

    if (event.type === 'termination') {
      titleEl.textContent = 'Termination';
      const cx = w / 2, cy = h / 2;
      ctx.fillStyle = '#4ecdc4';
      ctx.beginPath(); ctx.arc(cx - 20, cy - 5, 7, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(cx + 20, cy + 5, 7, 0, Math.PI * 2); ctx.fill();
      [cx - 20, cx + 20].forEach((rx, i) => {
        const grad = ctx.createRadialGradient(rx, cy - 5 + i * 10, 0, rx, cy - 5 + i * 10, 10);
        grad.addColorStop(0, 'rgba(78,205,196,0.5)'); grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(rx, cy - 5 + i * 10, 10, 0, Math.PI * 2); ctx.fill();
      });
      ctx.strokeStyle = '#ff6b6b';
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(cx + 5, cy - 15); ctx.lineTo(cx + 15, cy - 5); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cx + 15, cy - 15); ctx.lineTo(cx + 5, cy - 5); ctx.stroke();
      ctx.fillStyle = '#555';
      ctx.beginPath(); ctx.arc(cx + 45, cy, 8, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.font = '9px sans-serif';
      ctx.fillText('dead', cx + 35, cy - 14);
    }
  }

  _scheduleCalloutClear() {
    if (this._calloutTimer) clearTimeout(this._calloutTimer);
    this._calloutTimer = setTimeout(() => {
      document.getElementById('callout').classList.add('hidden');
    }, 2500);
  }

  dispose() {
    window.removeEventListener('resize', this._resizeHandler);
  }
}
