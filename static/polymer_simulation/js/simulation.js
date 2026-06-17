// DEPRECATED: use free-radical/simulation.js instead. This file kept for backward compat with js/bundle.js.
export class Simulation {
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
