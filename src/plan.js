import { fmtTime } from './util.js';

// The British Rowing "Go Row" beginner plan: eight weeks, two sessions a
// week, building from 1:00 efforts to a confident 2000 m row. Each session
// is a stage list for the Workout engine; intensities carry the plan's
// guide stroke rates.

export const INTENSITY = {
  low:    { rate: [18, 22], aim: '18–22', feel: 'comfortable — can hold a conversation' },
  medium: { rate: [22, 26], aim: '22–26', feel: 'working harder — shorter sentences' },
  high:   { rate: [26, 99], aim: '26+',   feel: 'breathing hard — short bursts' },
};

const row = (by, amount, intensity, extra) => ({ type: 'row', by, amount, intensity, ...extra });
const rest = (amount, light = false) => ({ type: 'rest', by: 'time', amount, light });
// n repeats of work (a stage or a list), resting between but not after
const reps = (n, work, between = null) => {
  const out = [];
  for (let i = 0; i < n; i++) {
    for (const s of [].concat(work)) out.push({ ...s });
    if (between && i < n - 1) out.push({ ...between });
  }
  return out;
};

export const PLAN = [
  { aim: 'Get used to the machine: a consistent stroke rate, sequence and posture.',
    sessions: [
      { desc: '5 × 1:00 low, 1:00 rests',
        stages: reps(5, row('time', 60, 'low'), rest(60)) },
      { desc: '2 × 5:00 low, 3:00 rests',
        stages: reps(2, row('time', 300, 'low'), rest(180)) },
    ] },
  { aim: 'More time rowing, smoothly: a powerful drive, then a slow recovery.',
    sessions: [
      { desc: '5 × 2:00 low, 1:00 rests',
        stages: reps(5, row('time', 120, 'low'), rest(60)) },
      { desc: '3 × 5:00 low, 3:00 rests (or light row)',
        stages: reps(3, row('time', 300, 'low'), rest(180, true)) },
    ] },
  { aim: 'Longer efforts at higher intensity; hold the rate and split steady.',
    sessions: [
      { desc: '4 × 500 m medium, 2:00 rests — note each time',
        stages: reps(4, row('distance', 500, 'medium'), rest(120)) },
      { desc: '10:00 — first half low, second half medium',
        stages: [row('time', 300, 'low'), row('time', 300, 'medium')] },
    ] },
  { aim: 'More medium work, and think distance, not time: work harder, finish sooner.',
    sessions: [
      { desc: '2 × 1000 m medium, 5:00 rest',
        stages: reps(2, row('distance', 1000, 'medium'), rest(300)) },
      { desc: '15:00 alternating 3:00 low / 3:00 medium',
        stages: [row('time', 180, 'low'), row('time', 180, 'medium'), row('time', 180, 'low'),
          row('time', 180, 'medium'), row('time', 180, 'low')] },
    ] },
  { aim: 'Settle at this level, then complete your first 2000 m at medium intensity.',
    sessions: [
      { desc: '5 × (30 strokes low + 10-stroke medium burst)',
        stages: reps(5, [row('strokes', 30, 'low'), row('strokes', 10, 'medium')]) },
      { desc: '2000 m at medium — note your time',
        stages: [row('distance', 2000, 'medium')] },
    ] },
  { aim: 'Short pieces at high intensity build fitness and quick recovery.',
    sessions: [
      { desc: '6 × 1:00 high, 1:00 rests',
        stages: reps(6, row('time', 60, 'high'), rest(60)) },
      { desc: '4 × 500 m medium, 2:00 rests — beat week 3?',
        stages: reps(4, row('distance', 500, 'medium'), rest(120)) },
    ] },
  { aim: 'Varied work: can you hold good technique when you are tired?',
    sessions: [
      { desc: '2 × 1000 m medium + 10-stroke high bursts, 5:00 rest',
        stages: reps(2, row('distance', 1000, 'medium',
          { burst: { first: 60, every: 120, strokes: 10, intensity: 'high' } }), rest(300)) },
      { desc: '2 × 10:00 pyramid low → medium → high → medium → low, 5:00 rest',
        stages: reps(2, [row('time', 120, 'low'), row('time', 120, 'medium'), row('time', 60, 'high'),
          row('time', 120, 'medium'), row('time', 180, 'low')], rest(300)) },
    ] },
  { aim: 'A powerful drive and a slower recovery. How do your 500 m times compare?',
    sessions: [
      { desc: '4 × 5:00 medium, 3:00 rests (or light row)',
        stages: reps(4, row('time', 300, 'medium'), rest(180, true)) },
      { desc: '500 m medium · 1000 m medium · 500 m high, 2:00 rests',
        stages: [row('distance', 500, 'medium'), rest(120),
          row('distance', 1000, 'medium'), rest(120), row('distance', 500, 'high')] },
    ] },
];

// the free goal card compiles to the same stage shape
export function customStages(cfg) {
  return reps(cfg.repeats, row(cfg.mode, cfg.target, null), cfg.rest > 0 ? rest(cfg.rest) : null);
}

// rough seconds per stage, for proportioning the progress strip
const PACE = { low: 0.33, medium: 0.30, high: 0.27 };    // s per metre
const PER_STROKE = { low: 3.0, medium: 2.5, high: 2.1 }; // s per stroke
export function stageSeconds(s) {
  if (s.by === 'distance') return s.amount * (PACE[s.intensity] || 0.30);
  if (s.by === 'strokes') return s.amount * (PER_STROKE[s.intensity] || 2.5);
  return s.amount;
}

export function stageAmount(s) {
  if (s.by === 'time') return fmtTime(s.amount);
  if (s.by === 'distance') return `${s.amount} m`;
  return `${s.amount} strokes`;
}
