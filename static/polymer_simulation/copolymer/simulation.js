export class Simulation {
  constructor() {
    this.particles = [];
    this.time = 0;
    this.params = {
      initiatorCount: 10,
      monomerACount: 950,
      monomerBCount: 50,
      r1: 0.35,
      r2: 2.5,
      rateMultiplier: 5.0,
      speedMultiplier: 10.0,
      alternating: false,
      chainTransfer: 0,
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
    };
    this._monomerAAdded = 0;
    this._monomerBAdded = 0;
    this._recentAAdded = 0;
    this._recentBAdded = 0;
    this.calloutEvent = null;
    this._canvasW = 800;
    this._canvasH = 500;
  }

  setCanvasSize(w, h) {
    this._canvasW = w;
    this._canvasH = h;
  }

  setParams(p) {
    const needReset = ('initiatorCount' in p && p.initiatorCount !== this.params.initiatorCount) ||
                      ('monomerACount' in p && p.monomerACount !== this.params.monomerACount) ||
                      ('monomerBCount' in p && p.monomerBCount !== this.params.monomerBCount);
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
    this._initParticles();
  }

  _initParticles() {
    const { initiatorCount, monomerACount, monomerBCount } = this.params;
    this._initMonomerACount = monomerACount;
    this._initMonomerBCount = monomerBCount;
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

    this._updateStats();
  }

  _processInitiation(dt) {
    const rate = this.params.rateMultiplier;
    const kd = 25.0 * rate;

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      if (p.type !== 'initiator') continue;

      if (Math.random() < 1 - Math.exp(-kd * dt)) {
        this._decomposeInitiator(i);
      }
    }
  }

  _decomposeInitiator(idx) {
    const initiator = this.particles[idx];
    const x = initiator.x;
    const y = initiator.y;

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

    this.calloutEvent = {
      title: 'Initiation: I2 -> 2 I*',
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
        ctx.fillText('->', cx - 4, cy + 20);
      },
    };
  }

  _processRadicalCapture(dt) {
    const rate = this.params.rateMultiplier;
    const captureDist = 20;
    const kCapture = 12.5 * rate;
    const alternating = this.params.alternating;

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

      // In alternating mode the first captured monomer seeds the strict
      // alternation. Starting from the majority type is a reasonable default
      // (the subsequent ABAB... pattern is independent of this first pick).
      let forceType = null;
      if (alternating) {
        if (monomersA.length >= monomersB.length) forceType = 0;
        else forceType = 1;
      }

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

      if (alternating && forceType !== null) {
        const result = tryCapture(forceType);
        if (result.idx >= 0) {
          closestIdx = result.idx;
          closestDist = result.dist;
          closestType = forceType;
        }
        // 首选类型无合适单体时本帧不反应，等待扩散后下次机会；不 fallback 到另一类型
      } else {
        // Original logic: find closest of either type
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
      }

      if (closestIdx >= 0 && Math.random() < 1 - Math.exp(-kCapture * dt)) {
        const monomer = this.particles[closestIdx];
        monomer.consumed = true;

        this._monomerAAdded += (closestType === 0) ? 1 : 0;
        this._monomerBAdded += (closestType === 1) ? 1 : 0;
        this._recentAAdded += (closestType === 0) ? 1 : 0;
        this._recentBAdded += (closestType === 1) ? 1 : 0;

        const label = closestType === 0 ? 'M1 (2EHA)' : 'M2 (AA)';
        // initiator 字段记录引发剂残基位置（M1* 中的 I*），segments 只存真实单体
        this.particles[ri] = {
          type: 'chainRadical',
          initiator: { x: radical.x, y: radical.y },
          segments: [
            { x: monomer.x, y: monomer.y, monomerType: closestType },
          ],
          vx: (Math.random() - 0.5) * 1.5,
          vy: (Math.random() - 0.5) * 1.5,
          radius: 6,
        };
        this.calloutEvent = {
          title: `Initiation: R* + ${label} -> R${closestType === 0 ? 'M1' : 'M2'}*`,
          drawFn: (ctx, w, h) => {
            const cx = w / 2, cy = h / 2;
            ctx.fillStyle = closestType === 0 ? '#4da6ff' : '#ff9f43';
            ctx.beginPath(); ctx.arc(cx + 25, cy, 8, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#ff6b6b';
            ctx.beginPath(); ctx.arc(cx - 15, cy, 5, 0, Math.PI * 2); ctx.fill();
            const grad = ctx.createRadialGradient(cx - 15, cy, 0, cx - 15, cy, 10);
            grad.addColorStop(0, 'rgba(255,107,107,0.5)'); grad.addColorStop(1, 'transparent');
            ctx.fillStyle = grad;
            ctx.beginPath(); ctx.arc(cx - 15, cy, 10, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#fff';
            ctx.font = '14px sans-serif';
            ctx.fillText('->', cx + 4, cy + 5);
          },
        };
      }
    }
  }

  _processPropagation(dt) {
    const rate = this.params.rateMultiplier;
    const kpBase = 12.5 * rate;
    const r1 = this.params.r1;
    const r2 = this.params.r2;
    const reactDist = 18;
    const alternating = this.params.alternating;

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

      let targetType; // 0 = monomerA, 1 = monomerB

      if (alternating) {
        // Strict alternation: always add the opposite type
        targetType = (headType === 0) ? 1 : 0;
      } else {
        // Mayo-Lewis (penultimate model simplified): probabilistic selection
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
        targetType = Math.random() < probAddA ? 0 : 1;
      }

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

      // 链端只尝试加成偏好类型的单体；附近无合适单体时本帧不反应，等待下次机会
      // 不存在"跳跃到另一类型"的 fallback 机制——空间距离不影响反应选择性

      if (closestIdx >= 0) {
        const effectiveKp = kpBase;
        if (Math.random() < 1 - Math.exp(-effectiveKp * dt)) {
          const monomer = this.particles[closestIdx];
          monomer.consumed = true;

          const mType = targetType;
          chain.segments.push({ x: monomer.x, y: monomer.y, monomerType: mType });

          this._monomerAAdded += (mType === 0) ? 1 : 0;
          this._monomerBAdded += (mType === 1) ? 1 : 0;
          this._recentAAdded += (mType === 0) ? 1 : 0;
          this._recentBAdded += (mType === 1) ? 1 : 0;

          const mob = this._chainMobility(chain.segments.length);
          chain.vx += (Math.random() - 0.5) * 0.5 * mob;
          chain.vy += (Math.random() - 0.5) * 0.5 * mob;

          const label = mType === 0 ? 'M1 (2EHA)' : 'M2 (AA)';
          this.calloutEvent = {
            title: `Propagation: +${label} (n=${chain.segments.length})`,
            drawFn: (ctx, w, h) => {
              const cx = w / 2, cy = h / 2;
              ctx.fillStyle = mType === 0 ? '#4da6ff' : '#ff9f43';
              ctx.beginPath(); ctx.arc(cx + 25, cy, 8, 0, Math.PI * 2); ctx.fill();
              ctx.fillStyle = '#4ecdc4';
              ctx.beginPath(); ctx.arc(cx - 15, cy, 7, 0, Math.PI * 2); ctx.fill();
              const grad = ctx.createRadialGradient(cx - 15, cy, 0, cx - 15, cy, 12);
              grad.addColorStop(0, 'rgba(78,205,196,0.5)'); grad.addColorStop(1, 'transparent');
              ctx.fillStyle = grad;
              ctx.beginPath(); ctx.arc(cx - 15, cy, 12, 0, Math.PI * 2); ctx.fill();
              ctx.fillStyle = '#fff';
              ctx.font = '14px sans-serif';
              ctx.fillText('->', cx + 4, cy + 5);
            },
          };

          // Chain transfer: P* + S -> P (dead) + S*，new radical re-initiates.
          // Rate ∝ dt (frame-rate independent) like the other elementary reactions.
          const Ct = this.params.chainTransfer;
          if (Ct > 0 && Math.random() < 1 - Math.exp(-Ct * dt)) {
            const head = chain.segments[chain.segments.length - 1];
            // Convert chain to dead chain
            chain.type = '_ct_dead'; // temporary flag, filtered at end of tick
            // Spawn new primary radical at chain head
            this.particles.push({
              type: 'primaryRadical',
              x: head.x,
              y: head.y,
              vx: (Math.random() - 0.5) * 2,
              vy: (Math.random() - 0.5) * 2,
              radius: 4,
            });
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

          if (Math.random() < 0.5) {
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
              ctx.strokeStyle = '#ff6b6b'; ctx.lineWidth = 2;
              ctx.beginPath(); ctx.moveTo(cx + 5, cy - 15); ctx.lineTo(cx + 15, cy - 5); ctx.stroke();
              ctx.beginPath(); ctx.moveTo(cx + 15, cy - 15); ctx.lineTo(cx + 5, cy - 5); ctx.stroke();
              ctx.fillStyle = '#555';
              ctx.beginPath(); ctx.arc(cx + 45, cy, 8, 0, Math.PI * 2); ctx.fill();
              ctx.fillStyle = '#fff';
              ctx.font = '9px sans-serif';
              ctx.fillText('dead', cx + 35, cy - 14);
            },
          };
          break;
        }
      }
    }

    const toRemove = [...terminated].sort((a, b) => b - a);
    for (const idx of toRemove) {
      this.particles.splice(idx, 1);
    }
  }

  _updateStats() {
    const totalA = this._initMonomerACount;
    const totalB = this._initMonomerBCount;
    const freeA = this.particles.filter(p => p.type === 'monomerA' && !p.consumed).length;
    const freeB = this.particles.filter(p => p.type === 'monomerB' && !p.consumed).length;
    const totalMonomers = totalA + totalB;
    const consumed = totalMonomers - freeA - freeB;
    const activeChains = this.particles.filter(p => p.type === 'chainRadical').length;
    const deadChains = this.particles.filter(p => p.type === 'deadChain').length;

    // Mn / Mw / PDI computed from dead chains only (final polymer, GPC-style).
    // Mn = ΣDP / n_dead,  Mw = ΣDP² / ΣDP,  PDI = Mw / Mn.
    let sumDP = 0, sumDP2 = 0;
    for (const p of this.particles) {
      if (p.type === 'deadChain' && p.segments) {
        const dp = p.segments.length;
        sumDP += dp;
        sumDP2 += dp * dp;
      }
    }
    const mn = deadChains > 0 ? Math.round(sumDP / deadChains) : 0;
    const mw = sumDP > 0 ? Math.round(sumDP2 / sumDP) : 0;
    const pdi = (mn > 0 && mw > 0) ? mw / mn : 0;

    this.stats = {
      conversion: totalMonomers > 0 ? Math.round((consumed / totalMonomers) * 100) : 0,
      mn,
      mw,
      pdi,
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
    };

    this._recentAAdded *= 0.95;
    this._recentBAdded *= 0.95;
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
    this.particles = this.particles.filter(p => {
      if (p.type === '_ct_dead') {
        p.type = 'deadChain'; // promote to proper deadChain so it appears in stats
        return true;
      }
      return !((p.type === 'monomerA' || p.type === 'monomerB') && p.consumed);
    });
    this._updateStats();
  }

  _chainMobility(chainLength) {
    return 1 / Math.sqrt(1 + (chainLength - 1) * 0.3);
  }

  _moveParticles(dt) {
    const w = this._canvasW;
    const h = this._canvasH;

    // Free particles (initiator, primaryRadical, monomerA, monomerB) —
    // simple Brownian diffusion with wall bounce.
    for (const p of this.particles) {
      if (p.consumed) continue;
      if (p.type === 'chainRadical' || p.type === 'deadChain') continue; // handled below

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

    // Polymer chains — Rouse bead-spring model (same as free-radical sim):
    // every segment gets an independent Brownian kick, adjacent segments are
    // connected by symmetric harmonic springs, and the whole chain drifts via
    // a damped CM velocity. This produces real random-coil tumbling instead of
    // the old "head drags a stiff tail" model.
    const D0 = 2.0;
    const springK = 0.15;
    const targetDist = 10.0;
    const springPasses = 2;

    for (const p of this.particles) {
      if (p.type !== 'chainRadical' && p.type !== 'deadChain') continue;
      if (!p.segments || p.segments.length === 0) continue;

      const segs = p.segments;
      const N = segs.length;

      if (N === 1) {
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
        for (let i = 0; i < N; i++) {
          segs[i].x += p.vx * dt * 15;
          segs[i].y += p.vy * dt * 15;
        }
      }

      // Keep the initiator residue (I-M bond) attached to the first segment.
      if (p.initiator) {
        const first = segs[0];
        let dx = first.x - p.initiator.x;
        let dy = first.y - p.initiator.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const force = springK * (dist - targetDist);
        dx /= dist; dy /= dist;
        p.initiator.x += force * dx;
        p.initiator.y += force * dy;
      }

      // Wall clamp — all segments
      for (let i = 0; i < segs.length; i++) {
        const s = segs[i];
        if (s.x < 5) s.x = 5;
        if (s.x > w - 5) s.x = w - 5;
        if (s.y < 5) s.y = 5;
        if (s.y > h - 5) s.y = h - 5;
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
