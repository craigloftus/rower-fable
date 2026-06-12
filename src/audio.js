// Tiny synthesised sound effects; the context is created lazily on the
// first user gesture so autoplay policies are satisfied.
export class Sounds {
  constructor() {
    this.ctx = null;
  }

  ensure() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
    }
    if (this.ctx.state === 'suspended') this.ctx.resume();
  }

  tone(freq, t0, dur, peak = 0.15, glide = 0) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const at = ctx.currentTime + t0;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, at);
    if (glide) osc.frequency.exponentialRampToValueAtTime(freq + glide, at + dur * 0.6);
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(peak, at + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    osc.connect(gain).connect(ctx.destination);
    osc.start(at);
    osc.stop(at + dur + 0.05);
  }

  // gentle bubble pop for course markers
  pop() { this.tone(540, 0, 0.16, 0.12, 320); }
  // soft two-note chime at interval boundaries
  chime() { this.tone(660, 0, 0.3, 0.09); this.tone(880, 0.16, 0.4, 0.09); }
  // little arpeggio when the workout completes
  fanfare() {
    this.tone(523, 0, 0.35, 0.09);
    this.tone(659, 0.18, 0.35, 0.09);
    this.tone(784, 0.36, 0.6, 0.10);
  }
}
