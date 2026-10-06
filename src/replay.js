import { bytes, FORMAT } from './recorder.js';
import { decodeRowerData } from './ftms.js';

// The other half of the debug recorder: plays a saved capture back into the
// FTMS client at its recorded timing, so the sim runs off a real machine's
// data with no machine attached. Everything downstream — drive events, the
// rate that paces the animation, the pace that carries the boat — goes
// through the same code path a live device does.
export function isRecording(json) {
  return !!json && json.format === FORMAT && Array.isArray(json.samples);
}

export async function readRecording(file) {
  const json = JSON.parse(await file.text());
  if (!isRecording(json)) throw new Error('not a Morning Row BLE recording');
  return json;
}

// Decoded Rower Data as a time series: the shape to reason about when tuning
// the stroke model (stroke timing from strokeCount steps, drive effort from
// the power trace, boat speed from pace).
export function rowerFrames(rec) {
  const out = [];
  for (const s of rec.samples) {
    if (s.c !== '2ad1') continue;
    out.push({ t: s.t / 1000, ...decodeRowerData(bytes(s.d)) });
  }
  return out;
}

// Catch times, inferred the way the live client infers them: a step in the
// machine's stroke counter. Rower Data lands at ~2 Hz, so these are coarse —
// good enough for rate and drive-onset work, not for sub-stroke phase.
export function catches(rec) {
  const out = [];
  let prev = null;
  for (const f of rowerFrames(rec)) {
    if (f.strokeCount == null) continue;
    if (prev != null && f.strokeCount > prev) out.push(f.t);
    prev = f.strokeCount;
  }
  return out;
}

export class Replay {
  constructor(ftms) {
    this.ftms = ftms;
    this.rec = null;
    this.timer = 0;
    this.i = 0;
    this.t0 = 0;
    this.speed = 1;
    this.wasConnected = false;
    this.onEnd = null;
  }

  get playing() { return !!this.rec; }

  play(rec, { speed = 1 } = {}) {
    if (!isRecording(rec)) throw new Error('not a Morning Row BLE recording');
    this.stop();
    this.rec = rec;
    this.speed = speed;
    this.i = 0;
    this.t0 = performance.now();
    // present as a live machine so the sim treats the feed as real
    this.wasConnected = this.ftms.connected;
    this.ftms.connected = true;
    this.ftms.strokeCount = null;
    this.ftms.lastDriveStart = 0;
    this.ftms.onChange?.();
    this.step();
    return this;
  }

  step() {
    const { samples } = this.rec;
    const due = (performance.now() - this.t0) * this.speed;
    while (this.i < samples.length && samples[this.i].t <= due) {
      const s = samples[this.i++];
      if (s.c === '2ad1') this.ftms.parse(bytes(s.d));
    }
    if (this.i >= samples.length) {
      const done = this.rec;
      this.stop();
      this.onEnd?.(done);
      return;
    }
    const wait = samples[this.i].t / this.speed - (performance.now() - this.t0);
    this.timer = setTimeout(() => this.step(), Math.max(0, wait));
  }

  stop() {
    if (!this.rec) return;
    clearTimeout(this.timer);
    this.timer = 0;
    this.rec = null;
    this.ftms.connected = this.wasConnected;
    this.ftms.onChange?.();
  }
}
