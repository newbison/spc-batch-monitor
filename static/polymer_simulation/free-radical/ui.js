import { UIBase } from '../lib/ui-base.js';

export class UI extends UIBase {
  constructor() {
    super();

    this.btnPlay = document.getElementById('btn-play');
    this.btnPause = document.getElementById('btn-pause');
    this.btnReset = document.getElementById('btn-reset');
    this.sliderInitiator = document.getElementById('slider-initiator');
    this.sliderMonomer = document.getElementById('slider-monomer');
    this.sliderRate = document.getElementById('slider-rate');
    this.sliderSpeed = document.getElementById('slider-speed');
    this.badgeInit = document.getElementById('badge-initiation');
    this.badgeProp = document.getElementById('badge-propagation');
    this.badgeTerm = document.getElementById('badge-termination');

    this._bindEvents();

    this.setReadoutSpec([
      { id: 'ro-time',       key: 'time',         format: v => v.toFixed(1) + 's' },
      { id: 'ro-conversion', key: 'conversion',   format: v => v + '%' },
      { id: 'ro-mn',         key: 'mn',           format: v => v || '—' },
      { id: 'ro-mw',         key: 'mw',           format: v => v || '—' },
      { id: 'ro-pdi',        key: 'pdi',          format: v => (typeof v === 'number' && v > 0 ? v.toFixed(2) : '—') },
      { id: 'ro-chains',     key: 'activeChains', format: v => String(v) },
      { id: 'ro-dead',       key: 'deadChains',   format: v => String(v) },
      { id: 'ro-monomers',   key: 'freeMonomers',  format: v => String(v) },
    ]);
  }

  _bindEvents() {
    this.bindButton('btn-play', 'play');
    this.bindButton('btn-pause', 'pause');
    this.bindButton('btn-reset', 'reset');

    this.bindSlider('slider-initiator', 'val-initiator', '', 'initiatorCount',
      () => {}
    );
    this.bindSlider('slider-monomer', 'val-monomer', '', 'monomerCount',
      () => {}
    );
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
  }

  _getParams() {
    return {
      initiatorCount: parseInt(this.sliderInitiator.value),
      monomerCount: parseInt(this.sliderMonomer.value),
      rateMultiplier: parseFloat(this.sliderRate.value),
    };
  }

  updateStageBadges(stats) {
    const hasActiveChains = stats.activeChains > 0;
    const hasDeadChains = stats.deadChains > 0;

    this.setBadge('badge-initiation', !hasActiveChains && !hasDeadChains);
    this.setBadge('badge-propagation', hasActiveChains && stats.conversion < 80);
    this.setBadge('badge-termination', hasDeadChains > 0 || stats.conversion >= 80);
  }
}
