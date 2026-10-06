import * as THREE from 'three';
import { createFramePacer } from './render-budget.js';
import { createPerformanceMonitor } from './performance-monitor.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { World, FOG_COLOR } from './world.js';
import { Course, frame as courseFrame } from './course.js';
import { createCourseBuilder } from './course-builder.js';
import { Boat } from './boat.js';
import { Rower } from './rower.js';
import { CHARACTERS } from './characters.js';
import { Stroke, G } from './stroke.js';
import { fitRowingPose } from './rowing-fit.js';
import { Workout } from './workout.js';
import { createScreenWakeLock } from './wake-lock.js';
import { PLAN, INTENSITY, customStages, stageSeconds, stageAmount } from './plan.js';
import { FTMS } from './ftms.js';
import { Sounds } from './audio.js';
import { loadPrefs, savePrefs, TARGETS, REPEATS, RESTS } from './prefs.js';
import { BleRecorder } from './recorder.js';
import { Replay, readRecording, rowerFrames, catches } from './replay.js';
import { clamp, lerp, fmtTime } from './util.js';

// ------------------------------------------------------------ renderer -----
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
let resolutionOverride = null;
const resizeResolution = () => renderer.setPixelRatio(resolutionOverride ?? devicePixelRatio);
resizeResolution();
renderer.toneMapping = THREE.NoToneMapping;
document.getElementById('app').appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(FOG_COLOR, 120, 620);

const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 1500);

// the course start is not at the world origin: build the camera rig there
const f0 = courseFrame(0, {});
const _yaw0 = new THREE.Matrix4().makeRotationY(f0.th);
const startRel = (x, y, z) =>
  new THREE.Vector3(x, y, z).applyMatrix4(_yaw0).add(new THREE.Vector3(f0.x, 0, f0.z));
camera.position.copy(startRel(10, 4.5, 14));

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(f0.x, 0.55, f0.z);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.minDistance = 2.5;
controls.maxDistance = 60;
controls.maxPolarAngle = 1.52;

// ------------------------------------------------------------- lights ------
const sunDir = new THREE.Vector3(-0.5, 0.75, 0.35).normalize();
const sun = new THREE.DirectionalLight(0xfff1da, 2.4);
sun.position.copy(sunDir).multiplyScalar(90);
scene.add(sun);
scene.add(new THREE.HemisphereLight(0xcfe4e6, 0x9db58a, 1.5));
scene.add(new THREE.AmbientLight(0xfffaf0, 0.25));

// -------------------------------------------------------------- actors -----
const sounds = new Sounds();
const world = new World(scene);
const course = new Course(scene, (pos) => {
  sounds.pop();
  world.fx.ring(pos, 0.5, 1.1, 1.4);
}, createCourseBuilder());

const boatGroup = new THREE.Group();
boatGroup.rotation.order = 'YXZ';
scene.add(boatGroup);
const boat = new Boat(boatGroup);
const rower = new Rower(boatGroup);

// soft contact shadow under the hull
const shadow = new THREE.Mesh(
  new THREE.CircleGeometry(1, 24),
  new THREE.MeshBasicMaterial({ color: 0x1c3a40, transparent: true, opacity: 0.16, depthWrite: false }));
shadow.rotation.order = 'YXZ';
shadow.rotation.set(-Math.PI / 2, 0, 0);
shadow.scale.set(4.4, 0.55, 1);
shadow.position.y = 0.035;
scene.add(shadow);

const stroke = new Stroke();
const input = { held: false, queued: false };

// -------------------------------------------------------------- input ------
addEventListener('keydown', (e) => {
  if (e.code === 'Space') {
    if (elOverlay.classList.contains('show') && e.target.closest('button, input, select, textarea')) return;
    e.preventDefault();
    sounds.ensure();
    if (!e.repeat) { input.held = true; input.queued = true; }
  } else if (e.code === 'KeyR') {
    resetToSetup();
  }
});
addEventListener('keyup', (e) => {
  if (e.code === 'Space') input.held = false;
});
// touch / click-and-hold rows too
let pointerRowing = false;
renderer.domElement.addEventListener('pointerdown', (e) => {
  if (e.pointerType === 'touch') { pointerRowing = true; input.held = true; input.queued = true; }
});
addEventListener('pointerup', () => {
  if (pointerRowing) { pointerRowing = false; input.held = false; }
});

