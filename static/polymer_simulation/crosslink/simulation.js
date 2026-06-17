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
