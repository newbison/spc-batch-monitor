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
        el.textContent = '-';
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
      el.textContent = el.textContent.replace('o', '*');
    } else {
      el.classList.remove('active');
      el.textContent = el.textContent.replace('*', 'o');
    }
  }

  // Override in subclass to collect all param values
  _getParams() {
    return {};
  }
}

class Simulation {
  constructor() {
    this.particles = [];
    this.time = 0;
    this.params = {
      initiatorCount: 10,
      monomerACount: 950,
      monomerBCount: 50,
      r1: 0.35,
      r2: 2.5,
      crosslinkerAmount: 1,     // % relative to AA monomer count
      crosslinkRate: 0.5,
      rateMultiplier: 5.0,
      speedMultiplier: 10.0,
    };
    this.stats = {
      conversion: 0,
      mn: 0,
      mw: 0,
      pdi: 0,
      activeChains: 0,
      deadChains: 0,
      freeMonomerA: 0,
      freeMonomerB: 0,
      cumulativeF1: 0,
      instantaneousF1: 0,
      crosslinkDensity: 0,
      crosslinkedAA: 0,
      totalAAinChains: 0,
      networkChains: 0,
      gelPointReached: false,
    };
    this._monomerAAdded = 0;
    this._monomerBAdded = 0;
    this._recentAAdded = 0;
    this._recentBAdded = 0;
    this.calloutEvent = null;
    this._crosslinks = [];            // { aChainId, aSegIdx, bChainId, bSegIdx }
    this._nextChainId = 1;
    this._gelPointReached = false;
    this._canvasW = 800;
    this._canvasH = 500;
    this._eventLog = [];
    this._conversionHistory = [];
    this._xlDensityHistory = [];     // { t, density, conversion }
    this._lastSampleT = 0;
    this._sampleInterval = 0.1;
    this._maxHistoryPoints = 250;
  }

  setCanvasSize(w, h) {
    this._canvasW = w;
    this._canvasH = h;
  }

  setParams(p) {
    const needReset = ('initiatorCount' in p && p.initiatorCount !== this.params.initiatorCount) ||
                      ('monomerACount' in p && p.monomerACount !== this.params.monomerACount) ||
                      ('monomerBCount' in p && p.monomerBCount !== this.params.monomerBCount) ||
                      ('crosslinkerAmount' in p && p.crosslinkerAmount !== this.params.crosslinkerAmount);
    Object.assign(this.params, p);
    if (needReset) this.reset();
  }

  reset() {
    this.particles = [];
    this.time = 0;
    this.calloutEvent = null;
    this._monomerAAdded = 0;
    this._monomerBAdded = 0;
    this._recentAAdded = 0;
    this._recentBAdded = 0;
    this._crosslinks = [];
    this._nextChainId = 1;
    this._gelPointReached = false;
    this._eventLog = [];
    this._conversionHistory = [];
    this._xlDensityHistory = [];
    this._lastSampleT = 0;
    this._initParticles();
  }

