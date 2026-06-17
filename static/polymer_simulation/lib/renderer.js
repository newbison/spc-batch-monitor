export class Renderer {
  constructor(canvas, theme) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.theme = theme;
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
    const { colors, radii, glowColors, bgColor } = this.theme;
    ctx.clearRect(0, 0, this.w, this.h);

    // Background
    ctx.fillStyle = bgColor || colors.bg || '#0f0f23';
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
      if ((p.type === 'chainRadical' || p.type === 'deadChain' || p.type === 'oligomer') && p.segments?.length > 1) {
        for (let i = 0; i < p.segments.length - 1; i++) {
          const a = p.segments[i];
          const b = p.segments[i + 1];
          let alpha = 0.3;
          let bondLineColor = '#666';
          let bondWidth = 1.5;
          if (p.type === 'chainRadical') { alpha = 0.4; bondLineColor = colors.chainRadical || '#4ecdc4'; bondWidth = 2.5; }
          else if (p.type === 'oligomer') { alpha = 0.35; bondLineColor = colors.oligomer || '#6abf69'; bondWidth = 2; }
          else { alpha = 0.2; bondLineColor = colors.deadChain || '#555'; bondWidth = 1.5; }
          ctx.strokeStyle = `rgba(${this._hexToRgb(bondLineColor)},${alpha})`;
          ctx.lineWidth = bondWidth;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    // Draw particles
    for (const p of particles) {
      const pos = p.type === 'chainRadical' || p.type === 'deadChain' || p.type === 'oligomer'
        ? p.segments[p.segments.length - 1]
        : p;

      // Glow for particles with a defined glowColor
      if (glowColors && glowColors[p.type]) {
        const glowColor = glowColors[p.type];
        const r = radii?.[p.type] ?? 5;
        const grad = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, r * 3);
        grad.addColorStop(0, glowColor);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r * 3, 0, Math.PI * 2);
        ctx.fill();
      }

      // Body
      const r = radii?.[p.type] ?? 5;
      const color = this._colorForParticle(p, colors);
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
      ctx.fill();

      // Draw chain body segments
      if ((p.type === 'chainRadical' || p.type === 'deadChain' || p.type === 'oligomer') && p.segments?.length > 1) {
        for (let i = 0; i < p.segments.length - 1; i++) {
          const seg = p.segments[i];
          const segColor = this._segmentColor(p, seg, i, colors);
          ctx.fillStyle = segColor;
          ctx.beginPath();
          ctx.arc(seg.x, seg.y, 3, 0, Math.PI * 2);
          ctx.fill();
        }
        // Head
        const head = p.segments[p.segments.length - 1];
        const headColor = this._segmentColor(p, head, p.segments.length - 1, colors);
        ctx.fillStyle = headColor;
        ctx.beginPath();
        ctx.arc(head.x, head.y, radii?.[p.type] ?? 6, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  _colorForParticle(p, colors) {
    if ((p.type === 'chainRadical' || p.type === 'deadChain' || p.type === 'oligomer') && p.segments?.length) {
      const head = p.segments[p.segments.length - 1];
      if (this.theme.segmentColor && head.monomerType !== undefined) {
        return this.theme.segmentColor(head.monomerType, p.type, head);
      }
    }
    return colors[p.type] || '#fff';
  }

  _segmentColor(p, seg, idx, colors) {
    if (this.theme.segmentColor && seg.monomerType !== undefined) {
      return this.theme.segmentColor(seg.monomerType, p.type, seg);
    }
    return colors[p.type] || '#fff';
  }

  _hexToRgb(hex) {
    if (hex.startsWith('#')) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `${r},${g},${b}`;
    }
    return '255,255,255';
  }

  drawCallout(title, drawFn) {
    const calloutEl = document.getElementById('callout');
    const titleEl = document.getElementById('callout-title');
    const calloutCanvas = document.getElementById('callout-canvas');
    const ctx = calloutCanvas.getContext('2d');

    if (!drawFn) {
      calloutEl.classList.add('hidden');
      return;
    }

    calloutEl.classList.remove('hidden');
    ctx.clearRect(0, 0, calloutCanvas.width, calloutCanvas.height);

    if (title) {
      titleEl.textContent = title;
    }

    drawFn(ctx, calloutCanvas.width, calloutCanvas.height);
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
