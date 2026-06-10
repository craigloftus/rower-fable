import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { World, FOG_COLOR } from './world.js';
import { Boat } from './boat.js';
import { Rower } from './rower.js';
import { Stroke, G } from './stroke.js';
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
camera.position.set(10, 4.5, 14);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0.2, 0.55, 0);
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
const world = new World(scene);

const boatGroup = new THREE.Group();
scene.add(boatGroup);
const boat = new Boat(boatGroup);
const rower = new Rower(boatGroup);

// soft contact shadow under the hull
const shadow = new THREE.Mesh(
  new THREE.CircleGeometry(1, 24),
  new THREE.MeshBasicMaterial({ color: 0x1c3a40, transparent: true, opacity: 0.16, depthWrite: false }));
shadow.rotation.x = -Math.PI / 2;
shadow.scale.set(4.4, 0.55, 1);
shadow.position.y = 0.035;
scene.add(shadow);

const stroke = new Stroke();
const input = { held: false, queued: false };

// -------------------------------------------------------------- input ------
addEventListener('keydown', (e) => {
  if (e.code === 'Space') {
    e.preventDefault();
    if (!e.repeat) { input.held = true; input.queued = true; }
  } else if (e.code === 'KeyR') {
    stroke.reset();
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
const elBead = $('bead'), elHint = $('hint');
let smoothV = 0, strokes = 0;

function fmtSplit(v) {
  if (v < 0.35) return '–:––';
  const s = 500 / v;
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  return `${m}:${sec < 10 ? '0' : ''}${sec.toFixed(1)}`;
}

// ------------------------------------------------------------ fly-in -------
const camFrom = camera.position.clone();
const camTo = new THREE.Vector3(3.9, 2.1, 7.3);
let introT = 0, introDone = false;
renderer.domElement.addEventListener('pointerdown', () => { introDone = true; }, { once: true });

// --------------------------------------------------------------- loop ------
let last = performance.now();
let prevBlade = 0.2, prevMode = 'rec', dripT = 0;
const _w = new THREE.Vector3();

function bladeWorld(tipLocal) {
  return _w.copy(tipLocal).applyMatrix4(boatGroup.matrix);
}

// dev handle for poking the sim from the console
window.__sim = {
  camera, controls, stroke, input, scene, boat, rower,
  pause(mode, p) { stroke.mode = mode; stroke.p = p; window.__paused = true; },
  play() { window.__paused = false; },
};

renderer.setAnimationLoop(() => {
  const now = performance.now();
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  const t = now / 1000;

  if (!introDone) {
    introT = Math.min(introT + dt / 3.2, 1);
    const e = 1 - Math.pow(1 - introT, 3);
    camera.position.lerpVectors(camFrom, camTo, e);
    if (introT >= 1) introDone = true;
  }

  // dev: window.__sim.pause('drive', 0.5) freezes the cycle for inspection
  const pose = window.__paused ? stroke.pose() : stroke.update(dt, input);

  // hull secondary motion: bob, stroke pitch (bow up when mass is sternward)
  const c = (G.seatFinish - pose.seat) / (G.seatFinish - G.seatCatch); // 1 at catch
  boatGroup.position.y = 0.02 * Math.sin(t * 1.1) + 0.012 * Math.sin(t * 1.7) - 0.012 * pose.thrust;
  boatGroup.rotation.z = 0.012 * Math.sin(t * 0.9) + lerp(-0.008, 0.010, c);
  boatGroup.rotation.x = 0.010 * Math.sin(t * 0.74) + (pose.mode === 'rec' ? 0.006 * Math.sin(t * 3.1) : 0);
  boatGroup.updateMatrix();

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
    _w.set(4.0, 0, (Math.random() - 0.5) * 0.3);
    world.fx.ring(_w, 0.18, 0.35 + stroke.v * 0.06, 1.3);
  }

  if (pose.mode === 'drive' && prevMode === 'rec') {
    strokes++;
    if (strokes === 2) elHint.classList.add('dim');
  }
  prevBlade = pose.blade;
  prevMode = pose.mode;

  world.update(dt, stroke.dist, stroke.v);

  // HUD
  smoothV = lerp(smoothV, stroke.v, 1 - Math.exp(-dt * 1.6));
  elSplit.textContent = fmtSplit(smoothV);
  elRate.textContent = stroke.spm > 0 ? stroke.spm.toFixed(0) : '––';
  elDist.textContent = `${stroke.dist.toFixed(0)} m`;
  const pct = clamp((pose.seat - G.seatCatch) / (G.seatFinish - G.seatCatch), 0, 1);
  elBead.style.left = `${(1 - pct) * 100}%`;

  controls.update();
  renderer.render(scene, camera);
});

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
