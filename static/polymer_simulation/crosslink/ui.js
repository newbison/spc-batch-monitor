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
    this.sliderCrosslinker = document.getElementById('slider-crosslinker');
    this.sliderXRate = document.getElementById('slider-xrate');
    this.sliderRate = document.getElementById('slider-rate');
    this.sliderSpeed = document.getElementById('slider-speed');
    this.presetSelect = document.getElementById('preset-select');
    this.badgeCopoly = document.getElementById('badge-copolymerization');
    this.badgeCrosslink = document.getElementById('badge-crosslinking');
    this.badgeGelation = document.getElementById('badge-gelation');

    this._bindEvents();

    this.setReadoutSpec([
      { id: 'ro-time',        key: 'time',             format: v => v.toFixed(1) + 's' },
      { id: 'ro-conversion',  key: 'conversion',       format: v => v + '%' },
      { id: 'ro-mn',          key: 'mn',               format: v => v || '—' },
      { id: 'ro-mw',          key: 'mw',               format: v => v || '—' },
      { id: 'ro-pdi',         key: 'pdi',              format: v => (typeof v === 'number' && v > 0 ? v.toFixed(2) : '—') },
      { id: 'ro-xldensity',   key: 'crosslinkDensity',  format: v => v.toFixed(1) + '%' },
      { id: 'ro-net-chains',  key: 'networkChains',    format: v => String(v) },
      { id: 'ro-chains',      key: 'activeChains',     format: v => String(v) },
      { id: 'ro-dead',        key: 'deadChains',       format: v => String(v) },
      { id: 'ro-gelpoint',    key: 'gelPointReached',  format: v => v ? '● GEL' : '○ sol' },
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
    this.bindSlider('slider-crosslinker', 'val-crosslinker', '%', 'crosslinkerAmount');
    this.bindSlider('slider-xrate', 'val-xrate', '', 'crosslinkRate');
    this.bindSlider('slider-rate', 'val-rate', '×', 'rateMultiplier',
      (key, val) => document.getElementById('val-rate').textContent = val.toFixed(1) + '×'
    );

    // Speed slider
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
      'psa': {
        monomerACount: 950, monomerBCount: 50,
        crosslinkerAmount: 1, crosslinkRate: 0.5,
        r1: 0.35, r2: 2.5, rateMultiplier: 5.0,
      },
      'sap': {
        monomerACount: 800, monomerBCount: 200,
        crosslinkerAmount: 10, crosslinkRate: 3.0,
        r1: 0.35, r2: 2.5, rateMultiplier: 5.0,
      },
      'hard-coating': {
        monomerACount: 600, monomerBCount: 400,
        crosslinkerAmount: 30, crosslinkRate: 5.0,
        r1: 0.35, r2: 2.5, rateMultiplier: 3.0,
      },
      'hydrogel': {
        monomerACount: 900, monomerBCount: 100,
        crosslinkerAmount: 5, crosslinkRate: 1.5,
        r1: 0.35, r2: 2.5, rateMultiplier: 4.0,
      },
    };

    const p = presets[name];
    if (!p) return;

    const setSlider = (id, valId, value, suffix) => {
      const slider = document.getElementById(id);
      const display = document.getElementById(valId);
      if (slider) slider.value = value;
      if (display) display.textContent = suffix ? value + suffix : value;
    };

    setSlider('slider-monomer-a', 'val-monomer-a', p.monomerACount);
    setSlider('slider-monomer-b', 'val-monomer-b', p.monomerBCount);
    setSlider('slider-crosslinker', 'val-crosslinker', p.crosslinkerAmount, '%');
    setSlider('slider-xrate', 'val-xrate', p.crosslinkRate);
    setSlider('slider-r1', 'val-r1', p.r1);
    setSlider('slider-r2', 'val-r2', p.r2);
    setSlider('slider-rate', 'val-rate', p.rateMultiplier);
    document.getElementById('val-rate').textContent = p.rateMultiplier.toFixed(1) + '×';

    this._cb('paramChange', this._getParams());
  }

  _getParams() {
    return {
      initiatorCount: parseInt(this.sliderInitiator.value),
      monomerACount: parseInt(this.sliderMonomerA.value),
      monomerBCount: parseInt(this.sliderMonomerB.value),
      r1: parseFloat(this.sliderR1.value),
      r2: parseFloat(this.sliderR2.value),
      crosslinkerAmount: parseInt(this.sliderCrosslinker.value),
      crosslinkRate: parseFloat(this.sliderXRate.value),
      rateMultiplier: parseFloat(this.sliderRate.value),
    };
  }

  updateStageBadges(stats) {
    const xlDensity = stats.crosslinkDensity || 0;
    const gelReached = stats.gelPointReached || false;
    const conversion = stats.conversion || 0;

    if (gelReached) {
      this.setBadge('badge-copolymerization', false);
      this.setBadge('badge-crosslinking', false);
      this.setBadge('badge-gelation', true);
    } else if (xlDensity > 0.5) {
      this.setBadge('badge-copolymerization', false);
      this.setBadge('badge-crosslinking', true);
      this.setBadge('badge-gelation', false);
    } else {
      this.setBadge('badge-copolymerization', true);
      this.setBadge('badge-crosslinking', false);
      this.setBadge('badge-gelation', false);
    }
  }
}