  _initParticles() {
    const { initiatorCount, monomerACount, monomerBCount, crosslinkerAmount } = this.params;
    this._initMonomerACount = monomerACount;
    this._initMonomerBCount = monomerBCount;
    this.particles = [];
    const minDist = 15;

    const tooClose = (x, y, existing) => {
      for (const p of existing) {
        const px = (p.type === 'chainRadical' || p.type === 'deadChain')
          ? p.segments[p.segments.length - 1].x : p.x;
        const py = (p.type === 'chainRadical' || p.type === 'deadChain')
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

    for (let i = 0; i < monomerACount; i++) {
      let x, y, attempts = 0;
      do {
        x = Math.random() * this._canvasW;
        y = Math.random() * this._canvasH;
        attempts++;
      } while (tooClose(x, y, this.particles) && attempts < 100);
      this.particles.push({
        type: 'monomerA', x, y,
        vx: (Math.random() - 0.5) * 1.0,
        vy: (Math.random() - 0.5) * 1.0,
        radius: 5,
        consumed: false,
      });
    }

    for (let i = 0; i < monomerBCount; i++) {
      let x, y, attempts = 0;
      do {
        x = Math.random() * this._canvasW;
        y = Math.random() * this._canvasH;
        attempts++;
      } while (tooClose(x, y, this.particles) && attempts < 100);
      this.particles.push({
        type: 'monomerB', x, y,
        vx: (Math.random() - 0.5) * 1.0,
        vy: (Math.random() - 0.5) * 1.0,
        radius: 5,
        consumed: false,
      });
    }

    // Crosslinker particles: count = floor(AA_count * crosslinkerAmount / 100)
    const xlCount = Math.floor(monomerBCount * crosslinkerAmount / 100);
    for (let i = 0; i < xlCount; i++) {
      let x, y, attempts = 0;
      do {
        x = Math.random() * this._canvasW;
        y = Math.random() * this._canvasH;
        attempts++;
      } while (tooClose(x, y, this.particles) && attempts < 100);
      this.particles.push({
        type: 'crosslinker', x, y,
        vx: (Math.random() - 0.5) * 1.0,
        vy: (Math.random() - 0.5) * 1.0,
        radius: 5,
        consumed: false,
        attachedChainId: null,    // first AA attachment
        attachedSegIdx: null,
      });
    }

    this._pushEvent('init', `System: ${monomerACount} M₁ (2EHA) + ${monomerBCount} M₂ (AA) + ${xlCount} crosslinker (${crosslinkerAmount}% of AA)`);
    this._updateStats();
  }

  _pushEvent(kind, text) {
    this._eventLog.push({ t: this.time, kind, text });
    if (this._eventLog.length > 20) this._eventLog.shift();
  }

  // ──────────── Kinetics pipeline (same as copolymer) ────────────

  _processInitiation(dt) {
    const rate = this.params.rateMultiplier;
    const kd = 25.0 * rate;

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      if (p.type !== 'initiator') continue;
      if (Math.random() < kd * dt) {
        this._decomposeInitiator(i);
      }
    }
  }

  _decomposeInitiator(idx) {
    const initiator = this.particles[idx];
    const x = initiator.x, y = initiator.y;
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
    this._pushEvent('init', 'I₂ → 2 I• (initiation)');
    this.calloutEvent = {
      title: 'Initiation: I₂ → 2 I•',
      drawFn: (ctx, w, h) => {
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
      },
    };
  }

  _processRadicalCapture(dt) {
    const rate = this.params.rateMultiplier;
    const captureDist = 20;
    const kCapture = 12.5 * rate;

    const primaryRadicals = [];
    const monomersA = [];
    const monomersB = [];

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      if (p.type === 'primaryRadical') primaryRadicals.push(i);
      else if (p.type === 'monomerA' && !p.consumed) monomersA.push(i);
      else if (p.type === 'monomerB' && !p.consumed) monomersB.push(i);
    }

    for (const ri of primaryRadicals) {
      const radical = this.particles[ri];

      let closestIdx = -1;
      let closestDist = captureDist;
      let closestType = null;

      const tryCapture = (targetType) => {
        const list = targetType === 0 ? monomersA : monomersB;
        let localClosest = -1;
        let localDist = captureDist;
        for (const mi of list) {
          const monomer = this.particles[mi];
          if (monomer.consumed) continue;
          const dx = radical.x - monomer.x;
          const dy = radical.y - monomer.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < localDist) {
            localDist = dist;
            localClosest = mi;
          }
        }
        return { idx: localClosest, dist: localDist };
      };

      const resultA = tryCapture(0);
      const resultB = tryCapture(1);
      if (resultA.dist < resultB.dist && resultA.idx >= 0) {
        closestIdx = resultA.idx;
        closestDist = resultA.dist;
        closestType = 0;
      } else if (resultB.idx >= 0) {
        closestIdx = resultB.idx;
        closestDist = resultB.dist;
        closestType = 1;
      }

      if (closestIdx >= 0 && Math.random() < kCapture * dt) {
        const monomer = this.particles[closestIdx];
        monomer.consumed = true;

        this._monomerAAdded += (closestType === 0) ? 1 : 0;
        this._monomerBAdded += (closestType === 1) ? 1 : 0;
        this._recentAAdded += (closestType === 0) ? 1 : 0;
        this._recentBAdded += (closestType === 1) ? 1 : 0;

        const label = closestType === 0 ? 'M₁ (2EHA)' : 'M₂ (AA)';
        this.particles[ri] = {
          type: 'chainRadical',
          chainId: this._nextChainId++,
          initiator: { x: radical.x, y: radical.y },
          segments: [
            { x: monomer.x, y: monomer.y, monomerType: closestType, isCrosslinked: false },
          ],
          vx: (Math.random() - 0.5) * 1.5,
          vy: (Math.random() - 0.5) * 1.5,
          radius: 6,
        };
        this._pushEvent('prop', `I• + ${label} → chain (DP=1)`);
      }
    }
  }

  _processPropagation(dt) {
    const rate = this.params.rateMultiplier;
    const kpBase = 12.5 * rate;
    const r1 = this.params.r1;
    const r2 = this.params.r2;
    const reactDist = 18;

    const chainRadicals = [];
    const monomersA = [];
    const monomersB = [];

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      if (p.type === 'chainRadical') chainRadicals.push(i);
      else if (p.type === 'monomerA' && !p.consumed) monomersA.push(i);
      else if (p.type === 'monomerB' && !p.consumed) monomersB.push(i);
    }

    const freeA = monomersA.length;
    const freeB = monomersB.length;

    for (const ci of chainRadicals) {
      const chain = this.particles[ci];
      const head = chain.segments[chain.segments.length - 1];
      const headType = head.monomerType;

      // Mayo-Lewis probabilistic selection
      let probAddA;
      if (headType === 0) {
        const num = r1 * freeA;
        const den = num + freeB;
        probAddA = den > 0 ? num / den : 0;
      } else {
        const num = freeA;
        const den = num + r2 * freeB;
        probAddA = den > 0 ? num / den : 0;
      }
      const targetType = Math.random() < probAddA ? 0 : 1;

      const targetMonomers = targetType === 0 ? monomersA : monomersB;

      let closestIdx = -1;
      let closestDist = reactDist;

      for (const mi of targetMonomers) {
        const monomer = this.particles[mi];
        if (monomer.consumed) continue;
        const dx = head.x - monomer.x;
        const dy = head.y - monomer.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < closestDist) {
          closestDist = dist;
          closestIdx = mi;
        }
      }

      if (closestIdx >= 0) {
        const effectiveKp = kpBase;
        if (Math.random() < effectiveKp * dt) {
          const monomer = this.particles[closestIdx];
          monomer.consumed = true;

          const mType = targetType;
          chain.segments.push({ x: monomer.x, y: monomer.y, monomerType: mType, isCrosslinked: false });

          this._monomerAAdded += (mType === 0) ? 1 : 0;
          this._monomerBAdded += (mType === 1) ? 1 : 0;
          this._recentAAdded += (mType === 0) ? 1 : 0;
          this._recentBAdded += (mType === 1) ? 1 : 0;

          if (chain.segments.length % 5 === 0) {
            this._pushEvent('prop', `Chain c${chain.chainId}: DP now ${chain.segments.length}`);
          }
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
    const idRemap = {}; // old chainId -> new chainId for crosslink updates

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

          if (Math.random() < 0.5) {
            // Combination: both chains merge into one dead chain
            const combinedSegments = [
              ...chainA.segments,
              ...chainB.segments.slice().reverse(),
            ];
            const newId = this._nextChainId++;
            idRemap[chainA.chainId] = newId;
            idRemap[chainB.chainId] = newId;
            this.particles.push({
              type: 'deadChain',
              chainId: newId,
              segments: combinedSegments,
              vx: (chainA.vx + chainB.vx) / 2,
              vy: (chainA.vy + chainB.vy) / 2,
              radius: 5,
            });
            this._pushEvent('term', `c${chainA.chainId} + c${chainB.chainId} → dc${newId} (combination)`);
          } else {
            // Disproportionation: each chain radical becomes its own dead chain
            const idA = chainA.chainId;
            const idB = chainB.chainId;
            this.particles.push({
              type: 'deadChain',
              chainId: idA,
              segments: [...chainA.segments],
              vx: chainA.vx * 0.5,
              vy: chainA.vy * 0.5,
              radius: 5,
            });
            this.particles.push({
              type: 'deadChain',
              chainId: idB,
              segments: [...chainB.segments],
              vx: chainB.vx * 0.5,
              vy: chainB.vy * 0.5,
              radius: 5,
            });
            this._pushEvent('term', `c${idA} + c${idB} → dc${idA} + dc${idB} (disprop.)`);
          }
          break;
        }
      }
    }

    // Remap crosslinks for combination
    if (Object.keys(idRemap).length > 0) {
      this._crosslinks = this._crosslinks.filter(link => {
        const newA = idRemap[link.aChainId] || link.aChainId;
        const newB = idRemap[link.bChainId] || link.bChainId;
        if (newA === newB) return false; // same chain after merge — drop
        link.aChainId = newA;
        link.bChainId = newB;
        return true;
      });
    }

    const toRemove = [...terminated].sort((a, b) => b - a);
    for (const idx of toRemove) {
      this.particles.splice(idx, 1);
    }
  }

  // ──────────── Crosslinking ────────────

  _processCrosslinking(dt) {
    const rate = this.params.rateMultiplier;
    const reactDist = 10;  // tight: only bridge nearby AA units

    // Collect chains and crosslinkers
    const chains = [];
    const crosslinkers = [];

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      if ((p.type === 'chainRadical' || p.type === 'deadChain') && p.segments?.length) {
        chains.push({ idx: i, particle: p });
      } else if (p.type === 'crosslinker' && !p.consumed) {
        crosslinkers.push({ idx: i, particle: p });
      }
    }

    if (crosslinkers.length === 0) return;

    // Step 1: Free crosslinkers attach to first uncrosslinked AA segment
    for (const cl of crosslinkers) {
      const p = cl.particle;
      if (p.attachedChainId !== null) continue; // already attached at one end

      let bestChainId = null;
      let bestSegIdx = -1;
      let bestDist = reactDist;

      for (const ch of chains) {
        for (let si = 0; si < ch.particle.segments.length; si++) {
          const seg = ch.particle.segments[si];
          if (seg.monomerType !== 1) continue;  // only AA has -COOH
          if (seg.isCrosslinked) continue;       // already crosslinked
          const dx = p.x - seg.x;
          const dy = p.y - seg.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < bestDist) {
            bestDist = dist;
            bestChainId = ch.particle.chainId;
            bestSegIdx = si;
          }
        }
      }

      if (bestChainId !== null) {
        const kAttach = this.params.crosslinkRate * rate;
        if (Math.random() < kAttach * dt) {
          p.attachedChainId = bestChainId;
          p.attachedSegIdx = bestSegIdx;
          // Find the segment and mark it as partially attached
          const targetChain = this._findChainById(bestChainId);
          if (targetChain) {
            targetChain.segments[bestSegIdx]._clAttached = true;
            // Move crosslinker to the segment position
            const seg = targetChain.segments[bestSegIdx];
            p.x = seg.x;
            p.y = seg.y;
          }
        }
      }
    }

    // Step 2: Partially attached crosslinkers find second AA on DIFFERENT chain
    for (const cl of crosslinkers) {
      const p = cl.particle;
      if (p.attachedChainId === null) continue;
      if (p.consumed) continue;

      let bestChainId = null;
      let bestSegIdx = -1;
      let bestDist = reactDist;

      for (const ch of chains) {
        if (ch.particle.chainId === p.attachedChainId) continue; // must be different chain
        for (let si = 0; si < ch.particle.segments.length; si++) {
          const seg = ch.particle.segments[si];
          if (seg.monomerType !== 1) continue;
          if (seg.isCrosslinked) continue;
          const dx = p.x - seg.x;
          const dy = p.y - seg.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < bestDist) {
            bestDist = dist;
            bestChainId = ch.particle.chainId;
            bestSegIdx = si;
          }
        }
      }

      if (bestChainId !== null) {
        const kAttach = this.params.crosslinkRate * rate;
        if (Math.random() < kAttach * dt) {
          // Complete the crosslink!
          const chainA = this._findChainById(p.attachedChainId);
          const chainB = this._findChainById(bestChainId);

          if (chainA && chainB) {
            // Mark both segments as fully crosslinked
            chainA.segments[p.attachedSegIdx].isCrosslinked = true;
            chainA.segments[p.attachedSegIdx]._clAttached = false;
            chainB.segments[bestSegIdx].isCrosslinked = true;

            this._crosslinks.push({
              aChainId: p.attachedChainId,
              aSegIdx: p.attachedSegIdx,
              bChainId: bestChainId,
              bSegIdx: bestSegIdx,
            });

            p.consumed = true;

            // Check gel point
            if (!this._gelPointReached) {
              this._gelPointReached = this._checkGelPoint();
              if (this._gelPointReached) {
                this._pushEvent('xlink', `GEL POINT REACHED — network spans >50% of chains!`);
                this.calloutEvent = {
                  title: 'Gelation! Network formed',
                  drawFn: (ctx, w, h) => {
                    const cx = w / 2, cy = h / 2;
                    ctx.fillStyle = 'rgba(217,74,106,0.3)';
                    ctx.beginPath(); ctx.arc(cx, cy, 30, 0, Math.PI * 2); ctx.fill();
                    ctx.strokeStyle = '#d94a6a';
                    ctx.lineWidth = 2;
                    for (let i = 0; i < 8; i++) {
                      const angle = (i / 8) * Math.PI * 2;
                      ctx.beginPath();
                      ctx.moveTo(cx, cy);
                      ctx.lineTo(cx + Math.cos(angle) * 35, cy + Math.sin(angle) * 35);
                      ctx.stroke();
                    }
                    ctx.fillStyle = '#d94a6a';
                    ctx.font = '10px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.fillText('GEL', cx, cy + 4);
                  },
                };
              }
            }

            if (this._crosslinks.length % 5 === 0) {
              this._pushEvent('xlink', `Crosslink #${this._crosslinks.length}: bridge between c${p.attachedChainId} and c${bestChainId}`);
            }
          }
        }
      }
    }
  }

  _findChainById(chainId) {
    for (const p of this.particles) {
      if ((p.type === 'chainRadical' || p.type === 'deadChain') && p.chainId === chainId) {
        return p;
      }
    }
    return null;
  }

  _checkGelPoint() {
    // Union-Find: largest connected component via crosslinks
    if (this._crosslinks.length < 2) return false;

    // Collect all chainIds from crosslinks
    const chainIds = new Set();
    for (const link of this._crosslinks) {
      chainIds.add(link.aChainId);
      chainIds.add(link.bChainId);
    }

    // Count total chains (dead + active)
    let totalChains = 0;
    for (const p of this.particles) {
      if (p.type === 'chainRadical' || p.type === 'deadChain') totalChains++;
    }
    if (totalChains < 3) return false;

    // Build Union-Find
    const idList = [...chainIds];
    const parent = {};
    const size = {};
    for (const id of idList) {
      parent[id] = id;
      size[id] = 1;
    }

    const find = (x) => {
      while (parent[x] !== x) {
        parent[x] = parent[parent[x]];
        x = parent[x];
      }
      return x;
    };

    const union = (a, b) => {
      const ra = find(a), rb = find(b);
      if (ra === rb) return;
      if (size[ra] < size[rb]) { parent[ra] = rb; size[rb] += size[ra]; }
      else { parent[rb] = ra; size[ra] += size[rb]; }
    };

    for (const link of this._crosslinks) {
      union(link.aChainId, link.bChainId);
    }

    // Find largest component
    let maxSize = 0;
    for (const id of idList) {
      if (parent[id] === id && size[id] > maxSize) {
        maxSize = size[id];
      }
    }

    return maxSize > totalChains * 0.5;
  }

  // ──────────── Stats ────────────

  _updateStats() {
    const totalA = this._initMonomerACount;
    const totalB = this._initMonomerBCount;
    const freeA = this.particles.filter(p => p.type === 'monomerA' && !p.consumed).length;
    const freeB = this.particles.filter(p => p.type === 'monomerB' && !p.consumed).length;
    const totalMonomers = totalA + totalB;
    const consumed = totalMonomers - freeA - freeB;
    const activeChains = this.particles.filter(p => p.type === 'chainRadical').length;
    const deadChains = this.particles.filter(p => p.type === 'deadChain').length;

    // Mn/Mw/PDI from dead chains
    let sumDP = 0, sumDP2 = 0;
    for (const p of this.particles) {
      if (p.type === 'deadChain' && p.segments) {
        const dp = p.segments.length;
        sumDP += dp;
        sumDP2 += dp * dp;
      }
    }
    const mn = deadChains > 0 ? Math.round(consumed / deadChains) : 0;
    const mw = sumDP > 0 ? Math.round(sumDP2 / sumDP) : 0;
    const pdi = (sumDP > 0 && deadChains > 1) ? (sumDP2 / sumDP) / (sumDP / deadChains) : 0;

    // Crosslink stats
    let totalAAinChains = 0;
    for (const p of this.particles) {
      if ((p.type === 'chainRadical' || p.type === 'deadChain') && p.segments) {
        for (const seg of p.segments) {
          if (seg.monomerType === 1) totalAAinChains++;
        }
      }
    }
    const crosslinkedAA = this._crosslinks.length * 2; // each bridge uses 2 AA units
    const xlDensity = totalAAinChains > 0 ? (crosslinkedAA / totalAAinChains) * 100 : 0;

    // Network chains
    const networkChainIds = new Set();
    for (const link of this._crosslinks) {
      networkChainIds.add(link.aChainId);
      networkChainIds.add(link.bChainId);
    }

    this.stats = {
      conversion: totalMonomers > 0 ? Math.round((consumed / totalMonomers) * 100) : 0,
      mn,
      mw,
      pdi: pdi || 0,
      activeChains,
      deadChains,
      freeMonomerA: freeA,
      freeMonomerB: freeB,
      cumulativeF1: (this._monomerAAdded + this._monomerBAdded) > 0
        ? this._monomerAAdded / (this._monomerAAdded + this._monomerBAdded)
        : this._initMonomerACount / totalMonomers,
      instantaneousF1: (this._recentAAdded + this._recentBAdded) > 0
        ? this._recentAAdded / (this._recentAAdded + this._recentBAdded)
        : this._initMonomerACount / totalMonomers,
      crosslinkDensity: xlDensity,
      crosslinkedAA,
      totalAAinChains,
      networkChains: networkChainIds.size,
      gelPointReached: this._gelPointReached,
    };

    this._recentAAdded *= 0.95;
    this._recentBAdded *= 0.95;
  }

  _updateHistories() {
    this._conversionHistory.push({ t: this.time, p: this.stats.conversion });
    this._xlDensityHistory.push({
      t: this.time,
      density: this.stats.crosslinkDensity,
      conversion: this.stats.conversion,
    });
    if (this._xlDensityHistory.length > this._maxHistoryPoints) {
      this._xlDensityHistory.shift();
    }
    if (this._conversionHistory.length > this._maxHistoryPoints) {
      this._conversionHistory.shift();
    }
  }

  // ──────────── Movement (Rouse bead-spring) ────────────

  _moveParticles(dt) {
    const w = this._canvasW;
    const h = this._canvasH;
    const D0 = 2.0;
    const springK = 0.15;
    const targetDist = 10.0;
    const springPasses = 2;

    for (const p of this.particles) {
      if ((p.type === 'monomerA' || p.type === 'monomerB') && p.consumed) continue;

      const isChain = p.type === 'chainRadical' || p.type === 'deadChain';

      if (isChain) {
        const segs = p.segments;
        const N = segs.length;

        if (N === 1) {
          p.vx += (Math.random() - 0.5) * 0.5;
          p.vy += (Math.random() - 0.5) * 0.5;
          p.vx *= 0.98; p.vy *= 0.98;
          segs[0].x += p.vx * dt * 60;
          segs[0].y += p.vy * dt * 60;
        } else {
          // Step 1: Brownian kicks to every segment
          for (let i = 0; i < N; i++) {
            segs[i].x += (Math.random() - 0.5) * D0;
            segs[i].y += (Math.random() - 0.5) * D0;
          }

          // Step 2: intra-chain spring relaxation
          for (let pass = 0; pass < springPasses; pass++) {
            for (let i = 0; i < N - 1; i++) {
              const a = segs[i], b = segs[i + 1];
              let dx = b.x - a.x, dy = b.y - a.y;
              const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
              const force = springK * (dist - targetDist);
              dx /= dist; dy /= dist;
              a.x += force * dx * 0.5;
              a.y += force * dy * 0.5;
              b.x -= force * dx * 0.5;
              b.y -= force * dy * 0.5;
            }
          }

          // Step 3: CM drift
          p.vx += (Math.random() - 0.5) * 0.1;
          p.vy += (Math.random() - 0.5) * 0.1;
          p.vx *= 0.96; p.vy *= 0.96;
          for (let i = 0; i < N; i++) {
            segs[i].x += p.vx * dt * 15;
            segs[i].y += p.vy * dt * 15;
          }
        }

        // Wall bounce
        for (let i = 0; i < segs.length; i++) {
          const s = segs[i];
          if (s.x < 5) s.x = 5;
          if (s.x > w - 5) s.x = w - 5;
          if (s.y < 5) s.y = 5;
          if (s.y > h - 5) s.y = h - 5;
        }
      } else {
        // Free particles
        p.vx += (Math.random() - 0.5) * 0.5;
        p.vy += (Math.random() - 0.5) * 0.5;
        p.vx *= 0.98;
        p.vy *= 0.98;

        const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
        const maxSpeed = 3;
        if (speed > maxSpeed) {
          p.vx = (p.vx / speed) * maxSpeed;
          p.vy = (p.vy / speed) * maxSpeed;
        }

        p.x += p.vx * dt * 60;
        p.y += p.vy * dt * 60;

        if (p.x < p.radius) { p.x = p.radius; p.vx *= -0.5; }
        if (p.x > w - p.radius) { p.x = w - p.radius; p.vx *= -0.5; }
        if (p.y < p.radius) { p.y = p.radius; p.vy *= -0.5; }
        if (p.y > h - p.radius) { p.y = h - p.radius; p.vy *= -0.5; }
      }
    }

    // ── Crosslink spring forces (inter-chain) ──
    const xlSpringK = springK * 0.8;   // nearly as strong as intra-chain bonds
    const maxBridgeDist = 60;          // break bridges stretched beyond this
    const brokenBridges = [];

    for (let li = 0; li < this._crosslinks.length; li++) {
      const link = this._crosslinks[li];
      const chainA = this._findChainById(link.aChainId);
      const chainB = this._findChainById(link.bChainId);
      if (!chainA || !chainB) {
        brokenBridges.push(li);
        continue;
      }

      const segA = chainA.segments[link.aSegIdx];
      const segB = chainB.segments[link.bSegIdx];
      if (!segA || !segB) {
        brokenBridges.push(li);
        continue;
      }

      let dx = segB.x - segA.x;
      let dy = segB.y - segA.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;

      // Break over-stretched bridges
      if (dist > maxBridgeDist) {
        brokenBridges.push(li);
        if (segA.isCrosslinked) segA.isCrosslinked = false;
        if (segB.isCrosslinked) segB.isCrosslinked = false;
        continue;
      }

      const force = xlSpringK * (dist - targetDist);
      dx /= dist; dy /= dist;

      segA.x += force * dx * 0.5;
      segA.y += force * dy * 0.5;
      segB.x -= force * dx * 0.5;
      segB.y -= force * dy * 0.5;
    }

    // Remove broken bridges (highest index first)
    if (brokenBridges.length > 0) {
      for (let i = brokenBridges.length - 1; i >= 0; i--) {
        this._crosslinks.splice(brokenBridges[i], 1);
      }
    }
  }

  // ──────────── Main tick ────────────

  tick(dt) {
    const speed = this.params.speedMultiplier;
    const scaledDt = dt * speed;

    this.time += scaledDt;
    this._moveParticles(scaledDt);
    this._processInitiation(scaledDt);
    this._processRadicalCapture(scaledDt);
    this._processPropagation(scaledDt);
    this._processTermination(scaledDt);
    this._processCrosslinking(scaledDt);

    // Remove consumed monomers and crosslinkers
    this.particles = this.particles.filter(p => {
      if (p.type === 'crosslinker' && p.consumed) return false;
      return !((p.type === 'monomerA' || p.type === 'monomerB') && p.consumed);
    });

    this._updateStats();

    if (this.time - this._lastSampleT >= this._sampleInterval) {
      this._updateHistories();
      this._lastSampleT = this.time;
    }
  }

  // ──────────── Public API ────────────

  getState() {
    return {
      particles: this.particles,
      stats: this.stats,
      crosslinks: this._crosslinks,
    };
  }

  getStats() {
    return this.stats;
  }

  getEventLog() {
    return this._eventLog;
  }

  getConversionHistory() {
    return this._conversionHistory;
  }

  getXLHistory() {
    return this._xlDensityHistory;
  }
}

