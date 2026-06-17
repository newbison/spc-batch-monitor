export const THEME = {
  bgColor: '#0f0f23',
  colors: {
    initiator: '#ffd93d',
    primaryRadical: '#ff6b6b',
    monomerA: '#4da6ff',
    monomerB: '#ff9f43',
    chainRadical: '#4ecdc4',
    deadChain: '#555',
    bg: '#0f0f23',
  },
  radii: {
    initiator: 7,
    primaryRadical: 4,
    monomerA: 5,
    monomerB: 5,
    chainRadical: 6,
    deadChain: 5,
  },
  glowColors: {
    primaryRadical: 'rgba(255,107,107,0.6)',
    chainRadical: 'rgba(78,205,196,0.6)',
  },
  segmentColor: (monomerType, chainType) => {
    if (chainType === 'deadChain') return monomerType === 0 ? '#3d7ec4' : '#d08a38';
    return monomerType === 0 ? '#4da6ff' : '#ff9f43';
  },
};