// ---------------------------------------------------------------- HUD ------
const $ = (id) => document.getElementById(id);
const elSplit = $('split'), elRate = $('rate'), elDist = $('dist');
const elHint = $('hint'), elHud = $('hud');
const elOverlay = $('overlay'), elSetup = $('setupCard'), elDone = $('doneCard');
const elGoalStat = $('goalStat'), elGoalLabel = $('goalLabel'), elGoalVal = $('goalVal');
const elSession = $('session'), elSessName = $('sessName'), elSessStage = $('sessStage');
const elRateAim = $('rateAim');
let smoothV = 0, strokes = 0;

function fmtSplit(v) {
  if (v < 0.35) return '–:––';
  return fmtTime(500 / v, 1);
}
// ------------------------------------------------------- goals + overlay ---
// the setup card reopens where it was left: goal mode, that mode's target,
// repeats/rest, and the plan week + session
const cfg = loadPrefs(PLAN.length);
let characterRequest = 0;
async function selectCharacter(id) {
  const request = ++characterRequest;
  $('characterStatus').textContent = 'Loading rower…';
  $('begin').disabled = true;
  try {
    const selected = await rower.select(id);
    if (!selected) return;
    cfg.character = id;
    savePrefs(cfg);
    document.querySelectorAll('#characterChoices button').forEach((b) => {
      b.setAttribute('aria-pressed', String(b.dataset.character === id));
    });
    $('characterStatus').textContent = `${CHARACTERS.find((c) => c.id === id).name} is ready`;
  } catch (error) {
    if (request !== characterRequest) return;
    $('characterStatus').textContent = 'Couldn’t load rower. Choose an avatar to retry.';
    console.error(error);
  } finally {
    if (request === characterRequest) $('begin').disabled = !rower.ready;
  }
}
for (const character of CHARACTERS) {
  const button = document.createElement('button');
  button.type = 'button';
  button.dataset.character = character.id;
  button.setAttribute('aria-label', `Choose ${character.name}`);
  button.setAttribute('aria-pressed', 'false');
  const avatar = document.createElement('span');
  avatar.className = 'character-avatar';
  const portrait = document.createElement('img');
  portrait.src = character.portrait;
  portrait.className = 'character-concept';
  portrait.alt = '';
  avatar.append(portrait);
  const label = document.createElement('span');
  label.textContent = character.name;
  button.append(avatar, label);
  button.addEventListener('click', () => selectCharacter(character.id));
  $('characterChoices').append(button);
}
selectCharacter(cfg.character);
const target = () => cfg.targets[cfg.mode];
let workout = null;
let sessFills = [];   // strip fill elements, one per stage
let lastTick = 0;     // last rest-countdown second chirped
let hintT = 0;        // auto-dim timer for stage hints
let activeLabel = ''; // 'week 3 · session 1' while a plan session runs

// every pick writes the card's state straight back to storage, so closing the
// tab mid-fiddle still reopens on the same choice
function commitSetup() {
  savePrefs(cfg);
  refreshSetup();
}

function buildChips(rowId, list, current, onPick) {
  const box = $(rowId);
  box.innerHTML = '';
  for (const [v, label] of list) {
    const b = document.createElement('button');
    b.textContent = label;
    if (v === current) b.classList.add('sel');
    b.addEventListener('click', () => {
      onPick(v);
      commitSetup();
    });
    box.appendChild(b);
  }
}