const THEME = {
  bgColor: '#0f0f23',
  colors: {
    initiator: '#ffd93d',           // yellow
    primaryRadical: '#ff6b6b',       // red
    monomerA: '#4da6ff',            // 2EHA blue
    monomerB: '#ff9f43',            // AA orange
    crosslinker: '#5fff5f',         // bright green — hard to miss
    chainRadical: '#4ecdc4',        // teal
    deadChain: '#555',              // gray
    crosslinkedAA: '#ff3388',       // hot pink (crosslinked AA units)
    networkBridge: '#ff3388',       // hot pink (crosslink bridge lines)
    bg: '#0f0f23',
  },
  radii: {
    initiator: 7,
    primaryRadical: 4,
    monomerA: 5,
    monomerB: 5,
    crosslinker: 6,                 // slightly larger for visibility
    chainRadical: 6,
    deadChain: 5,
  },
  glowColors: {
    primaryRadical: 'rgba(255,107,107,0.6)',
    chainRadical: 'rgba(78,205,196,0.6)',
    crosslinker: 'rgba(95,255,95,0.7)',   // bright green glow
  },
  segmentColor: (monomerType, chainType, segment) => {
    if (monomerType === 0) {
      // M1 (2EHA): blue, dimmer if deadChain
      return chainType === 'deadChain' ? '#3d7ec4' : '#4da6ff';
    }
    if (monomerType === 1) {
      // M2 (AA): crosslinked = hot pink, otherwise orange
      if (segment && segment.isCrosslinked) return '#ff3388';
      return chainType === 'deadChain' ? '#d08a38' : '#ff9f43';
    }
    return '#fff';
  },
};


