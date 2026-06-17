import { UIBase } from '../lib/ui-base.js';

export class UI extends UIBase {
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
    this.sliderRate = document.getElementById('slider-rate');
    this.sliderSpeed = document.getElementById('slider-speed');
    this.chkAlternating = document.getElementById('chk-alternating');
    this.sliderCt = document.getElementById('slider-ct');
    this.presetSelect = document.getElementById('preset-select');

    this._bindEvents();

    this.setReadoutSpec([
      { id: 'ro-time',           key: 'time',           format: v => v.toFixed(1) + 's' },
      { id: 'ro-conversion',     key: 'conversion',     format: v => v + '%' },
      { id: 'ro-cumulative-f1',  key: 'cumulativeF1',   format: v => v.toFixed(3) },
      { id: 'ro-instant-f1',     key: 'instantaneousF1', format: v => v.toFixed(3) },
      { id: 'ro-mn',             key: 'mn',             format: v => v || '-' },
      { id: 'ro-mw',             key: 'mw',             format: v => v || '-' },
      { id: 'ro-pdi',            key: 'pdi',            format: v => (typeof v === 'number' && v > 0 ? v.toFixed(2) : '-') },
      { id: 'ro-chains',         key: 'activeChains',   format: v => String(v) },
      { id: 'ro-dead',           key: 'deadChains',     format: v => String(v) },
      { id: 'ro-free-a',         key: 'freeMonomerA',   format: v => String(v) },
      { id: 'ro-free-b',         key: 'freeMonomerB',   format: v => String(v) },
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
    this.bindSlider('slider-rate', 'val-rate', 'x', 'rateMultiplier',
      (key, val) => document.getElementById('val-rate').textContent = val.toFixed(1) + 'x'
    );

    // Chain transfer slider
    const ctSlider = document.getElementById('slider-ct');
    const ctDisplay = document.getElementById('val-ct');
    if (ctSlider) {
      ctSlider.addEventListener('input', () => {
        const val = parseFloat(ctSlider.value);
        ctDisplay.textContent = val.toFixed(2);
        this._cb('paramChange', this._getParams());
      });
    }

    // Speed slider
    const speedSlider = document.getElementById('slider-speed');
    const speedDisplay = document.getElementById('val-speed');
    if (speedSlider) {
      speedSlider.addEventListener('input', () => {
        const val = parseFloat(speedSlider.value);
        speedDisplay.textContent = val + 'x';
        this._cb('speedChange', val);
      });
    }

    // Alternating mode checkbox
    if (this.chkAlternating) {
      this.chkAlternating.addEventListener('change', () => {
        this._cb('paramChange', this._getParams());
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
      '2eha-aa':  { r1: 0.35, r2: 2.5 },   // 2EHA/AA (Q-e estimates)
      'ideal':    { r1: 1.0, r2: 1.0 },
      'alternating': { r1: 0.01, r2: 0.01 },
      'styrene-an': { r1: 0.4, r2: 0.04 },
    };

    const p = presets[name];
    if (!p) return;

    const sliderR1 = document.getElementById('slider-r1');
    const sliderR2 = document.getElementById('slider-r2');
    sliderR1.value = p.r1;
    sliderR2.value = p.r2;
    document.getElementById('val-r1').textContent = p.r1.toFixed(2);
    document.getElementById('val-r2').textContent = p.r2.toFixed(2);

    this._cb('paramChange', this._getParams());
  }

  _getParams() {
    return {
      initiatorCount: parseInt(this.sliderInitiator.value),
      monomerACount: parseInt(this.sliderMonomerA.value),
      monomerBCount: parseInt(this.sliderMonomerB.value),
      r1: parseFloat(this.sliderR1.value),
      r2: parseFloat(this.sliderR2.value),
      rateMultiplier: parseFloat(this.sliderRate.value),
      alternating: this.chkAlternating ? this.chkAlternating.checked : false,
      chainTransfer: this.sliderCt ? parseFloat(this.sliderCt.value) : 0,
    };
  }
}
