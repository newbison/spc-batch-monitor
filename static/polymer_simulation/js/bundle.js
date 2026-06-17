class Renderer {
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

      // Glow for radicals
      if (glowColors && (p.type === 'primaryRadical' || p.type === 'chainRadical')) {
        const glowColor = p.type === 'primaryRadical'
          ? (glowColors.primaryRadical || 'rgba(255,107,107,0.6)')
          : (glowColors.chainRadical || 'rgba(78,205,196,0.6)');
        const r = radii?.[p.type] ?? (p.type === 'primaryRadical' ? 4 : 6);
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
        return this.theme.segmentColor(head.monomerType, p.type);
      }
    }
    return colors[p.type] || '#fff';
  }

  _segmentColor(p, seg, idx, colors) {
    if (this.theme.segmentColor && seg.monomerType !== undefined) {
      return this.theme.segmentColor(seg.monomerType, p.type);
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
class UIBase {
  constructor() {
    this._callbacks = {};
  }

  on(event, fn) {
    this._callbacks[event] = fn;
  }

  _cb(event, data) {
    if (this._callbacks[event]) this._callbacks[event](data);
  }

  // Bind a button element to a callback event
  bindButton(id, event) {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('click', () => this._cb(event));
    }
  }

  // Bind a slider: sets up display value update and param-change callback
  // onChange receives the parsed slider value
  bindSlider(id, valueId, format, paramKey, onChange) {
    const slider = document.getElementById(id);
    const display = document.getElementById(valueId);
    if (!slider) return;

    slider.addEventListener('input', () => {
      const val = parseFloat(slider.value);
      if (display) {
        display.textContent = typeof format === 'function' ? format(val) : val + format;
      }
      if (onChange) {
        onChange(paramKey, val);
      }
      this._cb('paramChange', this._getParams());
    });
  }

  // Set initial display value for a slider
  setSliderValue(id, valueId, value, format) {
    const display = document.getElementById(valueId);
    if (display) {
      display.textContent = typeof format === 'function' ? format(value) : value + format;
    }
  }

  // Register a readout spec: { id, key, format }
  setReadoutSpec(specs) {
    this._readoutSpecs = specs;
  }

  updateReadouts(data) {
    if (!this._readoutSpecs) return;
    for (const spec of this._readoutSpecs) {
      const el = document.getElementById(spec.id);
      if (!el) continue;
      const val = data[spec.key];
      if (val === undefined || val === null) {
        el.textContent = '—';
      } else if (spec.format) {
        el.textContent = typeof spec.format === 'function' ? spec.format(val) : val;
      } else {
        el.textContent = String(val);
      }
    }
  }

  // Badge toggling
  setBadge(id, active) {
    const el = document.getElementById(id);
    if (!el) return;
    if (active) {
      el.classList.add('active');
      el.textContent = el.textContent.replace('○', '●');
    } else {
      el.classList.remove('active');
      el.textContent = el.textContent.replace('●', '○');
    }
  }

  // Override in subclass to collect all param values
  _getParams() {
    return {};
  }
}
// DEPRECATED: use free-radical/simulation.js instead. This file kept for backward compat with js/bundle.js.
class Simulation {
  constructor() {
    this.particles = [];
    this.time = 0;
    this.params = {
      initiatorCount: 10,
      monomerCount: 1000,
      rateMultiplier: 5.0,
      speedMultiplier: 5.0,
    };
    this.stats = {
      conversion: 0,
      mn: 0,
      activeChains: 0,
      deadChains: 0,
      freeMonomers: 0,
    };
    this.calloutEvent = null;  // { type, data } for the current frame
    this._canvasW = 800;
    this._canvasH = 500;
  }

  setCanvasSize(w, h) {
    this._canvasW = w;
    this._canvasH = h;
  }

  setParams(p) {
    Object.assign(this.params, p);
  }

  reset() {
    this.particles = [];
    this.time = 0;
    this.calloutEvent = null;
    this._initParticles();
  }

  _initParticles() {
    const { initiatorCount, monomerCount } = this.params;
    this.particles = [];
    const minDist = 15;

    const tooClose = (x, y, existing) => {
      for (const p of existing) {
        const px = p.type === 'chainRadical' || p.type === 'deadChain'
          ? p.segments[p.segments.length - 1].x : p.x;
        const py = p.type === 'chainRadical' || p.type === 'deadChain'
          ? p.segments[p.segments.length - 1].y : p.y;
        if (Math.hypot(x - px, y - py) < minDist) return true;
      }
      return false;
    };

    for (let i = 0; i < initiatorCount; i++) {
      let x, y, attempts = 0;
      do {
        x = 20 + Math.random() * (this._canvasW - 40);
        y = 20 + Math.random() * (this._canvasH - 40);
        attempts++;
      } while (tooClose(x, y, this.particles) && attempts < 50);

      this.particles.push({
        type: 'initiator', x, y,
        vx: (Math.random() - 0.5) * 1.5,
        vy: (Math.random() - 0.5) * 1.5,
        radius: 7,
      });
    }

    for (let i = 0; i < monomerCount; i++) {
      let x, y, attempts = 0;
      do {
        x = Math.random() * this._canvasW;
        y = Math.random() * this._canvasH;
        attempts++;
      } while (tooClose(x, y, this.particles) && attempts < 100);

      this.particles.push({
        type: 'monomer', x, y,
        vx: (Math.random() - 0.5) * 1.0,
        vy: (Math.random() - 0.5) * 1.0,
        radius: 5,
        consumed: false,
      });
    }

    this._updateStats();
  }

  _processInitiation(dt) {
    const rate = this.params.rateMultiplier;
    const kd = 25.0 * rate; // initiator decomposition probability per second

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      if (p.type !== 'initiator') continue;

      // Probability of decomposition this frame
      if (Math.random() < kd * dt) {
        this._decomposeInitiator(i);
      }
    }
  }

  _decomposeInitiator(idx) {
    const initiator = this.particles[idx];
    const x = initiator.x;
    const y = initiator.y;

    // Remove initiator, add 2 primary radicals
    this.particles.splice(idx, 1);

    for (let i = 0; i < 2; i++) {
      this.particles.push({
        type: 'primaryRadical',
        x: x + (Math.random() - 0.5) * 6,
        y: y + (Math.random() - 0.5) * 6,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        radius: 4,
      });
    }

    this.calloutEvent = { type: 'initiation', time: this.time };
  }

  _processRadicalCapture(dt) {
    const rate = this.params.rateMultiplier;
    const captureDist = 20; // pixels, generous for visual clarity
    const kCapture = 12.5 * rate; // high probability — diffusion-limited

    const primaryRadicals = [];
    const monomers = [];

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      if (p.type === 'primaryRadical') primaryRadicals.push(i);
      else if (p.type === 'monomer' && !p.consumed) monomers.push(i);
    }

    for (const ri of primaryRadicals) {
      const radical = this.particles[ri];
      for (const mi of monomers) {
        const monomer = this.particles[mi];
        if (monomer.consumed) continue;

        const dx = radical.x - monomer.x;
        const dy = radical.y - monomer.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < captureDist && Math.random() < kCapture * dt) {
          // Convert to chain radical of length 1
          monomer.consumed = true;
          this.particles[ri] = {
            type: 'chainRadical',
            segments: [
              { x: monomer.x, y: monomer.y },
              { x: radical.x, y: radical.y },
            ],
            vx: (Math.random() - 0.5) * 1.5,
            vy: (Math.random() - 0.5) * 1.5,
            radius: 6,
          };
          this.calloutEvent = { type: 'firstPropagation', time: this.time };
          break; // each radical captures one monomer per frame
        }
      }
    }
  }

  _processPropagation(dt) {
    const rate = this.params.rateMultiplier;
    const kp = 12.5 * rate; // propagation probability
    const reactDist = 18;

    const chainRadicals = [];
    const monomers = [];

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      if (p.type === 'chainRadical') chainRadicals.push(i);
      else if (p.type === 'monomer' && !p.consumed) monomers.push(i);
    }

    for (const ci of chainRadicals) {
      const chain = this.particles[ci];
      const head = chain.segments[chain.segments.length - 1];

      for (const mi of monomers) {
        const monomer = this.particles[mi];
        if (monomer.consumed) continue;

        const dx = head.x - monomer.x;
        const dy = head.y - monomer.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < reactDist && Math.random() < kp * dt) {
          monomer.consumed = true;
          // Add monomer position as new head
          chain.segments.push({ x: monomer.x, y: monomer.y });
          const mob = this._chainMobility(chain.segments.length);
          chain.vx += (Math.random() - 0.5) * 0.5 * mob;
          chain.vy += (Math.random() - 0.5) * 0.5 * mob;
          this.calloutEvent = { type: 'propagation', time: this.time, chainLen: chain.segments.length };
          break; // one propagation per chain per frame
        }
      }
    }
  }

  _processTermination(dt) {
    const rate = this.params.rateMultiplier;
    const kt = 3.75 * rate;
    const termDist = 16;

    const chainRadicals = [];
    for (let i = 0; i < this.particles.length; i++) {
      if (this.particles[i].type === 'chainRadical') chainRadicals.push(i);
    }

    const terminated = new Set();

    for (let i = 0; i < chainRadicals.length; i++) {
      const ai = chainRadicals[i];
      if (terminated.has(ai)) continue;
      const chainA = this.particles[ai];

      for (let j = i + 1; j < chainRadicals.length; j++) {
        const bi = chainRadicals[j];
        if (terminated.has(bi)) continue;
        const chainB = this.particles[bi];

        const headA = chainA.segments[chainA.segments.length - 1];
        const headB = chainB.segments[chainB.segments.length - 1];
        const dx = headA.x - headB.x;
        const dy = headA.y - headB.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < termDist && Math.random() < kt * dt) {
          terminated.add(ai);
          terminated.add(bi);

          // 50% combination, 50% disproportionation
          if (Math.random() < 0.5) {
            // Combination: join chains into one dead chain
            const combinedSegments = [
              ...chainA.segments,
              ...chainB.segments.slice().reverse(),
            ];
            this.particles.push({
              type: 'deadChain',
              segments: combinedSegments,
              vx: (chainA.vx + chainB.vx) / 2,
              vy: (chainA.vy + chainB.vy) / 2,
              radius: 5,
            });
          } else {
            // Disproportionation: both become dead chains
            this.particles.push({
              type: 'deadChain',
              segments: [...chainA.segments],
              vx: chainA.vx * 0.5,
              vy: chainA.vy * 0.5,
              radius: 5,
            });
            this.particles.push({
              type: 'deadChain',
              segments: [...chainB.segments],
              vx: chainB.vx * 0.5,
              vy: chainB.vy * 0.5,
              radius: 5,
            });
          }

          this.calloutEvent = { type: 'termination', time: this.time };
          break; // one termination pair per frame check
        }
      }
    }

    // Remove terminated chain radicals (highest indices first)
    const toRemove = [...terminated].sort((a, b) => b - a);
    for (const idx of toRemove) {
      this.particles.splice(idx, 1);
    }
  }

  _updateStats() {
    const totalMonomerInit = this.params.monomerCount;
    const free = this.particles.filter(p => p.type === 'monomer' && !p.consumed).length;
    const consumed = totalMonomerInit - free;
    const activeChains = this.particles.filter(p => p.type === 'chainRadical').length;
    const deadChains = this.particles.filter(p => p.type === 'deadChain').length;

    this.stats = {
      conversion: totalMonomerInit > 0 ? Math.round((consumed / totalMonomerInit) * 100) : 0,
      mn: deadChains > 0 ? Math.round(consumed / deadChains) : 0,
      activeChains,
      deadChains,
      freeMonomers: free,
    };
  }

  tick(dt) {
    const speed = this.params.speedMultiplier;
    const scaledDt = dt * speed;

    this.time += scaledDt;
    this._moveParticles(scaledDt);
    this._processInitiation(scaledDt);
    this._processRadicalCapture(scaledDt);
    this._processPropagation(scaledDt);
    this._processTermination(scaledDt);
    // Remove consumed monomers from display
    this.particles = this.particles.filter(p => !(p.type === 'monomer' && p.consumed));
    this._updateStats();
  }

  _chainMobility(chainLength) {
    return 1 / Math.sqrt(1 + (chainLength - 1) * 0.3);
  }

  _moveParticles(dt) {
    const w = this._canvasW;
    const h = this._canvasH;

    for (const p of this.particles) {
      if (p.type === 'monomer' && p.consumed) continue;

      const mobility = (p.type === 'chainRadical' || p.type === 'deadChain')
        ? this._chainMobility(p.segments.length)
        : 1;

      // Brownian perturbation — scaled by mobility
      p.vx += (Math.random() - 0.5) * 0.5 * Math.sqrt(mobility);
      p.vy += (Math.random() - 0.5) * 0.5 * Math.sqrt(mobility);

      // Damping
      p.vx *= 0.98;
      p.vy *= 0.98;

      // Speed cap — scaled by mobility
      const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
      const maxSpeed = 3 * mobility;
      if (speed > maxSpeed) {
        p.vx = (p.vx / speed) * maxSpeed;
        p.vy = (p.vy / speed) * maxSpeed;
      }

      if (p.type === 'chainRadical' || p.type === 'deadChain') {
        if (!p.segments || p.segments.length === 0) continue;
        const head = p.segments[p.segments.length - 1];
        head.x += p.vx * dt * 60;
        head.y += p.vy * dt * 60;

        // Bounce head off walls
        if (head.x < 5) { head.x = 5; p.vx *= -0.5; }
        if (head.x > w - 5) { head.x = w - 5; p.vx *= -0.5; }
        if (head.y < 5) { head.y = 5; p.vy *= -0.5; }
        if (head.y > h - 5) { head.y = h - 5; p.vy *= -0.5; }

        // Body follows leader with lag
        for (let i = 0; i < p.segments.length - 1; i++) {
          const seg = p.segments[i];
          const leader = p.segments[i + 1];
          const dx = leader.x - seg.x;
          const dy = leader.y - seg.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const targetDist = 10;
          if (dist > targetDist) {
            const ratio = (dist - targetDist) / dist;
            seg.x += dx * ratio * 0.8;
            seg.y += dy * ratio * 0.8;
          }
        }
      } else {
        p.x += p.vx * dt * 60;
        p.y += p.vy * dt * 60;

        // Bounce off walls
        if (p.x < p.radius) { p.x = p.radius; p.vx *= -0.5; }
        if (p.x > w - p.radius) { p.x = w - p.radius; p.vx *= -0.5; }
        if (p.y < p.radius) { p.y = p.radius; p.vy *= -0.5; }
        if (p.y > h - p.radius) { p.y = h - p.radius; p.vy *= -0.5; }
      }
    }
  }

  getState() {
    return { particles: this.particles, stats: this.stats };
  }

  getStats() {
    return this.stats;
  }
}
// DEPRECATED: use free-radical/ui.js instead. This file kept for backward compat with js/bundle.js.
class UI {
  constructor() {
    this._callbacks = {};
    this._getElements();
    this._bindEvents();
  }

