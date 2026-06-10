import { lerp, smooth, easeSin, clamp } from './util.js';

// Geometry constants shared by boat + rower (all metres, boat-local).
// Boat axis = X, bow at +X. Rower faces the stern (-X), feet on the
// stretcher sternward of the seat, sliding bow-ward through the drive.
export const G = {
  seatCatch: -0.12,   // seat x at the catch (compressed)
  seatFinish: 0.36,   // seat x at the finish (legs down)
  leanCatch: 0.46,    // torso pitch, + = forward (toward stern)
  leanFinish: -0.36,  // layback
  oarCatch: 0.99,     // oar sweep angle, + = blade toward bow
  oarFinish: -0.62,
  pinX: 0.05, pinY: 0.30, pinZ: 0.80,   // oarlock pin
  inboard: 0.86, outboard: 2.03,        // scull dimensions either side of pin
  bladeDrive: -0.075, // blade height in the water during the drive
  bladeRec: 0.26,     // blade height on the recovery
  driveDur: 0.85,
  recDur: 1.65,
  restPoint: 0.24,    // recovery fraction where the rower pauses, "easy oars"
  hipY: 0.40,
  ankle: { x: -0.50, y: 0.215, z: 0.115 },
  thigh: 0.46, shin: 0.44,
  upperArm: 0.30, foreArm: 0.32,
};

// Stroke cycle state machine + hull physics.
// phase p in [0,1) of either 'drive' or 'rec'. Holding space (or a queued
// tap) carries the recovery through to the catch; the drive always completes.
export class Stroke {
  constructor() {
    this.mode = 'rec';
    this.p = G.restPoint;
    this.dist = 0;
    this.v = 0;
    this.time = 0;
    this.lastCatch = null;
    this.spm = 0;
  }

  reset() {
    this.dist = 0; this.v = 0; this.spm = 0; this.lastCatch = null;
  }

  update(dt, input) {
    this.time += dt;
    const want = input.held || input.queued;

    if (this.mode === 'drive') {
      this.p += dt / G.driveDur;
      if (this.p >= 1) { this.p = 0; this.mode = 'rec'; }
    } else {
      if (this.p < G.restPoint) {
        // extraction + hands-away always completes
        this.p = Math.min(this.p + dt / G.recDur, want ? 1 : G.restPoint);
      } else if (want) {
        this.p += dt / G.recDur;
      }
      if (this.p >= 1) {
        this.p = 0; this.mode = 'drive'; input.queued = false;
        if (this.lastCatch != null) {
          this.spm = 60 / (this.time - this.lastCatch);
        }
        this.lastCatch = this.time;
      }
    }
    if (this.lastCatch != null && this.time - this.lastCatch > 4) this.spm = 0;

    const pose = this.pose();

    // hull physics: thrust during drive vs linear + quadratic drag
    const drag = 0.028 * this.v + 0.062 * this.v * Math.abs(this.v);
    this.v += (pose.thrust * 5.0 - drag) * dt;
    if (this.v < 0) this.v = 0;
    this.dist += this.v * dt;

    return pose;
  }

  // Maps phase to body/oar targets with realistic sequencing:
  // drive = legs, then back swing, then arms; recovery = the reverse.
  pose() {
    const g = G;
    let seat, lean, oar, blade, feather, thrust;
    if (this.mode === 'drive') {
      const d = this.p;
      seat = lerp(g.seatCatch, g.seatFinish, smooth(0.0, 0.80, d));
      lean = lerp(g.leanCatch, g.leanFinish, smooth(0.20, 0.97, d));
      oar = lerp(g.oarCatch, g.oarFinish, easeSin(d));
      blade = lerp(-0.02, g.bladeDrive, smooth(0, 0.12, d));
      feather = 0;
      thrust = Math.pow(Math.sin(Math.PI * Math.min(d * 1.05, 1)), 1.15);
    } else {
      const r = this.p;
      seat = lerp(g.seatFinish, g.seatCatch, smooth(0.38, 0.96, r));
      lean = lerp(g.leanFinish, g.leanCatch, smooth(0.12, 0.62, r));
      oar = lerp(g.oarFinish, g.oarCatch, easeSin(smooth(0.06, 0.93, r)));
      const out = smooth(0, 0.08, r);     // extraction
      const drop = smooth(0.94, 1, r);    // blade entry at the catch
      blade = lerp(lerp(g.bladeDrive, g.bladeRec, out), -0.02, drop);
      feather = smooth(0.05, 0.18, r) * (1 - smooth(0.86, 0.96, r));
      thrust = 0;
    }
    return { seat, lean, oar, blade, feather, thrust, mode: this.mode, p: this.p };
  }
}
