import * as THREE from 'three';
import { mat, makeLimb, setLimb, ik2, clamp, rng } from './util.js';
import { jitterGeo } from './scenery.js';
import { G } from './stroke.js';

const COL = {
  skin: 0xd9a878,
  skinShade: 0xb9855f,
  shirt: 0xe6deca,
  trouser: 0x6e6553,
  hair: 0xc9a14e,
  belt: 0x5a4632,
  strap: 0x7a5f48,
  dark: 0x3a352c,
};

const _hip = new THREE.Vector3();
const _ankle = new THREE.Vector3();
const _knee = new THREE.Vector3();
const _foot = new THREE.Vector3();
const _sh = new THREE.Vector3();
const _elbow = new THREE.Vector3();
const _handEnd = new THREE.Vector3();
const _pole = new THREE.Vector3();
const POLE_UP = new THREE.Vector3(0.18, 1, 0).normalize();

function ball(parent, r, material) {
  const m = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), material);
  parent.add(m);
  return m;
}

// ------------------------------------------------------- ring modelling ----
// A body part is described by horizontal "edge loops" (front toward -X):
// { y, xF (front), xB (back), w (half width) }. Each loop becomes 8 points
// and consecutive loops are skinned with quads; flat shading does the rest.
const ST_X = [0, 0.26, 0.55, 0.82, 1];   // front-to-back blend per station
const ST_Z = [0, 0.80, 1, 0.86, 0];      // width factor per station

function ringPoints(rg) {
  const pts = [];
  for (let i = 0; i < 8; i++) {
    const st = i <= 4 ? i : 8 - i;
    pts.push(new THREE.Vector3(
      rg.xF + (rg.xB - rg.xF) * ST_X[st],
      rg.y,
      (i <= 4 ? 1 : -1) * rg.w * ST_Z[st]));
  }
  return pts;
}

function ringsMesh(parent, rings, material, jitter = 0) {
  const loops = rings.map(ringPoints);
  if (jitter) {
    const r = rng(5511);
    for (const lp of loops) {
      for (let i = 0; i < 8; i++) {
        // mirror the jitter so the face stays symmetric
        if (i > 4) continue;
        const dx = (r() - 0.5) * jitter, dy = (r() - 0.5) * jitter, dz = (r() - 0.5) * jitter;
        lp[i].x += dx; lp[i].y += dy;
        if (i > 0 && i < 4) {
          lp[i].z += dz;
          lp[8 - i].set(lp[i].x, lp[i].y, -lp[i].z);
        }
      }
    }
  }
  const pos = [];
  const tri = (a, b, c) => pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
  for (let rI = 0; rI < loops.length - 1; rI++) {
    const lo = loops[rI], hi = loops[rI + 1];
    for (let i = 0; i < 8; i++) {
      const j = (i + 1) % 8;
      tri(lo[i], lo[j], hi[j]);
      tri(lo[i], hi[j], hi[i]);
    }
  }
  // caps
  const bot = loops[0], top = loops[loops.length - 1];
  const bc = bot.reduce((v, p) => v.add(p), new THREE.Vector3()).multiplyScalar(1 / 8);
  const tc = top.reduce((v, p) => v.add(p), new THREE.Vector3()).multiplyScalar(1 / 8);
  for (let i = 0; i < 8; i++) {
    const j = (i + 1) % 8;
    tri(bot[j], bot[i], bc);
    tri(top[i], top[j], tc);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, material);
  parent.add(m);
  return m;
}

// ----------------------------------------------------------------- head ----
// loops from chin to crown carve the jaw, cheekbones, brow ledge and skull
const HEAD_RINGS = [
  { y: 0.054, xF: -0.042, xB: 0.028, w: 0.022 },  // under the chin
  { y: 0.070, xF: -0.070, xB: 0.058, w: 0.052 },  // jaw line
  { y: 0.102, xF: -0.070, xB: 0.084, w: 0.068 },  // mouth / lower cheeks
  { y: 0.138, xF: -0.066, xB: 0.096, w: 0.082 },  // cheekbones
  { y: 0.162, xF: -0.061, xB: 0.098, w: 0.080 },  // eye line, recessed socket
  { y: 0.186, xF: -0.080, xB: 0.098, w: 0.078 },  // brow ledge overhang
  { y: 0.216, xF: -0.066, xB: 0.094, w: 0.071 },  // forehead
  { y: 0.244, xF: -0.030, xB: 0.068, w: 0.048 },  // crown
  { y: 0.258, xF: 0.002, xB: 0.036, w: 0.020 },   // apex
];

// hair: a close-fitting base cap; chunky swept strands are added on top
const HAIR_RINGS = [
  { y: 0.140, xF: -0.020, xB: 0.114, w: 0.090 },  // down over the ears
  { y: 0.208, xF: -0.076, xB: 0.114, w: 0.086 },  // fringe above the brow
  { y: 0.250, xF: -0.058, xB: 0.106, w: 0.074 },
  { y: 0.286, xF: -0.004, xB: 0.066, w: 0.040 },
];