// a strip of segments mirroring the stage list: width ~ duration,
// height (via class) = intensity; returns the fill elements for progress
function renderStrip(box, stages) {
  box.innerHTML = '';
  const fills = [];
  for (const st of stages) {
    const seg = document.createElement('div');
    seg.className = `seg ${st.type === 'rest' ? 'rest' : st.intensity || 'medium'}`;
    seg.style.flex = `${Math.max(stageSeconds(st), 25)} 1 0px`;
    const fill = document.createElement('div');
    fill.className = 'fill';
    seg.appendChild(fill);
    box.appendChild(seg);
    fills.push(fill);
  }
  return fills;
}

// the week rail: numbered nodes, prior weeks marked done, the accent line
// filling across to the selected node
function renderWeekRail(current, onPick) {
  const box = $('weekChips');
  box.querySelectorAll('button').forEach((b) => b.remove());
  for (let i = 0; i < PLAN.length; i++) {
    const w = i + 1;
    const b = document.createElement('button');
    b.innerHTML = `<span class="dot"></span>${w}`;
    if (w < current) b.classList.add('done');
    if (w === current) b.classList.add('sel');
    b.addEventListener('click', () => { onPick(w); commitSetup(); });
    box.appendChild(b);
  }
  // anchor the fill to node centres once laid out
  requestAnimationFrame(() => {
    const btns = box.querySelectorAll('button');
    const sel = btns[current - 1];
    if (!sel) return;
    const box0 = box.getBoundingClientRect();
    const mid = (el) => el.getBoundingClientRect().left + el.offsetWidth / 2 - box0.left;
    const fill = $('weekFill');
    fill.style.left = `${mid(btns[0])}px`;
    fill.style.width = `${Math.max(0, mid(sel) - mid(btns[0]))}px`;
  });
}

function refreshSetup() {
  buildChips('modeChips',
    [['just', 'just row'], ['distance', 'distance'], ['time', 'time'], ['plan', 'plan']],
    cfg.mode, (v) => { cfg.mode = v; });
  const goal = cfg.mode === 'distance' || cfg.mode === 'time';
  const plan = cfg.mode === 'plan';
  $('targetRow').hidden = !goal;
  $('repeatRow').hidden = !goal;
  $('restRow').hidden = !goal || cfg.repeats < 2;
  $('planPanel').hidden = !plan;
  if (goal) {
    buildChips('targetChips', TARGETS[cfg.mode], target(), (v) => { cfg.targets[cfg.mode] = v; });
    buildChips('repeatChips', REPEATS.map((n) => [n, `×${n}`]), cfg.repeats, (v) => { cfg.repeats = v; });
    buildChips('restChips', RESTS.map((s) => [s, fmtTime(s)]), cfg.rest, (v) => { cfg.rest = v; });
  }
  if (plan) {
    renderWeekRail(cfg.week, (v) => { cfg.week = v; });
    buildChips('sessionChips', [[1, 'session 1'], [2, 'session 2']], cfg.session, (v) => { cfg.session = v; });
    const week = PLAN[cfg.week - 1], sess = week.sessions[cfg.session - 1];
    renderStrip($('planStrip'), sess.stages);
    $('planDesc').textContent = sess.desc;
    $('planTotal').textContent = `≈ ${Math.round(sess.stages.reduce((a, s) => a + stageSeconds(s), 0) / 60)} min`;
    $('planAim').textContent = week.aim;
  }
}

function showSetup() {
  screenWakeLock.stop();
  refreshSetup();
  elSetup.hidden = false;
  elDone.hidden = true;
  elOverlay.classList.add('show');
  elHud.classList.remove('started');
  elHint.classList.add('gone');
}

const screenWakeLock = createScreenWakeLock({
  onChange(status) {
    const box = $('wakeStatus');
    const label = $('wakeMessage');
    const retry = $('wakeRetry');
    box.hidden = !status.wanted;
    box.dataset.state = status.state;
    retry.hidden = status.state !== 'error';
    label.textContent = status.state === 'active' ? 'Screen awake'
      : status.state === 'requesting' ? 'Keeping screen awake…'
      : status.state === 'insecure' || status.state === 'unsupported' ? status.error
      : status.state === 'suspended' ? 'Screen lock paused while away'
      : 'Screen may sleep. Check power-saving settings and browser permissions.';
    box.title = status.error || '';
  },
});
$('wakeRetry').addEventListener('click', () => screenWakeLock.retry());

