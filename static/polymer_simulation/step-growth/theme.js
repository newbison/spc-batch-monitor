export const THEME = {
  bgColor: '#0f0f23',
  colors: {
    monomerA: '#d97742',
    monomerB: '#4888dd',
    oligomer: '#6abf69',
    deadChain: '#444',
    byproduct: 'rgba(120, 200, 255, 0.3)',
    bg: '#0f0f23',
  },
  radii: {
    monomerA: 5,
    monomerB: 5,
    byproduct: 2,
  },
  glowColors: {},
  segmentColor: (monomerType, chainType) => {
    if (chainType === 'deadChain') {
      return monomerType === 0 ? '#8a5530' : '#2a5590';
    }
    return monomerType === 0 ? '#d97742' : '#4888dd';
  },
};
