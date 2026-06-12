import * as THREE from 'three';
import { mat, makeLimb, setLimb, ik2, clamp, rng } from './util.js';
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
  { y: 0.054, xF: -0.040, xB: 0.028, w: 0.020 },  // under the chin
  { y: 0.072, xF: -0.068, xB: 0.058, w: 0.050 },  // jaw line
  { y: 0.108, xF: -0.068, xB: 0.084, w: 0.066 },  // mouth / lower cheeks
  { y: 0.144, xF: -0.065, xB: 0.096, w: 0.079 },  // cheekbones
  { y: 0.176, xF: -0.072, xB: 0.098, w: 0.076 },  // brow ledge
  { y: 0.210, xF: -0.059, xB: 0.094, w: 0.070 },  // forehead
  { y: 0.240, xF: -0.028, xB: 0.068, w: 0.048 },  // crown
  { y: 0.254, xF: 0.002, xB: 0.036, w: 0.020 },   // apex
];

// angular swept-back hair shell sitting just proud of the skull
const HAIR_RINGS = [
  { y: 0.132, xF: -0.024, xB: 0.112, w: 0.088 },  // down over the ears
  { y: 0.202, xF: -0.078, xB: 0.112, w: 0.086 },  // fringe above the brow
  { y: 0.242, xF: -0.058, xB: 0.106, w: 0.075 },
  { y: 0.284, xF: -0.004, xB: 0.066, w: 0.040 },
];

function makeNose(parent, material) {
  const v = {
    bridge: [-0.067, 0.186, 0],
    bL: [-0.058, 0.182, 0.014], bR: [-0.058, 0.182, -0.014],
    tip: [-0.099, 0.124, 0],
    baL: [-0.054, 0.106, 0.018], baR: [-0.054, 0.106, -0.018],
    base: [-0.062, 0.102, 0],
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
  { y: 0.120, xF: -0.108, xB: 0.106, w: 0.172 },  // chest
  { y: 0.230, xF: -0.092, xB: 0.094, w: 0.184 },  // shoulder line
  { y: 0.305, xF: -0.054, xB: 0.058, w: 0.082 },  // trapezius slope to neck
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
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.060, 0.11, 7), skin);
    neck.position.y = 0.030;
    this.headG.add(neck);

    ringsMesh(this.headG, HEAD_RINGS, skin, 0.006);
    makeNose(this.headG, skin);
    ringsMesh(this.headG, HAIR_RINGS, hairM, 0.010);
    // bun at the back
    const bun = new THREE.Mesh(new THREE.IcosahedronGeometry(0.042, 0), hairM);
    bun.position.set(0.118, 0.212, 0);
    this.headG.add(bun);
    const wisp = new THREE.Mesh(new THREE.IcosahedronGeometry(0.024, 0), hairM);
    wisp.position.set(0.124, 0.166, 0);
    this.headG.add(wisp);

    // eyes, brows and a hint of mouth
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.0105, 5, 4), mat(COL.dark, { roughness: 0.4 }));
      eye.position.set(-0.0635, 0.160, s * 0.033);
      this.headG.add(eye);
      const brow = new THREE.Mesh(new THREE.BoxGeometry(0.010, 0.0075, 0.036), mat(0xa07b3e));
      brow.position.set(-0.0685, 0.183, s * 0.034);
      brow.rotation.x = s * 0.14;
      this.headG.add(brow);
    }
    const mouth = new THREE.Mesh(new THREE.BoxGeometry(0.006, 0.004, 0.028), mat(COL.skinShade));
    mouth.position.set(-0.066, 0.084, 0);
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