  _getElements() {
    this.btnPlay = document.getElementById('btn-play');
    this.btnPause = document.getElementById('btn-pause');
    this.btnReset = document.getElementById('btn-reset');
    this.sliderInitiator = document.getElementById('slider-initiator');
    this.sliderMonomer = document.getElementById('slider-monomer');
    this.sliderRate = document.getElementById('slider-rate');
    this.sliderSpeed = document.getElementById('slider-speed');
    this.badgeInit = document.getElementById('badge-initiation');
    this.badgeProp = document.getElementById('badge-propagation');
    this.badgeTerm = document.getElementById('badge-termination');
  }

  _bindEvents() {
    this.btnPlay.addEventListener('click', () => this._cb('play'));
    this.btnPause.addEventListener('click', () => this._cb('pause'));
    this.btnReset.addEventListener('click', () => this._cb('reset'));

    this.sliderInitiator.addEventListener('input', () => {
      document.getElementById('val-initiator').textContent = this.sliderInitiator.value;
      this._cb('paramChange', this._getParams());
    });
    this.sliderMonomer.addEventListener('input', () => {
      document.getElementById('val-monomer').textContent = this.sliderMonomer.value;
      this._cb('paramChange', this._getParams());
    });
    this.sliderRate.addEventListener('input', () => {
      document.getElementById('val-rate').textContent = parseFloat(this.sliderRate.value).toFixed(1) + '×';
      this._cb('paramChange', this._getParams());
    });
    this.sliderSpeed.addEventListener('input', () => {
      document.getElementById('val-speed').textContent = parseFloat(this.sliderSpeed.value) + '×';
      this._cb('speedChange', parseFloat(this.sliderSpeed.value));
    });
  }