// Fullscreen and orientation are optional; screen wake lock is requested
// separately, directly from Begin, so these promises cannot delay it.
async function enterImmersive() {
  try {
    const root = document.documentElement;
    if (!document.fullscreenElement && root.requestFullscreen) {
      await root.requestFullscreen({ navigationUI: 'hide' });
    }
    await screen.orientation?.lock?.('landscape');
  } catch { /* unsupported or denied — carry on windowed */ }
}

function beginWorkout() {
  screenWakeLock.start();
  enterImmersive();
  sounds.ensure();
  stroke.reset();
  course.reset();
  let stages = null;
  if (cfg.mode === 'plan') stages = PLAN[cfg.week - 1].sessions[cfg.session - 1].stages;
  else if (cfg.mode !== 'just') stages = customStages({ ...cfg, target: target() });
  workout = stages ? new Workout(stages) : null;
  activeLabel = cfg.mode === 'plan' ? `week ${cfg.week} · session ${cfg.session}` : '';
  savePrefs(cfg);

  course.setFinish(stages && stages[0].by === 'distance' ? stages[0].amount : null);
  elSession.hidden = !workout;
  if (workout) {
    sessFills = renderStrip($('sessStrip'), stages);
    elSessName.textContent = activeLabel
      || (stages.length > 1 ? `${cfg.repeats} × ${stageAmount(stages[0])}` : stageAmount(stages[0]));
    elSessStage.textContent = 'ready';
  }
  lastTick = 0;
  elRateAim.hidden = true;
  chasePending = true;
  elOverlay.classList.remove('show');
  elHud.classList.add('started');
  elGoalStat.hidden = !workout;
  setHint(ftms.connected ? '<span>row on your machine</span>' : '<span>Hold</span><kbd>space</kbd><span>to row</span>');
  strokes = 0;
}

function showSummary() {
  screenWakeLock.stop();
  const s = workout.summary();
  $('doneTag').textContent = activeLabel ? `${activeLabel} complete` : 'workout complete';
  $('sumDist').textContent = `${s.dist.toFixed(0)} m`;
  $('sumTime').textContent = fmtTime(s.time, 1);
  $('sumSplit').textContent = s.split ? fmtTime(s.split, 1) : '–:––';
  elSetup.hidden = true;
  elDone.hidden = false;
  elOverlay.classList.add('show');
  elHud.classList.remove('started');
  elHint.classList.add('gone');
}

function resetToSetup() {
  stroke.reset();
  course.reset();
  workout = null;
  showSetup();
}

function setHint(html, autodim = false) {
  clearTimeout(hintT);
  elHint.innerHTML = html;
  elHint.classList.remove('gone', 'dim');
  if (autodim) hintT = setTimeout(() => elHint.classList.add('dim'), 4000);
}

function rowHint(st) {
  const parts = [st.by === 'strokes' ? `${st.amount} strokes` : 'row'];
  if (st.intensity) parts.push(st.intensity, `${INTENSITY[st.intensity].aim} spm`);
  return `<span>${parts.join(' · ')}</span>`;
}

function onWorkoutEvent(ev) {
  if (ev === 'done') {
    sounds.fanfare();
    showSummary();
    workout = null;
    return;
  }
  const st = workout.stage;
  if (ev === 'burst') {
    sounds.cueBurst();
    setHint(`<span>burst · ${st.burst.strokes} hard strokes</span>`);
    return;
  }
  if (ev === 'burstEnd') {
    sounds.cueRow(st.intensity);
    setHint(`<span>steady · ${st.intensity}</span>`, true);
    return;
  }
  // 'start' | 'stage': a new stage begins
  lastTick = 0;
  if (st.type === 'rest') {
    sounds.cueRest();
    course.setFinish(null);
  } else {
    sounds.cueRow(st.intensity);
    course.setFinish(st.by === 'distance' ? workout.stageStart + st.amount : null);
    setHint(rowHint(st), true);
  }
}

