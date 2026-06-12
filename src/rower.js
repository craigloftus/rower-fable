import * as THREE from 'three';
import { mat, makeLimb, setLimb, ik2, clamp } from './util.js';
import { G } from './stroke.js';

const COL = {
  skin: 0xd9a878,
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

export class Rower {
  constructor(parent) {
    const g = new THREE.Group();
    parent.add(g);
    this.group = g;

    const skin = mat(COL.skin);
    const shirt = mat(COL.shirt);
    const trouser = mat(COL.trouser);

    // pelvis sits on the seat
    this.pelvis = new THREE.Mesh(new THREE.BoxGeometry(0.20, 0.13, 0.30), trouser);
    g.add(this.pelvis);

    // torso: lower segment pivots at the hip, chest segment adds hunch
    this.torso = new THREE.Group();
    g.add(this.torso);
    const lower = new THREE.Mesh(new THREE.BoxGeometry(0.19, 0.28, 0.29), shirt);
    lower.position.y = 0.14;
    this.torso.add(lower);
    const belt = new THREE.Mesh(new THREE.BoxGeometry(0.21, 0.06, 0.31), mat(COL.belt));
    belt.position.y = 0.015;
    this.torso.add(belt);

    this.chestG = new THREE.Group();
    this.chestG.position.y = 0.26;
    this.torso.add(this.chestG);
    const chest = new THREE.Mesh(new THREE.BoxGeometry(0.21, 0.30, 0.35), shirt);
    chest.position.y = 0.135;
    this.chestG.add(chest);
    // satchel strap, a nod to the reference image
    const strap = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.34, 0.06), mat(COL.strap));
    strap.position.set(-0.108, 0.13, 0.02);
    strap.rotation.x = 0.6;
    this.chestG.add(strap);

    // head group counter-rotates to keep the gaze level
    this.headG = new THREE.Group();
    this.headG.position.y = 0.30;
    this.chestG.add(this.headG);
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.05, 0.09, 6), skin);
    neck.position.y = 0.035;
    this.headG.add(neck);
    const head = new THREE.Mesh(new THREE.IcosahedronGeometry(0.105, 1), skin);
    head.position.y = 0.155;
    this.headG.add(head);
    const hair = new THREE.Mesh(new THREE.IcosahedronGeometry(0.108, 1), mat(COL.hair));
    hair.position.set(0.028, 0.19, 0);
    hair.scale.set(1, 0.82, 1);
    this.headG.add(hair);
    const tail = new THREE.Mesh(new THREE.IcosahedronGeometry(0.045, 0), mat(COL.hair));
    tail.position.set(0.115, 0.10, 0);
    this.headG.add(tail);
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.013, 5, 4), mat(COL.dark, { roughness: 0.4 }));
      eye.position.set(-0.092, 0.155, s * 0.042);
      this.headG.add(eye);
    }

    // limbs (stretched between IK joints every frame)
    this.parts = {};
    for (const side of ['L', 'R']) {
      this.parts['thigh' + side] = makeLimb(g, 0.062, 0.052, trouser);
      this.parts['shin' + side] = makeLimb(g, 0.05, 0.042, trouser);
      this.parts['knee' + side] = ball(g, 0.06, trouser);
      this.parts['uarm' + side] = makeLimb(g, 0.048, 0.042, shirt);
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
