import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { World, FOG_COLOR } from './world.js';
import { Course, frame as courseFrame } from './course.js';
import { Boat } from './boat.js';
import { Rower } from './rower.js';
import { Stroke, G } from './stroke.js';
import { Workout } from './workout.js';
import { FTMS } from './ftms.js';
import { Sounds } from './audio.js';
import { clamp, lerp } from './util.js';

// ------------------------------------------------------------ renderer -----
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
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
});

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
const elBead = $('bead'), elHint = $('hint'), elHud = $('hud');
const elOverlay = $('overlay'), elSetup = $('setupCard'), elDone = $('doneCard');
const elGoalStat = $('goalStat'), elGoalLabel = $('goalLabel'), elGoalVal = $('goalVal');
let smoothV = 0, strokes = 0;

function fmtSplit(v) {
  if (v < 0.35) return '–:––';
  return fmtTime(500 / v, 1);
}
function fmtTime(s, dp = 0) {
  s = Math.max(0, s);
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  const ss = dp ? sec.toFixed(dp) : `${Math.floor(sec)}`;
  return `${m}:${sec < 10 ? '0' : ''}${ss}`;
}
// ------------------------------------------------------- goals + overlay ---
const cfg = { mode: 'distance', target: 1000, repeats: 1, rest: 60 };
const TARGETS = {
  distance: [[500, '500 m'], [1000, '1000 m'], [2000, '2000 m'], [5000, '5000 m']],
  time: [[120, '2:00'], [300, '5:00'], [600, '10:00'], [1200, '20:00']],
};
let workout = null;

function buildChips(rowId, list, current, onPick) {
  const box = $(rowId);
  box.innerHTML = '';
  for (const [v, label] of list) {
    const b = document.createElement('button');
    b.textContent = label;
    if (v === current) b.classList.add('sel');
    b.addEventListener('click', () => {
      onPick(v);
      refreshSetup();
    });
    box.appendChild(b);
  }
}

function refreshSetup() {
  buildChips('modeChips', [['just', 'just row'], ['distance', 'distance'], ['time', 'time']],
    cfg.mode, (v) => {
      cfg.mode = v;
      if (v !== 'just' && !TARGETS[v].some(([t]) => t === cfg.target)) cfg.target = TARGETS[v][1][0];
    });
  const goal = cfg.mode !== 'just';
  $('targetRow').hidden = !goal;
  $('repeatRow').hidden = !goal;
  $('restRow').hidden = !goal || cfg.repeats < 2;
  if (goal) {
    buildChips('targetChips', TARGETS[cfg.mode], cfg.target, (v) => { cfg.target = v; });
    buildChips('repeatChips', [[1, '×1'], [2, '×2'], [4, '×4'], [6, '×6']], cfg.repeats, (v) => { cfg.repeats = v; });
    buildChips('restChips', [[30, '0:30'], [60, '1:00'], [120, '2:00']], cfg.rest, (v) => { cfg.rest = v; });
  }
}

function showSetup() {
  refreshSetup();
  elSetup.hidden = false;
  elDone.hidden = true;
  elOverlay.classList.add('show');
  elHud.classList.remove('started');
  elHint.classList.add('gone');
}

function beginWorkout() {
  sounds.ensure();
  stroke.reset();
  course.reset();
  workout = cfg.mode === 'just' ? null : new Workout({ ...cfg });
  workout?.start(0);
  course.setFinish(cfg.mode === 'distance' ? cfg.target : null);
  elOverlay.classList.remove('show');
  elHud.classList.add('started');
  elGoalStat.hidden = cfg.mode === 'just';
  setHint(ftms.connected ? '<span>row on your machine</span>' : '<span>Hold</span><kbd>space</kbd><span>to row</span>');
  strokes = 0;
}

function showSummary() {
  const s = workout.summary();
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

function setHint(html) {
  elHint.innerHTML = html;
  elHint.classList.remove('gone', 'dim');
}

$('begin').addEventListener('click', beginWorkout);
$('again').addEventListener('click', beginWorkout);
$('change').addEventListener('click', showSetup);

// ------------------------------------------------------------- bluetooth ---
const ftms = new FTMS();
const elBt = $('btConnect'), elBtStatus = $('btStatus');
ftms.onStroke = () => { input.queued = true; };
ftms.onChange = () => {
  elBt.textContent = ftms.connected ? 'disconnect' : 'connect monitor';
  elBtStatus.textContent = ftms.connected ? `linked to ${ftms.device?.name || 'rower'}` : '';
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
const _w = new THREE.Vector3();
const _anchor = new THREE.Vector3();
const _delta = new THREE.Vector3();
const _frame = {};

function bladeWorld(tipLocal) {
  return _w.copy(tipLocal).applyMatrix4(boatGroup.matrix);
}

// dev handle for poking the sim from the console
window.__sim = {
  camera, controls, stroke, input, scene, boat, rower, course, world, renderer,
  pause(mode, p) { stroke.mode = mode; stroke.p = p; window.__paused = true; },
  play() { window.__paused = false; },
  step(ms = 16) { last -= ms; tick(); }, // manual frame, e.g. for hidden tabs
};

function tick() {
  const now = performance.now();
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
  const pose = window.__paused ? stroke.pose() : stroke.update(dt, input);

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

  // camera rig translates with the boat; orbit stays user-controlled
  _anchor.set(_frame.x, 0.55, _frame.z);
  _delta.subVectors(_anchor, controls.target);
  controls.target.copy(_anchor);
  camera.position.add(_delta);

  boat.setPose(pose);
  rower.update(pose, boat.handL, boat.handR, t);

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

  if (pose.mode === 'drive' && prevMode === 'rec') {
    strokes++;
    if (strokes === 2) elHint.classList.add('dim');
  }
  prevBlade = pose.blade;
  prevMode = pose.mode;

  world.update(dt, boatGroup.position);
  course.update(dt, stroke.dist, t);

  // workout state machine
  if (workout) {
    const ev = workout.update(dt, stroke.dist, pose.mode === 'drive' && !window.__paused);
    if (ev === 'rest') { sounds.chime(); }
    else if (ev === 'work') {
      sounds.chime();
      setHint('<span>row</span>');
      elHint.classList.add('dim');
      if (cfg.mode === 'distance') course.setFinish(workout.intStart + cfg.target);
    }
    else if (ev === 'done') { sounds.fanfare(); showSummary(); workout = null; }
    if (workout) {
      elGoalLabel.textContent = cfg.repeats > 1
        ? `Goal ${Math.min(workout.interval + 1, cfg.repeats)} of ${cfg.repeats}`
        : 'Goal';
      if (workout.state === 'rest') {
        elGoalVal.textContent = '–';
        setHint(`<span>rest · ${fmtTime(workout.restT)}</span>`);
      } else {
        const rem = workout.remaining(stroke.dist);
        elGoalVal.textContent = cfg.mode === 'time' ? fmtTime(rem) : `${rem.toFixed(0)} m`;
      }
    }
  }

  // HUD
  smoothV = lerp(smoothV, stroke.v, 1 - Math.exp(-dt * 1.6));
  elSplit.textContent = fmtSplit(smoothV);
  elRate.textContent = stroke.spm > 0 ? stroke.spm.toFixed(0) : '––';
  elDist.textContent = `${stroke.dist.toFixed(0)} m`;
  const pct = clamp((pose.seat - G.seatCatch) / (G.seatFinish - G.seatCatch), 0, 1);
  elBead.style.left = `${(1 - pct) * 100}%`;

  controls.update();
  renderer.render(scene, camera);
}

renderer.setAnimationLoop(tick);

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