function updateWorkoutHud() {
  const st = workout.stage;
  const active = workout.state === 'active';
  const idx = Math.max(workout.i, 0);
  const rem = workout.remaining(stroke.dist);
  const frac = active ? 1 - rem / st.amount : 0;
  for (let k = 0; k < sessFills.length; k++) {
    sessFills[k].style.width = k < idx ? '100%' : k === idx ? `${frac * 100}%` : '0%';
    sessFills[k].parentElement.classList.toggle('cur', k === idx && active);
  }

  // bottom-left goal: what to do right now, and how much of it is left
  if (st.type === 'rest') {
    elGoalLabel.textContent = 'Rest';
    elGoalVal.textContent = fmtTime(rem);
    elSessStage.textContent = st.light ? 'rest · or light row' : 'rest';
    const c = Math.ceil(rem);
    if (c <= 3 && c !== lastTick) { sounds.tick(); lastTick = c; }
    setHint(c <= 3 ? `<span>row in ${c}…</span>` : `<span>rest · ${fmtTime(rem)}</span>`);
  } else if (workout.burst) {
    elGoalLabel.textContent = 'Burst';
    elGoalVal.textContent = `${workout.burst.left} strokes`;
    elSessStage.textContent = `burst · ${workout.burst.left} to go`;
  } else {
    elGoalLabel.textContent = `Row ${workout.rowIndex()} of ${workout.rowCount}`;
    elGoalVal.textContent = st.by === 'time' ? fmtTime(rem)
      : st.by === 'distance' ? `${rem.toFixed(0)} m`
      : `${Math.ceil(rem)} strokes`;
    elSessStage.textContent = !active ? 'ready'
      : st.intensity ? `row · ${st.intensity}` : 'row';
  }
  elSessStage.classList.toggle('hot', !!workout.burst || (st.type === 'row' && st.intensity === 'high'));

  // guide stroke rate for the current intensity, judged against the live rate
  const k = active ? workout.intensity() : (st.type === 'row' ? st.intensity : null);
  if (k) {
    elRateAim.hidden = false;
    elRateAim.textContent = `aim ${INTENSITY[k].aim}`;
    const [lo, hi] = INTENSITY[k].rate;
    elRateAim.classList.toggle('on', stroke.spm >= lo && stroke.spm <= hi);
  } else {
    elRateAim.hidden = true;
  }
}

$('begin').addEventListener('click', beginWorkout);
$('again').addEventListener('click', beginWorkout);
$('change').addEventListener('click', showSetup);

// ------------------------------------------------------------- bluetooth ---
const ftms = new FTMS();
const elBt = $('btConnect'), elBtStatus = $('btStatus');
ftms.onDriveStart = () => {
  input.queued = false;
  stroke.catchNow();
};
ftms.onChange = () => {
  elBt.textContent = ftms.connected ? 'disconnect' : 'connect monitor';
  elBtStatus.textContent = ftms.connected ? `linked to ${ftms.device?.name || 'rower'}` : '';
  if (recorder.active && !ftms.connected) stopRecording('device dropped — save it');
  refreshRec();
};
if (!ftms.supported) {
  elBt.disabled = true;
  elBtStatus.textContent = 'bluetooth needs chrome or edge';
}
elBt.addEventListener('click', async () => {
  if (ftms.connected) { ftms.disconnect(); return; }
  elBtStatus.textContent = 'searching…';
  try {
    await ftms.connect();
  } catch (err) {
    elBtStatus.textContent = err.name === 'NotFoundError' ? '' : 'connection failed';
  }
});

// --------------------------------------------- TEMP: raw ble capture -------
// Records the machine's notification stream verbatim and saves it to disk;
// dropping a saved file back on the card replays it through the same code
// path a live device drives, so the stroke model can be worked on away from
// the boathouse. Remove alongside #debugRow when the model settles.
const recorder = new BleRecorder();
const replay = new Replay(ftms);
const elRec = $('recToggle'), elRecStatus = $('recStatus');
let recNote = '';     // transient status line; falls back to the hint below
let recPending = false; // captured samples not yet written to disk
let recTick = 0;

