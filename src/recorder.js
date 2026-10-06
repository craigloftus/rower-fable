// TEMP (debug): captures the raw notification stream from a connected
// fitness machine so real strokes can be replayed into the sim offline and
// used to tune the stroke model. See src/replay.js for the other half.
//
// The file is deliberately raw — every notification is stored as the exact
// bytes the machine sent plus a millisecond timestamp, so a decoder bug
// today does not cost us the data. Shape:
//
//   {
//     format: 'morningrow.ble-recording', version: 1,
//     recordedAt: '2026-07-26T08:12:04.512Z',
//     device: { name: 'PM5 430123456' },
//     userAgent: '...', durationMs: 184320,
//     characteristics: { '2ad1': { name: 'rower_data', samples: 184 } },
//     samples: [ { t: 998.4, c: '2ad1', d: '2c0930000100...' } ]
//   }
//
// t is milliseconds from the start of the recording, c the 16-bit UUID short
// form (or the full UUID for vendor services), d the payload as hex.
export const FORMAT = 'morningrow.ble-recording';
export const FORMAT_VERSION = 1;

const hex = (dv) => {
  const b = new Uint8Array(dv.buffer, dv.byteOffset, dv.byteLength);
  let s = '';
  for (const v of b) s += v.toString(16).padStart(2, '0');
  return s;
};

export const bytes = (h) => {
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(h.slice(i * 2, i * 2 + 2), 16);
  return new DataView(out.buffer);
};

// Web Bluetooth normalises 16-bit UUIDs to the full base form; shorten those
// back so the file stays readable, and leave vendor UUIDs (C2 et al) whole.
export const shortUuid = (uuid) => {
  const m = /^0000([0-9a-f]{4})-0000-1000-8000-00805f9b34fb$/.exec(uuid);
  return m ? m[1] : uuid;
};

const stamp = (d) => {
  const p = (n) => `${n}`.padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
};

export class BleRecorder {
  constructor() {
    this.active = false;
    this.samples = [];
    this.chars = {};      // uuid -> { name, samples }
    this.device = null;
    this.startedAt = null;
    this.t0 = 0;
    this.t1 = 0;
  }

  get count() { return this.samples.length; }
  get seconds() { return ((this.active ? performance.now() : this.t1) - this.t0) / 1000; }

  start(device) {
    this.samples = [];
    this.chars = {};
    this.device = device;
    this.startedAt = new Date();
    this.t0 = performance.now();
    this.t1 = this.t0;
    this.active = true;
  }

  // called for every notification on every characteristic being watched
  push(uuid, name, dv) {
    if (!this.active) return;
    const c = shortUuid(uuid);
    const slot = this.chars[c] || (this.chars[c] = { name, samples: 0 });
    slot.samples++;
    this.samples.push({
      t: Math.round((performance.now() - this.t0) * 10) / 10,
      c,
      d: hex(dv),
    });
  }

  stop() {
    if (!this.active) return;
    this.t1 = performance.now();
    this.active = false;
  }

  toJSON() {
    return {
      format: FORMAT,
      version: FORMAT_VERSION,
      recordedAt: this.startedAt?.toISOString() ?? null,
      device: { name: this.device?.name ?? null, id: this.device?.id ?? null },
      userAgent: navigator.userAgent,
      durationMs: Math.round(this.t1 - this.t0),
      characteristics: this.chars,
      samples: this.samples,
    };
  }

  filename() {
    const who = (this.device?.name || 'rower').replace(/[^\w.-]+/g, '-').toLowerCase();
    return `row-${who}-${stamp(this.startedAt ?? new Date())}.json`;
  }

  // Prompts for a location where the File System Access API is available
  // (Chrome/Edge, i.e. wherever Web Bluetooth works), else falls back to a
  // plain download. Must be called from a user gesture for the picker.
  // Returns the filename saved, or null if the user cancelled.
  async save() {
    const name = this.filename();
    const blob = new Blob([JSON.stringify(this.toJSON())], { type: 'application/json' });
    if (window.showSaveFilePicker) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: name,
          types: [{ description: 'BLE recording', accept: { 'application/json': ['.json'] } }],
        });
        const w = await handle.createWritable();
        await w.write(blob);
        await w.close();
        return handle.name;
      } catch (err) {
        if (err.name === 'AbortError') return null;
        /* no picker permission — fall back to a download */
      }
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    return name;
  }
}