class UI extends UIBase {
  constructor() {
    super();

    this.btnPlay = document.getElementById('btn-play');
    this.btnPause = document.getElementById('btn-pause');
    this.btnReset = document.getElementById('btn-reset');
    this.sliderInitiator = document.getElementById('slider-initiator');
    this.sliderMonomerA = document.getElementById('slider-monomer-a');
    this.sliderMonomerB = document.getElementById('slider-monomer-b');
    this.sliderR1 = document.getElementById('slider-r1');
    this.sliderR2 = document.getElementById('slider-r2');
    this.sliderCrosslinker = document.getElementById('slider-crosslinker');
    this.sliderXRate = document.getElementById('slider-xrate');
    this.sliderRate = document.getElementById('slider-rate');
    this.sliderSpeed = document.getElementById('slider-speed');
    this.presetSelect = document.getElementById('preset-select');
    this.badgeCopoly = document.getElementById('badge-copolymerization');
    this.badgeCrosslink = document.getElementById('badge-crosslinking');
    this.badgeGelation = document.getElementById('badge-gelation');

    this._bindEvents();

    this.setReadoutSpec([
      { id: 'ro-time',        key: 'time',             format: v => v.toFixed(1) + 's' },
      { id: 'ro-conversion',  key: 'conversion',       format: v => v + '%' },
      { id: 'ro-mn',          key: 'mn',               format: v => v || '—' },
      { id: 'ro-mw',          key: 'mw',               format: v => v || '—' },
      { id: 'ro-pdi',         key: 'pdi',              format: v => (typeof v === 'number' && v > 0 ? v.toFixed(2) : '—') },
      { id: 'ro-xldensity',   key: 'crosslinkDensity',  format: v => v.toFixed(1) + '%' },
      { id: 'ro-net-chains',  key: 'networkChains',    format: v => String(v) },
      { id: 'ro-chains',      key: 'activeChains',     format: v => String(v) },
      { id: 'ro-dead',        key: 'deadChains',       format: v => String(v) },
      { id: 'ro-gelpoint',    key: 'gelPointReached',  format: v => v ? '● GEL' : '○ sol' },
    ]);
  }