// angular tufts laid over the cap give the irregular low-poly silhouette:
// a quiff swept up off the brow, side sweeps, and a mass feeding the bun
const HAIR_TUFTS = [
  // [x, y, z,  sx, sy, sz,  rx, ry, rz]
  [-0.055, 0.262, 0.014, 0.052, 0.034, 0.046, 0.2, 0.3, 0.5],
  [-0.062, 0.240, -0.030, 0.046, 0.030, 0.042, -0.3, -0.4, 0.6],
  [-0.012, 0.282, -0.008, 0.058, 0.034, 0.054, 0.1, 1.1, 0.15],
  [0.020, 0.276, 0.040, 0.048, 0.030, 0.044, 0.5, 0.6, -0.2],
  [0.030, 0.272, -0.044, 0.050, 0.028, 0.046, -0.4, 0.2, -0.25],
  [-0.044, 0.184, 0.080, 0.034, 0.050, 0.030, 0.2, 0.4, 0.3],   // temple sweep
  [-0.044, 0.184, -0.080, 0.034, 0.050, 0.030, -0.2, -0.4, 0.3],
  [-0.060, 0.222, 0.052, 0.034, 0.026, 0.032, 0.3, 0.5, 0.4],   // fringe corners
  [-0.060, 0.222, -0.052, 0.034, 0.026, 0.032, -0.3, -0.5, 0.4],
  [0.082, 0.252, 0.030, 0.052, 0.034, 0.050, 0.3, -0.5, -0.3],  // back mass
  [0.086, 0.248, -0.036, 0.050, 0.032, 0.048, -0.3, 0.7, 0.2],
  [0.108, 0.226, 0.000, 0.044, 0.036, 0.044, 0.1, 0.9, -0.4],
];

function makeNose(parent, material) {
  const v = {
    bridge: [-0.076, 0.184, 0],
    bL: [-0.062, 0.178, 0.016], bR: [-0.062, 0.178, -0.016],
    tip: [-0.104, 0.120, 0],
    baL: [-0.056, 0.102, 0.020], baR: [-0.056, 0.102, -0.020],
    base: [-0.064, 0.098, 0],
  };
  const pos = [];
  const tri = (a, b, c) => pos.push(...v[a], ...v[b], ...v[c]);
  tri('bridge', 'tip', 'bL');
  tri('bridge', 'bR', 'tip');
  tri('bL', 'tip', 'baL');
  tri('bR', 'baR', 'tip');
  tri('tip', 'base', 'baL');
  tri('tip', 'baR', 'base');
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, material);
  parent.add(m);
  return m;
}

// ---------------------------------------------------------------- torso ----
const LOWER_RINGS = [
  { y: -0.005, xF: -0.104, xB: 0.104, w: 0.150 }, // hips at the belt
  { y: 0.110, xF: -0.090, xB: 0.090, w: 0.128 },  // waist
  { y: 0.270, xF: -0.099, xB: 0.099, w: 0.149 },  // lower ribs
];
const CHEST_RINGS = [
  { y: 0.000, xF: -0.098, xB: 0.098, w: 0.148 },  // joins the lower torso
  { y: 0.115, xF: -0.108, xB: 0.106, w: 0.176 },  // chest
  { y: 0.225, xF: -0.094, xB: 0.096, w: 0.190 },  // shoulder line
  { y: 0.272, xF: -0.078, xB: 0.082, w: 0.142 },  // trapezius mass
  { y: 0.312, xF: -0.048, xB: 0.054, w: 0.072 },  // neck base
];

