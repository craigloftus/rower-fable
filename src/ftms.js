// FTMS (Bluetooth Fitness Machine Service) rower client via Web Bluetooth.
// Subscribes to the Rower Data characteristic and surfaces stroke events,
// stroke rate, pace and power. Works with PM5s and most smart rowers.
export class FTMS {
  constructor() {
    this.device = null;
    this.connected = false;
    this.spm = 0;          // strokes per minute
    this.pace = 0;         // seconds per 500 m
    this.watts = 0;
    this.deviceDist = 0;   // metres reported by the machine
    this.strokeCount = null;
    this.lastData = 0;     // performance.now() of last notification
    this.onStroke = null;
    this.onChange = null;
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
    });
    this.device = device;
    device.addEventListener('gattserverdisconnected', () => {
      this.connected = false;
      this.onChange?.();
    });
    const server = await device.gatt.connect();
    const svc = await server.getPrimaryService('fitness_machine');
    const ch = await svc.getCharacteristic('rower_data');
    ch.addEventListener('characteristicvaluechanged', (e) => this.parse(e.target.value));
    await ch.startNotifications();
    this.connected = true;
    this.strokeCount = null;
    this.onChange?.();
  }

  disconnect() {
    this.device?.gatt?.disconnect();
  }

  // FTMS Rower Data (0x2AD1): uint16 flags, then fields per flag bits
  parse(dv) {
    let o = 0;
    const flags = dv.getUint16(o, true); o += 2;
    if (!(flags & 0x0001)) { // "more data" clear: stroke rate + count present
      this.spm = dv.getUint8(o) / 2; o += 1;
      const sc = dv.getUint16(o, true); o += 2;
      if (this.strokeCount != null && sc > this.strokeCount) {
        const n = Math.min(sc - this.strokeCount, 4);
        for (let i = 0; i < n; i++) this.onStroke?.();
      }
      this.strokeCount = sc;
    }
    if (flags & 0x0002) o += 1; // average stroke rate
    if (flags & 0x0004) {       // total distance, uint24
      this.deviceDist = dv.getUint16(o, true) | (dv.getUint8(o + 2) << 16);
      o += 3;
    }
    if (flags & 0x0008) {       // instantaneous pace, s/500m
      const p = dv.getUint16(o, true); o += 2;
      if (p > 0 && p < 0xffff) this.pace = p;
    }
    if (flags & 0x0010) o += 2; // average pace
    if (flags & 0x0020) {       // instantaneous power
      this.watts = dv.getInt16(o, true); o += 2;
    }
    this.lastData = performance.now();
  }
}
