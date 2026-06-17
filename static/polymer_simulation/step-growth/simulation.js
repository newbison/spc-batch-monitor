export class Simulation {
  constructor() {
    this.particles = [];
    this.time = 0;
    this.params = {
      monomerACount: 500,
      monomerBCount: 500,
      rateMultiplier: 5.0,
      speedMultiplier: 10.0,
    };
    this.stats = {
      conversion: 0,
      dp: 0,
      chains: 0,
      freeMonomerA: 0,
      freeMonomerB: 0,
      byproductCount: 0,
      maxDP: 0,
    };
    this._dpHistory = [];
    this._totalBonds = 0;
    this._initMonomerACount = 0;
    this._initMonomerBCount = 0;
    this._byproductParticles = [];
    this.calloutEvent = null;
    this._canvasW = 800;
    this._canvasH = 500;
    this._tickCounter = 0;
  }

  setCanvasSize(w, h) {
    this._canvasW = w;
    this._canvasH = h;
  }

  setParams(p) {
    const needReset = ('monomerACount' in p && p.monomerACount !== this.params.monomerACount) ||
                      ('monomerBCount' in p && p.monomerBCount !== this.params.monomerBCount);
    Object.assign(this.params, p);
    if (needReset) this.reset();
  }

  reset() {
    this.particles = [];
    this.time = 0;
    this._dpHistory = [];
    this._totalBonds = 0;
    this._byproductParticles = [];
    this._tickCounter = 0;
    this.calloutEvent = null;
    this._initParticles();
  }

  _initParticles() {
    const { monomerACount, monomerBCount } = this.params;
    this._initMonomerACount = monomerACount;
    this._initMonomerBCount = monomerBCount;
    this.particles = [];
    const minDist = 15;

    const tooClose = (x, y, existing) => {
      for (const p of existing) {
        const px = p.x;
        const py = p.y;
        if (Math.hypot(x - px, y - py) < minDist) return true;
      }
      return false;
    };

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
        segments: [{ x, y, monomerType: 0 }],
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
        segments: [{ x, y, monomerType: 1 }],
      });
    }

    this._updateStats();
  }

  // Count free A-end groups on a particle from its segment ends
  _freeA(p) {
    if (!p.segments || p.segments.length === 0) return 0;
    const first = p.segments[0].monomerType;
    const last = p.segments[p.segments.length - 1].monomerType;
    return (first === 0 ? 1 : 0) + (last === 0 ? 1 : 0);
  }

  // Count free B-end groups on a particle from its segment ends
  _freeB(p) {
    if (!p.segments || p.segments.length === 0) return 0;
    const first = p.segments[0].monomerType;
    const last = p.segments[p.segments.length - 1].monomerType;
    return (first === 1 ? 1 : 0) + (last === 1 ? 1 : 0);
  }

  _chainMobility(chainLength) {
    return 1 / Math.sqrt(1 + (chainLength - 1) * 0.3);
  }

  _moveParticles(dt) {
    const w = this._canvasW;
    const h = this._canvasH;

    // Rouse bead-spring model (same as free-radical & copolymer sims):
    // every segment gets an independent Brownian kick, adjacent segments are
    // connected by symmetric harmonic springs, and the whole chain drifts via
    // a damped CM velocity. Produces real random-coil tumbling.
    const D0 = 2.0;
    const springK = 0.15;
    const targetDist = 10.0;
    const springPasses = 2;

    for (const p of this.particles) {
      if (p.type === 'byproduct') continue;

      const segs = p.segments;
      const N = segs ? segs.length : 0;

      if (N === 0) continue;

      if (N === 1) {
        // Single monomer — move like a free particle
        p.vx += (Math.random() - 0.5) * 0.5;
        p.vy += (Math.random() - 0.5) * 0.5;
        p.vx *= 0.98; p.vy *= 0.98;
        const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
        const maxSpeed = 3;
        if (speed > maxSpeed) {
          p.vx = (p.vx / speed) * maxSpeed;
          p.vy = (p.vy / speed) * maxSpeed;
        }
        segs[0].x += p.vx * dt * 60;
        segs[0].y += p.vy * dt * 60;
        p.x = segs[0].x;
        p.y = segs[0].y;
      } else {
        // Step 1: independent Brownian kicks to every segment
        for (let i = 0; i < N; i++) {
          segs[i].x += (Math.random() - 0.5) * D0;
          segs[i].y += (Math.random() - 0.5) * D0;
        }
        // Step 2: spring relaxation between adjacent segments (symmetric)
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
        // Step 3: CM drift (damped momentum)
        p.vx += (Math.random() - 0.5) * 0.1;
        p.vy += (Math.random() - 0.5) * 0.1;
        p.vx *= 0.96; p.vy *= 0.96;
        let cx = 0, cy = 0;
        for (let i = 0; i < N; i++) {
          segs[i].x += p.vx * dt * 15;
          segs[i].y += p.vy * dt * 15;
          cx += segs[i].x; cy += segs[i].y;
        }
        // Sync top-level position with segment centroid (renderer uses p.x/p.y)
        p.x = cx / N;
        p.y = cy / N;
      }

      // Wall clamp — all segments
      for (let i = 0; i < N; i++) {
        const s = segs[i];
        if (s.x < 5) s.x = 5;
        if (s.x > w - 5) s.x = w - 5;
        if (s.y < 5) s.y = 5;
        if (s.y > h - 5) s.y = h - 5;
      }
    }
  }

  _processReactions(dt) {
    const rate = this.params.rateMultiplier;
    const k = 8.0 * rate;
    const reactDist = 18;

    const aCandidates = [];
    const bCandidates = [];

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      if (p.type === 'byproduct') continue;
      if (this._freeA(p) > 0) aCandidates.push(i);
      if (this._freeB(p) > 0) bCandidates.push(i);
    }

    const reacted = new Set();

    for (const ai of aCandidates) {
      if (reacted.has(ai)) continue;
      const particleA = this.particles[ai];
      if (this._freeA(particleA) < 1) continue;

      for (const bi of bCandidates) {
        if (reacted.has(bi)) continue;
        if (ai === bi) continue;
        const particleB = this.particles[bi];
        if (this._freeB(particleB) < 1) continue;

        // Both reactive ends are at the HEADS of the segments arrays
        // (the last segment is where the chain extends)
        const headA = particleA.segments[particleA.segments.length - 1];
        const headB = particleB.segments[particleB.segments.length - 1];

        const dx = headA.x - headB.x;
        const dy = headA.y - headB.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < reactDist && Math.random() < 1 - Math.exp(-k * dt)) {
          // Build alternating chain: reverse B's segments so its HEAD (reaction site)
          // comes first in the concatenated array, adjacent to A's HEAD
          const bReversed = [...particleB.segments].reverse();
          const newSegments = [
            ...particleA.segments,
            ...bReversed,
          ];

          // New chain head is the last segment of newSegments
          const newHead = newSegments[newSegments.length - 1];
          const chainLength = newSegments.length;
          const mob = this._chainMobility(chainLength);

          reacted.add(ai);
          reacted.add(bi);

          this.particles.push({
            type: 'oligomer',
            x: newHead.x,
            y: newHead.y,
            segments: newSegments,
            vx: (particleA.vx + particleB.vx) / 2 + (Math.random() - 0.5) * 0.5 * mob,
            vy: (particleA.vy + particleB.vy) / 2 + (Math.random() - 0.5) * 0.5 * mob,
            radius: 5,
          });

          this._emitByproduct((headA.x + headB.x) / 2, (headA.y + headB.y) / 2);
          this._totalBonds++;

          const fA = this._freeA({ segments: newSegments });
          const fB = this._freeB({ segments: newSegments });

          this.calloutEvent = {
            title: `Step-growth: bond formed (n=${chainLength})`,
            drawFn: (ctx, cw, ch) => {
              const cx = cw / 2, cy = ch / 2;
              const colors = ['#d97742', '#4888dd'];
              const segCount = Math.min(newSegments.length, 6);
              for (let i = 0; i < segCount; i++) {
                const offsetX = -15 + i * 7;
                ctx.fillStyle = colors[i % 2]; // force alternating for display
                ctx.beginPath();
                ctx.arc(cx + offsetX, cy, 5, 0, Math.PI * 2);
                ctx.fill();
              }
              if (newSegments.length > 6) {
                ctx.fillStyle = '#fff';
                ctx.font = '8px sans-serif';
                ctx.fillText('...', cx + 30, cy + 3);
              }
              ctx.fillStyle = '#6abf69';
              ctx.font = '9px sans-serif';
              ctx.fillText(`A:${fA} B:${fB}`, cx - 10, cy - 14);
            },
          };

          break;
        }
      }
    }

    const toRemove = [...reacted].sort((a, b) => b - a);
    for (const idx of toRemove) {
      this.particles.splice(idx, 1);
    }
  }

  _emitByproduct(x, y) {
    this._byproductParticles.push({
      type: 'byproduct',
      x, y,
      vx: (Math.random() - 0.5) * 0.3,
      vy: -0.5 - Math.random() * 1.0,
      radius: 2,
      alpha: 0.3,
      age: 0,
    });

    if (this._byproductParticles.length > 200) {
      this._byproductParticles.shift();
    }
  }

  _updateByproducts(dt) {
    for (const bp of this._byproductParticles) {
      bp.age += dt;
      bp.alpha = Math.max(0, 0.3 - bp.age * 0.8);
      bp.x += bp.vx * dt * 60;
      bp.y += bp.vy * dt * 60;
      bp.vx += (Math.random() - 0.5) * 0.1;
    }
  }

  _cleanupByproducts() {
    this._byproductParticles = this._byproductParticles.filter(bp => bp.alpha > 0);
  }

  _sampleDPData() {
    const p = this.stats.conversion;
    const dpActual = this.stats.dp;
    const dpTheory = p < 1 ? 1 / (1 - p) : 0;

    this._dpHistory.push({ p, dpTheory, dpActual });

    if (this._dpHistory.length > 200) {
      this._dpHistory = this._dpHistory.filter((_, i) => i % 2 === 0);
    }
  }

  _updateStats() {
    const totalA = this._initMonomerACount;
    const totalB = this._initMonomerBCount;
    const totalGroups = totalA * 2 + totalB * 2;

    // Count free A and B groups from segment ends of all particles
    let freeAGroups = 0;
    let freeBGroups = 0;
    for (const p of this.particles) {
      if (p.type === 'byproduct') continue;
      freeAGroups += this._freeA(p);
      freeBGroups += this._freeB(p);
    }
    const consumedGroups = totalGroups - freeAGroups - freeBGroups;
    const p = totalGroups > 0 ? consumedGroups / totalGroups : 0;

    const oligomers = this.particles.filter(p => p.type === 'oligomer');
    const chains = oligomers.filter(p => this._freeA(p) + this._freeB(p) > 0).length;

    const freeMonomerA = this.particles.filter(p => p.type === 'monomerA').length;
    const freeMonomerB = this.particles.filter(p => p.type === 'monomerB').length;

    // Carothers number-average DP: Xn = total monomer units / total molecules.
    // IMPORTANT: includes unreacted monomers (each counts as 1 unit / 1 molecule),
    // so Xn starts at 1 (all monomers) and rises toward 1/(1-p). The previous
    // implementation only counted oligomers, which made DP start at ~2 and
    // systematically overestimate against the 1/(1-p) theory curve.
    const allMolecules = this.particles.filter(pp => pp.type !== 'byproduct');
    const totalUnits = allMolecules.reduce(
      (sum, pp) => sum + (pp.segments ? pp.segments.length : 0), 0);
    const numMolecules = allMolecules.length;
    const dp = numMolecules > 0 ? totalUnits / numMolecules : 0;

    // Carothers max DP from stoichiometric imbalance
    const ratio = Math.min(totalA, totalB) / Math.max(totalA, totalB, 1);
    const maxDP = ratio > 0 && ratio < 1 ? Math.round((1 + ratio) / (1 - ratio)) : 0;

    this.stats = {
      conversion: p,
      dp,
      chains,
      deadChains: 0,
      freeMonomerA,
      freeMonomerB,
      byproductCount: this._totalBonds,
      maxDP,
    };
  }

  tick(dt) {
    const speed = this.params.speedMultiplier;
    const scaledDt = dt * speed;
    this.time += scaledDt;

    this._moveParticles(scaledDt);
    this._processReactions(scaledDt);
    this._updateByproducts(scaledDt);  // scale byproduct physics with sim speed
    this._cleanupByproducts();
    this._updateStats();

    this._tickCounter++;
    if (this._tickCounter % 10 === 0) {
      this._sampleDPData();
    }
  }

  getState() {
    const allParticles = [...this.particles, ...this._byproductParticles];
    return { particles: allParticles, stats: this.stats, dpHistory: this._dpHistory };
  }

  getStats() {
    return this.stats;
  }
}
