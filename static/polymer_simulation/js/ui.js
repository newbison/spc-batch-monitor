// DEPRECATED: use free-radical/ui.js instead. This file kept for backward compat with js/bundle.js.
export class UI {
  constructor() {
    this._callbacks = {};
    this._getElements();
    this._bindEvents();
  }

  _getElements() {
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
  }

  _bindEvents() {
    this.btnPlay.addEventListener('click', () => this._cb('play'));
    this.btnPause.addEventListener('click', () => this._cb('pause'));
    this.btnReset.addEventListener('click', () => this._cb('reset'));

    this.sliderInitiator.addEventListener('input', () => {
      document.getElementById('val-initiator').textContent = this.sliderInitiator.value;
      this._cb('paramChange', this._getParams());
    });
    this.sliderMonomer.addEventListener('input', () => {
      document.getElementById('val-monomer').textContent = this.sliderMonomer.value;
      this._cb('paramChange', this._getParams());
    });
    this.sliderRate.addEventListener('input', () => {
      document.getElementById('val-rate').textContent = parseFloat(this.sliderRate.value).toFixed(1) + '×';
      this._cb('paramChange', this._getParams());
    });
    this.sliderSpeed.addEventListener('input', () => {
      document.getElementById('val-speed').textContent = parseFloat(this.sliderSpeed.value) + '×';
      this._cb('speedChange', parseFloat(this.sliderSpeed.value));
    });
  }

  _getParams() {
    return {
      initiatorCount: parseInt(this.sliderInitiator.value),
      monomerCount: parseInt(this.sliderMonomer.value),
      rateMultiplier: parseFloat(this.sliderRate.value),
    };
  }

  on(event, fn) {
    this._callbacks[event] = fn;
  }

  _cb(event, data) {
    if (this._callbacks[event]) this._callbacks[event](data);
  }

  updateReadouts(stats) {
    document.getElementById('ro-time').textContent = stats.time.toFixed(1) + 's';
    document.getElementById('ro-conversion').textContent = stats.conversion + '%';
    document.getElementById('ro-mn').textContent = stats.mn || '—';
    document.getElementById('ro-chains').textContent = stats.activeChains;
    document.getElementById('ro-dead').textContent = stats.deadChains;
    document.getElementById('ro-monomers').textContent = stats.freeMonomers;
  }

  updateStageBadges(stats) {
    const hasActiveChains = stats.activeChains > 0;
    const hasDeadChains = stats.deadChains > 0;

    this._setBadge(this.badgeInit, !hasActiveChains && !hasDeadChains);
    this._setBadge(this.badgeProp, hasActiveChains && stats.conversion < 80);
    this._setBadge(this.badgeTerm, hasDeadChains > 0 || stats.conversion >= 80);
  }

  _setBadge(el, active) {
    if (active) {
      el.classList.add('active');
      el.textContent = el.textContent.replace('○', '●');
    } else {
      el.classList.remove('active');
      el.textContent = el.textContent.replace('●', '○');
    }
  }
}