  _bindEvents() {
    this.bindButton('btn-play', 'play');
    this.bindButton('btn-pause', 'pause');
    this.bindButton('btn-reset', 'reset');

    this.bindSlider('slider-initiator', 'val-initiator', '', 'initiatorCount');
    this.bindSlider('slider-monomer-a', 'val-monomer-a', '', 'monomerACount');
    this.bindSlider('slider-monomer-b', 'val-monomer-b', '', 'monomerBCount');
    this.bindSlider('slider-r1', 'val-r1', '', 'r1');
    this.bindSlider('slider-r2', 'val-r2', '', 'r2');
    this.bindSlider('slider-crosslinker', 'val-crosslinker', '%', 'crosslinkerAmount');
    this.bindSlider('slider-xrate', 'val-xrate', '', 'crosslinkRate');
    this.bindSlider('slider-rate', 'val-rate', '×', 'rateMultiplier',
      (key, val) => document.getElementById('val-rate').textContent = val.toFixed(1) + '×'
    );

    // Speed slider
    const speedSlider = document.getElementById('slider-speed');
    const speedDisplay = document.getElementById('val-speed');
    if (speedSlider) {
      speedSlider.addEventListener('input', () => {
        const val = parseFloat(speedSlider.value);
        speedDisplay.textContent = val + '×';
        this._cb('speedChange', val);
      });
    }

    // Preset dropdown
    if (this.presetSelect) {
      this.presetSelect.addEventListener('change', () => {
        const preset = this.presetSelect.value;
        this._applyPreset(preset);
      });
    }
  }

