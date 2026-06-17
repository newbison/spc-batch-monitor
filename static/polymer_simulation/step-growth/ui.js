import { UIBase } from '../lib/ui-base.js';

export class UI extends UIBase {
  constructor() {
    super();

    this.btnPlay = document.getElementById('btn-play');
    this.btnPause = document.getElementById('btn-pause');
    this.btnReset = document.getElementById('btn-reset');
    this.sliderMonomerA = document.getElementById('slider-monomer-a');
    this.sliderMonomerB = document.getElementById('slider-monomer-b');
    this.sliderRate = document.getElementById('slider-rate');
    this.sliderSpeed = document.getElementById('slider-speed');
    this.presetSelect = document.getElementById('preset-select');
    this.badgeMonomers = document.getElementById('badge-monomers');
    this.badgeReacting = document.getElementById('badge-reacting');
    this.badgeChains = document.getElementById('badge-chains');
    this.badgeSaturated = document.getElementById('badge-saturated');

    this._bindEvents();

    this.setReadoutSpec([
      { id: 'ro-time',       key: 'time',          format: v => v.toFixed(1) + 's' },
      { id: 'ro-conversion', key: 'conversion',    format: v => (v * 100).toFixed(1) + '%' },
      { id: 'ro-dp',         key: 'dp',            format: v => v.toFixed(1) },
      { id: 'ro-chains',     key: 'chains',        format: v => String(v) },
      { id: 'ro-dead',       key: 'deadChains',    format: v => String(v) },
      { id: 'ro-free-a',     key: 'freeMonomerA',  format: v => String(v) },
      { id: 'ro-free-b',     key: 'freeMonomerB',  format: v => String(v) },
      { id: 'ro-byproduct',  key: 'byproductCount', format: v => String(v) },
      { id: 'ro-max-dp',     key: 'maxDP',         format: v => v || '∞' },
    ]);
  }

  _bindEvents() {
    this.bindButton('btn-play', 'play');
    this.bindButton('btn-pause', 'pause');
    this.bindButton('btn-reset', 'reset');

    this.bindSlider('slider-monomer-a', 'val-monomer-a', '', 'monomerACount');
    this.bindSlider('slider-monomer-b', 'val-monomer-b', '', 'monomerBCount');
    this.bindSlider('slider-rate', 'val-rate', '×', 'rateMultiplier',
      (key, val) => document.getElementById('val-rate').textContent = val.toFixed(1) + '×'
    );

    // Speed slider — fires speedChange
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
      'equal':    { monomerACount: 500, monomerBCount: 500 },
      'nylon66':  { monomerACount: 500, monomerBCount: 500 },
      'b-excess': { monomerACount: 400, monomerBCount: 600 },
      'a-excess': { monomerACount: 600, monomerBCount: 400 },
    };

    const p = presets[name];
    if (!p) return;

    const sliderA = document.getElementById('slider-monomer-a');
    const sliderB = document.getElementById('slider-monomer-b');
    sliderA.value = p.monomerACount;
    sliderB.value = p.monomerBCount;
    document.getElementById('val-monomer-a').textContent = p.monomerACount;
    document.getElementById('val-monomer-b').textContent = p.monomerBCount;

    this._cb('paramChange', this._getParams());
  }

  _getParams() {
    return {
      monomerACount: parseInt(this.sliderMonomerA.value),
      monomerBCount: parseInt(this.sliderMonomerB.value),
      rateMultiplier: parseFloat(this.sliderRate.value),
    };
  }

  updateStageBadges(stats) {
    const p = stats.conversion;
    const freeMonomers = stats.freeMonomerA + stats.freeMonomerB;
    const totalInit = this._initTotal || 1000;

    this.setBadge('badge-monomers', freeMonomers > totalInit * 0.5);
    this.setBadge('badge-reacting', p < 0.5 && p > 0.01);
    this.setBadge('badge-chains', p >= 0.5 && p < 0.9);
    this.setBadge('badge-saturated', p >= 0.9);
  }

  setInitTotal(total) {
    this._initTotal = total;
  }
}