export class Rower {
  constructor(parent) {
    const g = new THREE.Group();
    parent.add(g);
    this.group = g;

    const skin = mat(COL.skin);
    const shirt = mat(COL.shirt);
    const trouser = mat(COL.trouser);
    const hairM = mat(COL.hair);

    // pelvis sits on the seat
    this.pelvis = new THREE.Mesh(new THREE.BoxGeometry(0.20, 0.13, 0.30), trouser);
    g.add(this.pelvis);

    // torso: lower segment pivots at the hip, chest segment adds hunch
    this.torso = new THREE.Group();
    g.add(this.torso);
    ringsMesh(this.torso, LOWER_RINGS, shirt);
    const belt = new THREE.Mesh(new THREE.BoxGeometry(0.205, 0.06, 0.305), mat(COL.belt));
    belt.position.y = 0.015;
    this.torso.add(belt);

    this.chestG = new THREE.Group();
    this.chestG.position.y = 0.26;
    this.torso.add(this.chestG);
    ringsMesh(this.chestG, CHEST_RINGS, shirt);
    // satchel strap, a nod to the reference image
    const strap = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.36, 0.06), mat(COL.strap));
    strap.position.set(-0.115, 0.13, 0.02);
    strap.rotation.x = 0.6;
    this.chestG.add(strap);

    // head group counter-rotates to keep the gaze level
    this.headG = new THREE.Group();
    this.headG.position.y = 0.30;
    this.chestG.add(this.headG);
    // collar at the neck base
    const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.072, 0.082, 0.034, 8), mat(0xd6ccb2));
    collar.position.y = 0.318;
    this.chestG.add(collar);

    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.050, 0.064, 0.09, 7), skin);
    neck.position.y = 0.025;
    this.headG.add(neck);

    ringsMesh(this.headG, HEAD_RINGS, skin, 0.006);
    makeNose(this.headG, skin);
    ringsMesh(this.headG, HAIR_RINGS, hairM, 0.010);
    // chunky strands over the cap
    const tuftR = rng(909);
    for (const [x, y, z, sx, sy, sz, rx, ry, rz] of HAIR_TUFTS) {
      const tuft = new THREE.Mesh(jitterGeo(new THREE.IcosahedronGeometry(1, 0), tuftR, 0.35), hairM);
      tuft.scale.set(sx, sy, sz);
      tuft.position.set(x, y, z);
      tuft.rotation.set(rx, ry, rz);
      this.headG.add(tuft);
    }
    // bun at the back
    const bun = new THREE.Mesh(new THREE.IcosahedronGeometry(0.044, 0), hairM);
    bun.position.set(0.126, 0.216, 0);
    this.headG.add(bun);
    const wisp = new THREE.Mesh(new THREE.IcosahedronGeometry(0.024, 0), hairM);
    wisp.position.set(0.130, 0.168, 0);
    this.headG.add(wisp);

    // eyes set into the sockets under the brow, heavier brows, mouth hint
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.0130, 6, 5), mat(COL.dark, { roughness: 0.35 }));
      eye.position.set(-0.0560, 0.162, s * 0.034);
      this.headG.add(eye);
      const brow = new THREE.Mesh(new THREE.BoxGeometry(0.011, 0.009, 0.031), mat(0x8a6a36));
      brow.position.set(-0.0745, 0.190, s * 0.030);
      brow.rotation.x = s * 0.10;
      brow.rotation.y = -s * 0.15;
      this.headG.add(brow);
    }
    const mouth = new THREE.Mesh(new THREE.BoxGeometry(0.006, 0.0045, 0.030), mat(COL.skinShade));
    mouth.position.set(-0.0665, 0.080, 0);
    this.headG.add(mouth);

    // limbs (stretched between IK joints every frame)
    this.parts = {};
    for (const side of ['L', 'R']) {
      this.parts['thigh' + side] = makeLimb(g, 0.062, 0.052, trouser);
      this.parts['shin' + side] = makeLimb(g, 0.05, 0.042, trouser);
      this.parts['knee' + side] = ball(g, 0.06, trouser);
      this.parts['uarm' + side] = makeLimb(g, 0.058, 0.042, shirt);
      this.parts['farm' + side] = makeLimb(g, 0.04, 0.034, skin);
      this.parts['elbow' + side] = ball(g, 0.046, skin);
      this.parts['hand' + side] = ball(g, 0.048, skin);
    }
  }

  update(pose, handL, handR, time) {
    const seatX = pose.seat;
    const lean = pose.lean + Math.sin(time * 1.4) * 0.012; // breath
    const ln = clamp((lean - G.leanFinish) / (G.leanCatch - G.leanFinish), 0, 1);
    const hunch = 0.05 + 0.30 * ln * ln;

    this.pelvis.position.set(seatX, 0.385, 0);
    this.torso.position.set(seatX, G.hipY, 0);
    this.torso.rotation.z = lean;
    this.chestG.rotation.z = hunch;
    this.headG.rotation.z = -(lean + hunch) * 0.55;

    // shoulder anchors via the same 2D rotations as the torso meshes
    const lt = lean + hunch;
    const shX = seatX - Math.sin(lean) * 0.26 - Math.sin(lt) * 0.27;
    const shY = G.hipY + Math.cos(lean) * 0.26 + Math.cos(lt) * 0.27;

    for (const side of [1, -1]) {
      const k = side > 0 ? 'L' : 'R';
      const hand = side > 0 ? handL : handR;

      // legs: hip on the seat, ankle strapped into the stretcher shoes
      _hip.set(seatX - 0.03, G.hipY - 0.02, side * 0.105);
      _ankle.set(G.ankle.x, G.ankle.y, side * G.ankle.z);
      ik2(_hip, _ankle, G.thigh, G.shin, POLE_UP, _knee, _foot);
      setLimb(this.parts['thigh' + k], _hip, _knee);
      setLimb(this.parts['shin' + k], _knee, _foot);
      this.parts['knee' + k].position.copy(_knee);

      // arms: shoulder to oar handle, elbows bend out / back / slightly down
      _sh.set(shX, shY, side * 0.185);
      _pole.set(0.55, -0.35, side * 1.0).normalize();
      ik2(_sh, hand, G.upperArm, G.foreArm, _pole, _elbow, _handEnd);
      setLimb(this.parts['uarm' + k], _sh, _elbow);
      setLimb(this.parts['farm' + k], _elbow, _handEnd);
      this.parts['elbow' + k].position.copy(_elbow);
      this.parts['hand' + k].position.copy(_handEnd);
    }
  }
}