  _applyPreset(name) {
    const presets = {
      'psa': {
        monomerACount: 950, monomerBCount: 50,
        crosslinkerAmount: 1, crosslinkRate: 0.5,
        r1: 0.35, r2: 2.5, rateMultiplier: 5.0,
      },
      'sap': {
        monomerACount: 800, monomerBCount: 200,
        crosslinkerAmount: 10, crosslinkRate: 3.0,
        r1: 0.35, r2: 2.5, rateMultiplier: 5.0,
      },
      'hard-coating': {
        monomerACount: 600, monomerBCount: 400,
        crosslinkerAmount: 30, crosslinkRate: 5.0,
        r1: 0.35, r2: 2.5, rateMultiplier: 3.0,
      },
      'hydrogel': {
        monomerACount: 900, monomerBCount: 100,
        crosslinkerAmount: 5, crosslinkRate: 1.5,
        r1: 0.35, r2: 2.5, rateMultiplier: 4.0,
      },
    };

    const p = presets[name];
    if (!p) return;

    const setSlider = (id, valId, value, suffix) => {
      const slider = document.getElementById(id);
      const display = document.getElementById(valId);
      if (slider) slider.value = value;
      if (display) display.textContent = suffix ? value + suffix : value;
    };

    setSlider('slider-monomer-a', 'val-monomer-a', p.monomerACount);
    setSlider('slider-monomer-b', 'val-monomer-b', p.monomerBCount);
    setSlider('slider-crosslinker', 'val-crosslinker', p.crosslinkerAmount, '%');
    setSlider('slider-xrate', 'val-xrate', p.crosslinkRate);
    setSlider('slider-r1', 'val-r1', p.r1);
    setSlider('slider-r2', 'val-r2', p.r2);
    setSlider('slider-rate', 'val-rate', p.rateMultiplier);
    document.getElementById('val-rate').textContent = p.rateMultiplier.toFixed(1) + '×';

    this._cb('paramChange', this._getParams());
  }

