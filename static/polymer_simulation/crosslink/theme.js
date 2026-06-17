export const THEME = {
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