function refreshRec() {
  const rec = recorder.active;
  elRec.disabled = !rec && !recPending && (!ftms.connected || replay.playing);
  elRec.textContent = rec ? `stop · ${fmtTime(recorder.seconds)} · ${recorder.count}`
    : recPending ? 'save recording' : 'record ble';
  elRec.classList.toggle('on', rec);
  elRecStatus.textContent = recNote
    || (replay.playing ? 'replaying — press begin'
      : ftms.connected ? 'or drop a recording here to replay'
      : 'connect a monitor, or drop a recording here');
}

async function startRecording() {
  recNote = '';
  recorder.start(ftms.device);
  ftms.onRaw = (uuid, name, dv) => recorder.push(uuid, name, dv);
  recPending = true;
  recTick = setInterval(refreshRec, 500);
  refreshRec();
  const names = await ftms.watchAll();
  recNote = `${names.length} stream${names.length === 1 ? '' : 's'}: ${names.join(' · ')}`;
  refreshRec();
}

function stopRecording(note) {
  clearInterval(recTick);
  recorder.stop();
  ftms.onRaw = null;
  ftms.unwatchAll();  // cleanup; not awaited so a save keeps its user gesture
  recNote = note || '';
  refreshRec();
}

elRec.addEventListener('click', async () => {
  if (recorder.active) stopRecording();
  else if (!recPending) return startRecording();
  if (!recorder.count) {
    recPending = false;
    recNote = 'nothing captured — is the machine awake?';
    return refreshRec();
  }
  const name = await recorder.save();
  recPending = !name;
  recNote = name ? `saved ${name} · ${recorder.count} packets` : 'save cancelled';
  refreshRec();
});

