// Stage-list workout engine. A session is an ordered list of stages:
//   { type: 'row'|'rest', by: 'time'|'distance'|'strokes', amount,
//     intensity?, light?, burst? }
// burst: { first, every, strokes, intensity } schedules short hard efforts
// inside a longer row stage ("a 10-stroke burst every other minute").
// The clock arms on the first drive; from then stages advance on their own.
export class Workout {
  constructor(stages) {
    this.stages = stages;
    this.state = 'waiting'; // waiting -> active -> done
    this.i = -1;            // current stage index (-1 until armed)
    this.elapsed = 0;       // seconds in the current stage
    this.strokes = 0;       // catches in the current stage
    this.stageStart = 0;    // dist at the start of the current stage
    this.burst = null;      // { left } while a burst is on
    this.burstAt = Infinity;
    this.workTotal = 0;     // time spent in row stages
    this.totalDist = 0;     // metres credited from completed row stages
  }

  get stage() { return this.stages[Math.max(this.i, 0)]; }
  get rowCount() { return this.stages.reduce((n, s) => n + (s.type === 'row'), 0); }
  rowIndex() {
    let n = 0;
    for (let k = 0; k <= Math.max(this.i, 0); k++) n += this.stages[k].type === 'row';
    return n;
  }

  enter(i, dist) {
    this.i = i;
    this.elapsed = 0;
    this.strokes = 0;
    this.stageStart = dist;
    this.burst = null;
    this.burstAt = this.stage.burst ? this.stage.burst.first : Infinity;
  }

  // events: 'start' | 'stage' | 'burst' | 'burstEnd' | 'done' | null
  update(dt, dist, driving, caught) {
    if (this.state === 'done') return null;
    if (this.state === 'waiting') {
      if (!driving) return null;
      this.state = 'active';
      this.enter(0, dist);
      if (caught) this.strokes = 1; // the arming catch counts
      return 'start';
    }
    const st = this.stage;
    this.elapsed += dt;
    if (caught) this.strokes++;
    if (st.type === 'row') {
      this.workTotal += dt;
      if (st.burst) {
        if (this.burst) {
          if (caught && --this.burst.left <= 0) {
            this.burst = null;
            return 'burstEnd';
          }
        } else if (this.elapsed >= this.burstAt) {
          this.burst = { left: st.burst.strokes };
          this.burstAt += st.burst.every;
          return 'burst';
        }
      }
    }
    if (this.progress(dist) >= st.amount) {
      if (st.type === 'row') this.totalDist += dist - this.stageStart;
      if (this.i + 1 >= this.stages.length) {
        this.state = 'done';
        return 'done';
      }
      this.enter(this.i + 1, dist);
      return 'stage';
    }
    return null;
  }

  progress(dist) {
    const st = this.stage;
    return st.by === 'time' ? this.elapsed
      : st.by === 'distance' ? dist - this.stageStart
      : this.strokes;
  }

  remaining(dist) {
    return Math.max(0, this.stage.amount - this.progress(dist));
  }

  // the burst overrides the stage's base intensity while it runs
  intensity() {
    const st = this.stage;
    if (this.state !== 'active' || st.type !== 'row') return null;
    return this.burst ? st.burst.intensity : st.intensity;
  }

  summary() {
    const t = this.workTotal, d = this.totalDist;
    return { dist: d, time: t, split: d > 1 ? (t / d) * 500 : 0 };
  }
}