  _getParams() {
    return {
      initiatorCount: parseInt(this.sliderInitiator.value),
      monomerCount: parseInt(this.sliderMonomer.value),
      rateMultiplier: parseFloat(this.sliderRate.value),
    };
  }

  on(event, fn) {
    this._callbacks[event] = fn;
  }

  _cb(event, data) {
    if (this._callbacks[event]) this._callbacks[event](data);
  }

  updateReadouts(stats) {
    document.getElementById('ro-time').textContent = stats.time.toFixed(1) + 's';
    document.getElementById('ro-conversion').textContent = stats.conversion + '%';
    document.getElementById('ro-mn').textContent = stats.mn || '—';
    document.getElementById('ro-chains').textContent = stats.activeChains;
    document.getElementById('ro-dead').textContent = stats.deadChains;
    document.getElementById('ro-monomers').textContent = stats.freeMonomers;
  }

  updateStageBadges(stats) {
    const hasActiveChains = stats.activeChains > 0;
    const hasDeadChains = stats.deadChains > 0;

    this._setBadge(this.badgeInit, !hasActiveChains && !hasDeadChains);
    this._setBadge(this.badgeProp, hasActiveChains && stats.conversion < 80);
    this._setBadge(this.badgeTerm, hasDeadChains > 0 || stats.conversion >= 80);
  }

  _setBadge(el, active) {
    if (active) {
      el.classList.add('active');
      el.textContent = el.textContent.replace('○', '●');
    } else {
      el.classList.remove('active');
      el.textContent = el.textContent.replace('●', '○');
    }
  }
}
// DEPRECATED: use free-radical/main.js instead. This file kept for backward compat with js/bundle.js.

const canvas = document.getElementById('sim-canvas');
const sim = new Simulation();
const renderer = new Renderer(canvas);
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

  // Handle callout event
  if (sim.calloutEvent) {
    renderer.drawCallout(sim.calloutEvent);
    renderer._scheduleCalloutClear();
    sim.calloutEvent = null;
  }

  const { particles, stats } = sim.getState();
  stats.time = sim.time;
  renderer.draw(particles);
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

// Wire UI callbacks
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
  ui.updateStageBadges({ ...stats, totalMonomers: sim.params.monomerCount });
  play();
});
ui.on('paramChange', (params) => {
  sim.setParams(params);
});
ui.on('speedChange', (speed) => {
  sim.setParams({ speedMultiplier: speed });
});

// Auto-start
syncSize();
sim.reset();
const { particles, stats } = sim.getState();
stats.time = sim.time;
renderer.draw(particles);
ui.updateReadouts(stats);
