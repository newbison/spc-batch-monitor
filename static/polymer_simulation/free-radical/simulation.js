export class Simulation {
  constructor() {
    this.particles = [];
    this.time = 0;
    this.params = {
      initiatorCount: 10,
      monomerCount: 1000,
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
      freeMonomers: 0,
    };
    this._conversionHistory = [];     // { t, p }
    this._sampleInterval = 0.1;       // sample every 0.1 sim seconds
    this._lastSampleT = 0;
    this._maxHistoryPoints = 250;
    this._eventLog = [];              // ring buffer of reaction events
    this._maxEventLog = 5;
    this._nextEventId = 1;
    this.calloutEvent = null;  // { type, data } for the current frame
    this._canvasW = 800;
    this._canvasH = 500;
  }

  setCanvasSize(w, h) {
    this._canvasW = w;
    this._canvasH = h;
  }

  setParams(p) {
    const needReset = ('initiatorCount' in p && p.initiatorCount !== this.params.initiatorCount) ||
                      ('monomerCount' in p && p.monomerCount !== this.params.monomerCount);
    Object.assign(this.params, p);
    if (needReset) this.reset();
  }

  reset() {
    this.particles = [];
    this.time = 0;
    this._conversionHistory = [];
    this._lastSampleT = 0;
    this._eventLog = [];
    this._nextEventId = 1;
    this.calloutEvent = null;
    this._initParticles();
  }

  _pushEvent(kind, text) {
    this._eventLog.push({
      id: this._nextEventId++,
      t: this.time,
      kind,
      text,
    });
    if (this._eventLog.length > this._maxEventLog) {
      this._eventLog.shift();
    }
  }

  _initParticles() {
    const { initiatorCount, monomerCount } = this.params;
    this._initMonomerCount = monomerCount;
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

      // Probability of decomposition this frame: P = 1 - exp(-kd·dt)
      // (exact Poisson limit — avoids the k·dt > 1 saturation of the old linear gate)
      if (Math.random() < 1 - Math.exp(-kd * dt)) {
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

    this._pushEvent('init', 'I₂ → 2 I• (initiator decomposes)');

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
        [cx - 22, cx + 22].forEach(rx => {
          const grad = ctx.createRadialGradient(rx, cy, 0, rx, cy, 10);
          grad.addColorStop(0, 'rgba(255,107,107,0.5)'); grad.addColorStop(1, 'transparent');
          ctx.fillStyle = grad;
          ctx.beginPath(); ctx.arc(rx, cy, 10, 0, Math.PI * 2); ctx.fill();
        });
        ctx.fillStyle = '#fff';
        ctx.font = '12px sans-serif';
        ctx.fillText('→', cx - 4, cy + 20);
      },
    };
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

        if (dist < captureDist && Math.random() < 1 - Math.exp(-kCapture * dt)) {
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
          this._pushEvent('init', 'R• + M → RM• (radical captures first monomer)');

          this.calloutEvent = {
            title: 'Initiation: R• + M → RM•',
            drawFn: (ctx, w, h) => {
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
            },
          };
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

        if (dist < reactDist && Math.random() < 1 - Math.exp(-kp * dt)) {
          monomer.consumed = true;
          // Add monomer position as new head
          chain.segments.push({ x: monomer.x, y: monomer.y });
          const mob = this._chainMobility(chain.segments.length);
          chain.vx += (Math.random() - 0.5) * 0.5 * mob;
          chain.vy += (Math.random() - 0.5) * 0.5 * mob;
          this._pushEvent('prop', `chain + M → longer chain (n=${chain.segments.length})`);

          this.calloutEvent = {
            title: `Propagation: chain + M (n=${chain.segments.length})`,
            drawFn: (ctx, w, h) => {
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
            },
          };
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

        if (dist < termDist && Math.random() < 1 - Math.exp(-kt * dt)) {
          terminated.add(ai);
          terminated.add(bi);

          // 50% combination, 50% disproportionation
          const byCombination = Math.random() < 0.5;
          if (byCombination) {
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

          this._pushEvent('term',
            byCombination
              ? 'chain• + chain• → dead chain (combination)'
              : 'chain• + chain• → 2 dead chains (disproportionation)'
          );

          this.calloutEvent = {
            title: 'Termination',
            drawFn: (ctx, w, h) => {
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
            },
          };
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
    const totalMonomerInit = this._initMonomerCount;
    const free = this.particles.filter(p => p.type === 'monomer' && !p.consumed).length;
    const consumed = totalMonomerInit - free;

    // Collect chain lengths (DP) for Mn/Mw/PDI
    let sumDP = 0;     // Σ DP_i
    let sumDP2 = 0;    // Σ DP_i²
    let deadChains = 0;
    let activeChains = 0;
    for (const p of this.particles) {
      if (p.type === 'chainRadical') {
        activeChains++;
      } else if (p.type === 'deadChain') {
        deadChains++;
        const dp = p.segments ? p.segments.length : 0;
        sumDP += dp;
        sumDP2 += dp * dp;
      }
    }

    const mn = sumDP > 0 ? Math.round(sumDP / deadChains) : 0;
    const mw = sumDP > 0 ? Math.round(sumDP2 / sumDP) : 0;
    const pdi = (sumDP > 0 && deadChains > 1) ? (sumDP2 / sumDP) / (sumDP / deadChains) : 0;

    this.stats = {
      conversion: totalMonomerInit > 0 ? Math.round((consumed / totalMonomerInit) * 100) : 0,
      mn,
      mw,
      pdi: pdi ? pdi : 0,
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

    // Sample conversion history at regular sim-time intervals
    if (this.time - this._lastSampleT >= this._sampleInterval) {
      this._conversionHistory.push({ t: this.time, p: this.stats.conversion });
      this._lastSampleT = this.time;
      if (this._conversionHistory.length > this._maxHistoryPoints) {
        this._conversionHistory.shift();
      }
    }
  }

  getConversionHistory() {
    return this._conversionHistory;
  }

  _chainMobility(chainLength) {
    return 1 / Math.sqrt(1 + (chainLength - 1) * 0.3);
  }

  _moveParticles(dt) {
    const w = this._canvasW;
    const h = this._canvasH;
    const D0 = 2.0;             // segment Brownian intensity per frame
    const springK = 0.15;       // harmonic spring stiffness (stretchy)
    const targetDist = 10.0;    // equilibrium bond length (px)
    const springPasses = 2;     // relaxation iterations (fewer = looser chains)

    for (const p of this.particles) {
      if (p.type === 'monomer' && p.consumed) continue;

      const isChain = p.type === 'chainRadical' || p.type === 'deadChain';

      if (isChain) {
        // ── Rouse bead-spring model ──
        // Every segment gets independent Brownian motion.
        // Adjacent segments connected by harmonic springs.
        // CM diffusion ∝ 1/N emerges naturally — no manual mobility scaling.
        const segs = p.segments;
        const N = segs.length;

        if (N === 1) {
          // Single segment — move like a free particle
          p.vx += (Math.random() - 0.5) * 0.5;
          p.vy += (Math.random() - 0.5) * 0.5;
          p.vx *= 0.98; p.vy *= 0.98;
          segs[0].x += p.vx * dt * 60;
          segs[0].y += p.vy * dt * 60;
        } else {
          // Step 1: independent Brownian kicks to every segment
          for (let i = 0; i < N; i++) {
            segs[i].x += (Math.random() - 0.5) * D0;
            segs[i].y += (Math.random() - 0.5) * D0;
          }

          // Step 2: spring relaxation between adjacent segments
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

          // Step 3: residual CM drift (damped momentum)
          p.vx += (Math.random() - 0.5) * 0.1;
          p.vy += (Math.random() - 0.5) * 0.1;
          p.vx *= 0.96; p.vy *= 0.96;
          for (let i = 0; i < N; i++) {
            segs[i].x += p.vx * dt * 15;
            segs[i].y += p.vy * dt * 15;
          }
        }

        // Wall bounce — all segments
        for (let i = 0; i < segs.length; i++) {
          const s = segs[i];
          if (s.x < 5) s.x = 5;
          if (s.x > w - 5) s.x = w - 5;
          if (s.y < 5) s.y = 5;
          if (s.y > h - 5) s.y = h - 5;
        }

      } else {
        // ── Free particles (monomers, initiators, primary radicals) ──
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

  getEventLog() {
    return this._eventLog;
  }
}
