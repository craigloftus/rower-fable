// Goal/interval state machine. cfg: { mode: 'just'|'distance'|'time',
// target (m or s), repeats, rest (s) }. The clock arms on the first drive.
export class Workout {
  constructor(cfg) {
    this.cfg = cfg;
    this.state = 'waiting'; // waiting -> work <-> rest -> done
    this.interval = 0;      // completed intervals
    this.workT = 0;         // time in the current work interval
    this.restT = 0;         // rest remaining
    this.workTotal = 0;     // time spent working across intervals
    this.totalDist = 0;     // metres rowed during work intervals
    this.intStart = 0;      // dist at the start of the current interval
  }

  start(dist) {
    this.intStart = dist;
  }

  // returns an event string when the state changes: 'start'|'rest'|'work'|'done'
  update(dt, dist, driving) {
    if (this.state === 'done' || this.cfg.mode === 'just') return null;
    if (this.state === 'waiting') {
      if (!driving) return null;
      this.state = 'work';
      this.intStart = dist;
      return 'start';
    }
    let ev = null;
    if (this.state === 'work') {
      this.workT += dt;
      this.workTotal += dt;
      this.d = dist - this.intStart;
      const hit = this.cfg.mode === 'time'
        ? this.workT >= this.cfg.target
        : this.d >= this.cfg.target;
      if (hit) {
        this.totalDist += this.d;
        this.interval++;
        if (this.interval >= this.cfg.repeats) {
          this.state = 'done';
          ev = 'done';
        } else if (this.cfg.rest > 0) {
          this.state = 'rest';
          this.restT = this.cfg.rest;
          ev = 'rest';
        } else {
          this.workT = 0;
          this.intStart = dist;
          ev = 'work';
        }
      }
    } else if (this.state === 'rest') {
      this.restT -= dt;
      if (this.restT <= 0) {
        this.state = 'work';
        this.workT = 0;
        this.intStart = dist;
        ev = 'work';
      }
    }
    return ev;
  }

  // remaining work in the current interval, for the HUD
  remaining(dist) {
    if (this.cfg.mode === 'time') return Math.max(0, this.cfg.target - this.workT);
    return Math.max(0, this.cfg.target - (dist - this.intStart));
  }

  summary() {
    const t = this.workTotal;
    const d = this.totalDist;
    return {
      dist: d,
      time: t,
      split: d > 1 ? (t / d) * 500 : 0,
    };
  }
}
