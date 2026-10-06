// FTMS (Bluetooth Fitness Machine Service) rower client via Web Bluetooth.
// Subscribes to the Rower Data characteristic and surfaces stroke events,
// stroke rate, pace and power. Works with PM5s and most smart rowers.
const DRIVE_POWER_WATTS = 12;
const DRIVE_COOLDOWN_MS = 900;

// Concept2's proprietary rowing service, where a PM5 publishes per-stroke
// detail the standard FTMS profile has no room for (notably the force curve).
// Only reached by the debug recorder, and skipped on machines without it.
const C2_ROWING_SERVICE = 'ce060030-43e5-11e4-916c-0800200c9a66';

// labels for the streams the debug recorder may pick up, so a saved file is
// readable without a UUID lookup
const NAMES = {
  '00002ad1-0000-1000-8000-00805f9b34fb': 'rower_data',
  '00002ad3-0000-1000-8000-00805f9b34fb': 'training_status',
  '00002ada-0000-1000-8000-00805f9b34fb': 'machine_status',
  '00002ad9-0000-1000-8000-00805f9b34fb': 'control_point',
  'ce060031-43e5-11e4-916c-0800200c9a66': 'c2_general_status',
  'ce060032-43e5-11e4-916c-0800200c9a66': 'c2_additional_status1',
  'ce060033-43e5-11e4-916c-0800200c9a66': 'c2_additional_status2',
  'ce060035-43e5-11e4-916c-0800200c9a66': 'c2_stroke_data',
  'ce060036-43e5-11e4-916c-0800200c9a66': 'c2_additional_stroke_data',
};
// anything else keeps its UUID as the label rather than a guessed name — the
// capture is only useful if what is in it can be trusted

export class FTMS {
  constructor() {
    this.device = null;
    this.connected = false;
    this.spm = 0;          // strokes per minute
    this.pace = 0;         // seconds per 500 m
    this.watts = 0;
    this.deviceDist = 0;   // metres reported by the machine
    this.strokeCount = null;
    this.lastDriveStart = 0;
    this.lastData = 0;     // performance.now() of last notification
    this.onDriveStart = null;
    this.onChange = null;
    this.onRaw = null;     // (uuid, name, DataView) — debug capture tap
    this.server = null;
    this.svc = null;
    this.rowerCh = null;
    this.watching = [];    // extra characteristics subscribed while recording
  }

  get supported() {
    return !!navigator.bluetooth;
  }

  get live() {
    return this.connected && performance.now() - this.lastData < 5000;
  }

  async connect() {
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ services: ['fitness_machine'] }],
      optionalServices: [C2_ROWING_SERVICE],
    });
    this.device = device;
    device.addEventListener('gattserverdisconnected', () => {
      this.connected = false;
      this.watching = [];
      this.onChange?.();
    });
    const server = await device.gatt.connect();
    const svc = await server.getPrimaryService('fitness_machine');
    const ch = await svc.getCharacteristic('rower_data');
    ch.addEventListener('characteristicvaluechanged', (e) => {
      this.onRaw?.(ch.uuid, 'rower_data', e.target.value);
      this.parse(e.target.value);
    });
    await ch.startNotifications();
    this.server = server;
    this.svc = svc;
    this.rowerCh = ch;
    this.connected = true;
    this.strokeCount = null;
    this.lastDriveStart = 0;
    this.onChange?.();
  }

  disconnect() {
    this.device?.gatt?.disconnect();
  }

  // Debug capture: widen the subscription to everything else the machine
  // will notify on — FTMS status characteristics, plus Concept2's rowing
  // service where present. Rower Data is already tapped via onRaw, so it is
  // not touched here. Failures per characteristic are ignored: a machine
  // refusing one stream should not cost us the rest. Returns the names being
  // watched.
  async watchAll() {
    if (!this.connected) return [];
    const services = [this.svc];
    try {
      services.push(await this.server.getPrimaryService(C2_ROWING_SERVICE));
    } catch { /* not a Concept2, or the service is not exposed */ }

    const names = ['rower_data'];
    for (const svc of services) {
      let chars = [];
      try { chars = await svc.getCharacteristics(); } catch { continue; }
      for (const ch of chars) {
        if (ch === this.rowerCh || !ch.properties.notify) continue;
        const name = NAMES[ch.uuid] || ch.uuid.slice(0, 8);
        const on = (e) => this.onRaw?.(ch.uuid, name, e.target.value);
        try {
          ch.addEventListener('characteristicvaluechanged', on);
          await ch.startNotifications();
          this.watching.push({ ch, on });
          names.push(name);
        } catch {
          ch.removeEventListener('characteristicvaluechanged', on);
        }
      }
    }
    return names;
  }

  async unwatchAll() {
    const watching = this.watching;
    this.watching = [];
    for (const { ch, on } of watching) {
      ch.removeEventListener('characteristicvaluechanged', on);
      try { await ch.stopNotifications(); } catch { /* already gone */ }
    }
  }

  driveStart(now = performance.now()) {
    if (now - this.lastDriveStart < DRIVE_COOLDOWN_MS) return;
    this.lastDriveStart = now;
    this.onDriveStart?.();
  }

  // Rower Data (0x2AD1), live: fold a notification into the machine state and
  // raise a drive event when the stroke count ticks or power comes on.
  parse(dv) {
    const now = performance.now();
    const d = decodeRowerData(dv);
    if (d.strokeCount != null) {
      this.spm = d.spm;
      if (this.strokeCount != null && d.strokeCount > this.strokeCount) this.driveStart(now);
      this.strokeCount = d.strokeCount;
    }
    if (d.dist != null) this.deviceDist = d.dist;
    if (d.pace != null) this.pace = d.pace;
    if (d.watts != null) {
      if (d.watts >= DRIVE_POWER_WATTS && this.watts < DRIVE_POWER_WATTS) this.driveStart(now);
      this.watts = d.watts;
    }
    this.lastData = now;
  }
}

// FTMS Rower Data (0x2AD1): uint16 flags, then fields present per flag bit.
// Pure, so recorded packets decode the same way offline (see src/replay.js).
export function decodeRowerData(dv) {
  let o = 0;
  const flags = dv.getUint16(o, true); o += 2;
  const out = { flags };
  if (!(flags & 0x0001)) { // "more data" clear: stroke rate + count present
    out.spm = dv.getUint8(o) / 2; o += 1;
    out.strokeCount = dv.getUint16(o, true); o += 2;
  }
  if (flags & 0x0002) { out.avgSpm = dv.getUint8(o) / 2; o += 1; }
  if (flags & 0x0004) {   // total distance, uint24
    out.dist = dv.getUint16(o, true) | (dv.getUint8(o + 2) << 16);
    o += 3;
  }
  if (flags & 0x0008) {   // instantaneous pace, s/500m (0xffff = no reading)
    const p = dv.getUint16(o, true); o += 2;
    if (p > 0 && p < 0xffff) out.pace = p;
  }
  if (flags & 0x0010) { out.avgPace = dv.getUint16(o, true); o += 2; }
  if (flags & 0x0020) { out.watts = dv.getInt16(o, true); o += 2; }
  return out;
}