// drop a saved recording anywhere on the setup card to play it back
const dropZone = elOverlay;
dropZone.addEventListener('dragover', (e) => {
  if (elSetup.hidden) return;
  e.preventDefault();
  dropZone.classList.add('dropping');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dropping'));
dropZone.addEventListener('drop', async (e) => {
  if (elSetup.hidden) return;
  e.preventDefault();
  dropZone.classList.remove('dropping');
  const file = e.dataTransfer.files[0];
  if (!file) return;
  try {
    const rec = await readRecording(file);
    replay.play(rec);
    recNote = `replaying ${file.name} · ${Math.round(rec.durationMs / 1000)}s`;
  } catch (err) {
    recNote = `not a recording: ${err.message}`;
  }
  refreshRec();
});
replay.onEnd = () => { recNote = 'replay finished'; refreshRec(); };
refreshRec();

// ------------------------------------------------------------ fly-in -------
const camFrom = camera.position.clone();
const camTo = startRel(3.9, 2.1, 7.3);
let introT = 0, introDone = false;
function endIntro() {
  if (introDone) return;
  introDone = true;
  showSetup();
}
renderer.domElement.addEventListener('pointerdown', endIntro, { once: true });

// --------------------------------------------------------------- loop ------
let last = performance.now();
let prevBlade = 0.2, prevMode = 'rec', dripT = 0;

// chase view: once rowing starts, the camera settles in behind the boat,
// above and angled down, looking along the hull in the direction of travel
const CHASE = { back: 8.5, up: 3.6, dur: 4.5, ease: 1.1 };
let chasePending = false, chaseT = 0;
const _chase = new THREE.Vector3();
let prevTh = f0.th;
const _up = new THREE.Vector3(0, 1, 0);
const _off = new THREE.Vector3();
// a deliberate camera drag (or zoom) takes priority over the settle
let downX = 0, downY = 0;
renderer.domElement.addEventListener('pointerdown', (e) => { downX = e.clientX; downY = e.clientY; });
renderer.domElement.addEventListener('pointermove', (e) => {
  if (e.buttons && Math.hypot(e.clientX - downX, e.clientY - downY) > 10) chaseT = 0;
});
addEventListener('wheel', () => { chaseT = 0; });
const _w = new THREE.Vector3();
const _anchor = new THREE.Vector3();
const _delta = new THREE.Vector3();
const _frame = {};

function bladeWorld(tipLocal) {
  return _w.copy(tipLocal).applyMatrix4(boatGroup.matrix);
}

// dev handle for poking the sim from the console
window.__sim = {
  camera, controls, stroke, input, scene, boat, rower, course, world, renderer, ftms,
  // TEMP: stroke-model work — __sim.replay.play(rec, { speed: 4 }), and
  // __sim.frames(rec) / __sim.catches(rec) for the decoded time series
  recorder, replay, frames: rowerFrames, catches, wakeLock: screenWakeLock,
  get workout() { return workout; },
  pause(mode, p) { stroke.mode = mode; stroke.p = p; window.__paused = true; },
  play() { window.__paused = false; },
  step(ms = 16) { last -= ms; renderFrame(performance.now()); }, // manual frame, e.g. for hidden tabs
};

const perf = createPerformanceMonitor(renderer, () => ({
  character: rower.character, characterReady: rower.ready, characterVisible: rower.group.visible,
  targetFps: elOverlay.classList.contains('show') && introDone ? 30 : 120, visibility: document.visibilityState, viewport: [innerWidth, innerHeight], distance: Math.round(stroke.dist),
  wakeLock: screenWakeLock.status,
}));
if (perf) {
  perf.onCaptureStart = () => { if (!rower.ready || ftms.connected) return false; beginWorkout(); input.held = true; };
  perf.onCaptureEnd = () => { input.held = false; };
  perf.onCharacter = visible => { rower.group.visible = visible; };
  perf.onResolution = value => { resolutionOverride = value === 'auto' ? null : Number(value); resizeResolution(); };
}

const shouldRender = createFramePacer();
let nextHud = 0;
function tick(now) {
  perf?.animationFrame(now);
  if (document.hidden || !shouldRender(now, elOverlay.classList.contains('show') && introDone ? 30 : 120)) return;
  renderFrame(now);
}

function renderFrame(now) {
  perf?.begin(now);
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  const t = now / 1000;

  if (!introDone) {
    introT = Math.min(introT + dt / 3.2, 1);
    const e = 1 - Math.pow(1 - introT, 3);
    camera.position.lerpVectors(camFrom, camTo, e);
    if (introT >= 1) endIntro();
  }

  // a live machine paces the avatar and carries the boat at its real pace
  if (ftms.live) {
    if (ftms.spm > 8) stroke.tempo = clamp((60 / ftms.spm) / (G.driveDur + G.recDur), 0.55, 1.6);
    if (ftms.pace > 0) {
      const vT = 500 / ftms.pace;
      stroke.v += (vT - stroke.v) * Math.min(1, dt * 1.5);
    }
  } else {
    stroke.tempo = 1;
  }

  // dev: window.__sim.pause('drive', 0.5) freezes the cycle for inspection
  const pose = fitRowingPose(window.__paused ? stroke.pose() : stroke.update(dt, input), rower.character);

  // follow the river: position + heading from the course centreline
  courseFrame(stroke.dist, _frame);
  const c = (G.seatFinish - pose.seat) / (G.seatFinish - G.seatCatch); // 1 at catch
  boatGroup.position.set(
    _frame.x,
    0.02 * Math.sin(t * 1.1) + 0.012 * Math.sin(t * 1.7) - 0.012 * pose.thrust,
    _frame.z);
  boatGroup.rotation.set(
    0.010 * Math.sin(t * 0.74) + (pose.mode === 'rec' ? 0.006 * Math.sin(t * 3.1) : 0),
    _frame.th,
    0.012 * Math.sin(t * 0.9) + lerp(-0.008, 0.010, c));
  boatGroup.updateMatrix();

  shadow.position.set(_frame.x, 0.035, _frame.z);
  shadow.rotation.y = _frame.th;

  // camera rig is locked to the boat: translate with it and swing around
  // it as the river bends, so the view holds its boat-relative angle
  _anchor.set(_frame.x, 0.55, _frame.z);
  _delta.subVectors(_anchor, controls.target);
  controls.target.copy(_anchor);
  camera.position.add(_delta);
  if (_frame.th !== prevTh) {
    _off.subVectors(camera.position, _anchor).applyAxisAngle(_up, _frame.th - prevTh);
    camera.position.copy(_anchor).add(_off);
    prevTh = _frame.th;
  }

  // ease toward the chase position behind the stern (travel dir is
  // (cos th, 0, -sin th), matching the course centreline integration)
  if (chaseT > 0) {
    chaseT -= dt;
    _chase.set(
      _frame.x - Math.cos(_frame.th) * CHASE.back,
      CHASE.up,
      _frame.z + Math.sin(_frame.th) * CHASE.back);
    camera.position.lerp(_chase, 1 - Math.exp(-dt * CHASE.ease));
  }

  perf?.mark('simulation');
  boat.setPose(pose);
  rower.update(pose);
  perf?.mark('animation');

  // blade water events: entry / exit splashes, release puddles
  if (prevBlade > -0.02 && pose.blade <= -0.02) {
    for (const tip of [boat.bladeL, boat.bladeR]) {
      world.fx.splash(bladeWorld(tip), 7, 0.9);
      world.fx.ring(bladeWorld(tip), 0.22, 0.5, 1.0);
    }
  }
  if (prevBlade <= -0.02 && pose.blade > -0.02) {
    for (const tip of [boat.bladeL, boat.bladeR]) {
      world.fx.splash(bladeWorld(tip), 9, 1.15);
      world.fx.ring(bladeWorld(tip), 0.40, 0.7, 1.8); // the puddles
    }
  }
  // drips off the blades early in the recovery
  if (pose.mode === 'rec' && pose.p > 0.05 && pose.p < 0.4) {
    dripT -= dt;
    if (dripT <= 0) {
      dripT = 0.08;
      const tip = Math.random() < 0.5 ? boat.bladeL : boat.bladeR;
      world.fx.splash(bladeWorld(tip), 1, 0.15);
    }
  }
  // gentle bow ripple while moving
  if (stroke.v > 0.8 && Math.random() < dt * 3.5) {
    _w.set(4.0, 0, (Math.random() - 0.5) * 0.3).applyMatrix4(boatGroup.matrix);
    world.fx.ring(_w, 0.18, 0.35 + stroke.v * 0.06, 1.3);
  }

  const caught = pose.mode === 'drive' && prevMode === 'rec';
  if (caught) {
    strokes++;
    if (strokes === 2) elHint.classList.add('dim');
    if (chasePending) { chasePending = false; chaseT = CHASE.dur; }
  }
  prevBlade = pose.blade;
  prevMode = pose.mode;

  world.update(dt, boatGroup.position);
  course.update(dt, stroke.dist, t);

  perf?.mark('world');

  // workout state machine: chime + re-cue on every stage change
  if (workout) {
    const ev = workout.update(dt, stroke.dist, pose.mode === 'drive' && !window.__paused, caught);
    if (ev) onWorkoutEvent(ev);
    if (workout && now >= nextHud) updateWorkoutHud();
  }

  // HUD
  smoothV = lerp(smoothV, stroke.v, 1 - Math.exp(-dt * 1.6));
  if (now >= nextHud) {
    nextHud = now + 100;
    elSplit.textContent = fmtSplit(smoothV);
    elRate.textContent = stroke.spm > 0 ? stroke.spm.toFixed(0) : '––';
    elDist.textContent = `${stroke.dist.toFixed(0)} m`;
  }

  controls.update();
  perf?.mark('hud');
  perf?.beforeRender();
  renderer.render(scene, camera);
  perf?.mark('render');
  perf?.end(now);
}

renderer.setAnimationLoop(tick);
document.addEventListener('visibilitychange', () => {
  last = performance.now();
  renderer.setAnimationLoop(document.hidden ? null : tick);
});

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  resizeResolution();
  renderer.setSize(innerWidth, innerHeight);
});
