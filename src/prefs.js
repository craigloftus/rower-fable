import { clamp } from './util.js';
import { CHARACTERS, DEFAULT_CHARACTER } from './characters.js';

// Setup-card state, persisted so the app opens where it was left: the same
// goal mode, the same target for that mode, and the same plan week/session.
// Targets are kept per mode so flipping distance <-> time does not lose the
// other one's choice.
const KEY = 'morningrow.cfg';
const VERSION = 2;

export const MODES = ['just', 'distance', 'time', 'plan'];
export const TARGETS = {
  distance: [[500, '500 m'], [1000, '1000 m'], [2000, '2000 m'], [5000, '5000 m']],
  time: [[120, '2:00'], [300, '5:00'], [600, '10:00'], [1200, '20:00']],
};
export const REPEATS = [1, 2, 4, 6];
export const RESTS = [30, 60, 120];

const defaults = () => ({
  character: DEFAULT_CHARACTER,
  mode: 'distance',
  targets: { distance: 1000, time: 600 },
  repeats: 1,
  rest: 60,
  week: 1,
  session: 1,
});

const oneOf = (v, list, fallback) => (list.includes(v) ? v : fallback);
const inTargets = (mode, v, fallback) =>
  (TARGETS[mode].some(([t]) => t === v) ? v : fallback);

// Anything unrecognised falls back to the default rather than throwing: a
// stale or hand-edited entry should never keep the card from opening.
export function loadPrefs(weeks) {
  const cfg = defaults();
  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem(KEY));
  } catch { /* corrupt entry — fresh start */ }
  if (!saved || typeof saved !== 'object') return cfg;

  cfg.mode = oneOf(saved.mode, MODES, cfg.mode);
  cfg.character = oneOf(saved.character, CHARACTERS.map((c) => c.id), cfg.character);
  // v1 stored a single shared `target`; file it under whichever mode it fits
  const legacy = saved.v ? null : Number(saved.target);
  for (const m of ['distance', 'time']) {
    const v = Number(saved.targets?.[m] ?? (legacy != null ? legacy : NaN));
    cfg.targets[m] = inTargets(m, v, cfg.targets[m]);
  }
  cfg.repeats = oneOf(Number(saved.repeats), REPEATS, cfg.repeats);
  cfg.rest = oneOf(Number(saved.rest), RESTS, cfg.rest);
  cfg.week = clamp(Math.round(saved.week) || 1, 1, weeks);
  cfg.session = clamp(Math.round(saved.session) || 1, 1, 2);
  return cfg;
}

export function savePrefs(cfg) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ v: VERSION, ...cfg }));
  } catch { /* private mode / quota — the session still works, just forgets */ }
}