  _getParams() {
    return {
      initiatorCount: parseInt(this.sliderInitiator.value),
      monomerACount: parseInt(this.sliderMonomerA.value),
      monomerBCount: parseInt(this.sliderMonomerB.value),
      r1: parseFloat(this.sliderR1.value),
      r2: parseFloat(this.sliderR2.value),
      crosslinkerAmount: parseInt(this.sliderCrosslinker.value),
      crosslinkRate: parseFloat(this.sliderXRate.value),
      rateMultiplier: parseFloat(this.sliderRate.value),
    };
  }

  updateStageBadges(stats) {
    const xlDensity = stats.crosslinkDensity || 0;
    const gelReached = stats.gelPointReached || false;
    const conversion = stats.conversion || 0;

    if (gelReached) {
      this.setBadge('badge-copolymerization', false);
      this.setBadge('badge-crosslinking', false);
      this.setBadge('badge-gelation', true);
    } else if (xlDensity > 0.5) {
      this.setBadge('badge-copolymerization', false);
      this.setBadge('badge-crosslinking', true);
      this.setBadge('badge-gelation', false);
    } else {
      this.setBadge('badge-copolymerization', true);
      this.setBadge('badge-crosslinking', false);
      this.setBadge('badge-gelation', false);
    }
  }
}


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

