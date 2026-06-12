import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { ik2, clamp } from './util.js';
import { G } from './stroke.js';

// The rower is Quaternius' CC0 "Casual" modular woman (quaternius.com),
// posed every frame by retargeting our stroke IK onto her skeleton:
// spine bones take lean/hunch, arms and legs are aimed at the same oar
// handle / foot stretcher targets the procedural figure used.

const HIP_Y = 0.415;          // upper-leg joints sit here when seated
const HIP_X = 0.065;          // hip joints ride this far ahead of seat centre
const PELVIS_TILT = -0.22;    // posterior tilt: tuck the seat bones under
const LEG_REACH = 0.875;      // scale the model so thigh+shin match the boat
const ARM_STRETCH = 1.14;     // lengthen the stubby rig arms to reach the oars
const HAND_LEN = 0.075;       // grip length beyond the wrist
const FOOT_PITCH = -0.88;     // toes-up tilt against the stretcher

const _hip = new THREE.Vector3();
const _ankle = new THREE.Vector3();
const _knee = new THREE.Vector3();
const _foot = new THREE.Vector3();
const _sh = new THREE.Vector3();
const _elbow = new THREE.Vector3();
const _handEnd = new THREE.Vector3();
const _pole = new THREE.Vector3();
const _v = new THREE.Vector3();
const _dw = new THREE.Vector3();
const _bend = new THREE.Vector3();
const _line = new THREE.Vector3();
const _a = new THREE.Vector3();
const _c = new THREE.Vector3();
const _x = new THREE.Vector3();
const _m0 = new THREE.Matrix4();
const _mt = new THREE.Matrix4();
const _qp = new THREE.Quaternion();
const _qi = new THREE.Quaternion();
const _dq = new THREE.Quaternion();
const _qz = new THREE.Quaternion();
const _qBoat = new THREE.Quaternion();
const Z_AXIS = new THREE.Vector3(0, 0, 1);
const POLE_UP = new THREE.Vector3(0.18, 1, 0).normalize();

export class Rower {
  constructor(parent) {
    this.group = new THREE.Group();
    parent.add(this.group);
    this.ready = false;
    new GLTFLoader().load(`${import.meta.env.BASE_URL}models/rower.glb`, (gltf) => this.build(gltf));
  }

  build(gltf) {
    const model = gltf.scene;
    this.bones = {};
    model.traverse((o) => {
      if (o.isBone) this.bones[o.name] = o;
      if (o.isMesh) {
        o.frustumCulled = false; // skinned bounds don't follow the pose
        o.material.metalness = 0;
        o.material.roughness = 0.95;
      }
    });
    const b = this.bones;

    // mount facing the stern (-X); model forward is +Z
    this.mount = new THREE.Group();
    this.mount.rotation.y = -Math.PI / 2;
    this.mount.add(model);
    this.group.add(this.mount);

    // the model loads async, so the boat may already be mid-bob/heading:
    // measure everything boat-local (this.group's frame), not world
    this.group.updateWorldMatrix(true, true);
    this.group.parent.getWorldQuaternion(_qBoat);
    const qBoatInv = _qBoat.clone().invert();
    const local = (bone) => this.group.worldToLocal(bone.getWorldPosition(new THREE.Vector3()));

    // scale so the legs span the seat-to-stretcher geometry
    const hipW = local(b.UpperLegL);
    const kneeW = local(b.LowerLegL);
    const footW = local(b.FootL);
    this.thigh = hipW.distanceTo(kneeW);
    this.shin = kneeW.distanceTo(footW);
    const s = LEG_REACH / (this.thigh + this.shin);
    this.mount.scale.setScalar(s);
    this.thigh *= s;
    this.shin *= s;
    // the rig's arms are short relative to the boat's oar geometry;
    // stretching the bones lengthens (and slightly thickens) the meshes
    b.UpperArmL.scale.setScalar(ARM_STRETCH);
    b.UpperArmR.scale.setScalar(ARM_STRETCH);
    const uaW = local(b.UpperArmL);
    const laW = local(b.LowerArmL);
    const wrW = local(b.WristL);
    this.upperArm = uaW.distanceTo(laW) * s * ARM_STRETCH;
    this.foreArm = laW.distanceTo(wrW) * s * ARM_STRETCH + HAND_LEN;

    // leg-root offset from the Body bone, in boat space, for seating
    this.group.updateWorldMatrix(true, true);
    const bodyW = local(b.Body);
    const legW = local(b.UpperLegL);
    this.legOffX = legW.x - bodyW.x;
    this.legOffY = legW.y - bodyW.y;

    // rest pose snapshots: local quats, child directions (for aiming) and
    // boat-local world quats (for spine/head/foot orientation targets)
    this.rest = {};
    const snap = (name, childName) => {
      const bone = b[name];
      const r = {
        q: bone.quaternion.clone(),
        q0: bone.getWorldQuaternion(new THREE.Quaternion()).premultiply(qBoatInv),
      };
      if (childName) r.dir = b[childName].position.clone().normalize();
      this.rest[name] = r;
    };
    snap('Body'); snap('Hips'); snap('Abdomen', 'Torso'); snap('Torso', 'Chest');
    snap('Chest', 'Neck'); snap('Neck', 'Head'); snap('Head');
    for (const sd of ['L', 'R']) {
      snap(`UpperArm${sd}`, `LowerArm${sd}`);
      snap(`LowerArm${sd}`, `Wrist${sd}`);
      snap(`Wrist${sd}`, `Middle1${sd}`);
      snap(`UpperLeg${sd}`, `LowerLeg${sd}`);
      snap(`LowerLeg${sd}`);
      snap(`Foot${sd}`);
    }
    // the shin bone's "toward ankle" direction: same convention as its parent
    this.rest.LowerLegL.dir = this.rest.UpperLegL.dir;
    this.rest.LowerLegR.dir = this.rest.UpperLegR.dir;

    // bend-reference axes (bone-local): kneecaps face the stern (-X) at
    // rest, elbow points face the bow (+X); aiming keeps them tracking the
    // IK bend plane so limbs can't roll arbitrarily
    for (const sd of ['L', 'R']) {
      for (const [name, axis] of [
        [`UpperLeg${sd}`, [-1, 0, 0]], [`LowerLeg${sd}`, [-1, 0, 0]],
        [`UpperArm${sd}`, [1, 0, 0]], [`LowerArm${sd}`, [1, 0, 0]],
        [`Wrist${sd}`, [0, 1, 0]],  // back of the hand
      ]) {
        const r = this.rest[name];
        r.c0 = new THREE.Vector3(...axis).applyQuaternion(r.q0.clone().invert());
        // orthonormalise against the child axis
        r.c0.addScaledVector(r.dir, -r.c0.dot(r.dir)).normalize();
      }
    }

    // a relaxed grip: curl the fingers around the oar handle
    for (const sd of ['L', 'R']) {
      for (const f of ['Index', 'Middle', 'Ring', 'Pinky']) {
        for (let k = 1; k <= 3; k++) {
          b[`${f}${k}${sd}`]?.rotateX(0.55);
        }
      }
      b[`Thumb2${sd}`]?.rotateX(0.4);
    }

    this.ready = true;
  }

  // orient a bone so its child axis follows dirBoat and its bend-reference
  // axis (kneecap / elbow point) follows bendBoat; both are boat-local
  aim(name, dirBoat, bendBoat) {
    const bone = this.bones[name];
    const r = this.rest[name];
    bone.parent.getWorldQuaternion(_qp);
    _a.copy(dirBoat).normalize();
    _c.copy(bendBoat).addScaledVector(_a, -bendBoat.dot(_a)).normalize();
    _x.crossVectors(_a, _c);
    _mt.makeBasis(_a, _c, _x);
    _x.crossVectors(r.dir, r.c0);
    _m0.makeBasis(r.dir, r.c0, _x);
    // local -> boat-local rotation, then into the parent's frame
    _dq.setFromRotationMatrix(_mt.multiply(_m0.transpose()));
    bone.quaternion.copy(_dq)
      .premultiply(_qBoat)
      .premultiply(_qi.copy(_qp).invert());
    bone.updateWorldMatrix(false, false);
  }

  // bone world quat = boatQuat * zRot(angle) * boat-local rest quat
  setLean(name, angle) {
    const bone = this.bones[name];
    const r = this.rest[name];
    bone.parent.getWorldQuaternion(_qp);
    _qz.setFromAxisAngle(Z_AXIS, angle);
    bone.quaternion.copy(r.q0)
      .premultiply(_qz)
      .premultiply(_qBoat)
      .premultiply(_qi.copy(_qp).invert());
    bone.updateWorldMatrix(false, false);
  }

  boneBoatPos(name, out) {
    return this.group.worldToLocal(this.bones[name].getWorldPosition(out));
  }

  update(pose, handL, handR, time) {
    if (!this.ready) return;
    const b = this.bones;
    const seatX = pose.seat;
    const lean = pose.lean + Math.sin(time * 1.4) * 0.012; // breath
    const ln = clamp((lean - G.leanFinish) / (G.leanCatch - G.leanFinish), 0, 1);
    const hunch = 0.05 + 0.30 * ln * ln;

    // keep this subtree's world matrices in sync with the boat this frame
    this.group.parent.getWorldQuaternion(_qBoat);
    this.group.updateWorldMatrix(true, true);

    // pelvis on the seat: the hip joints ride ahead of the seat centre so
    // the buttocks land on the wood, not in front of it
    _v.set(seatX + HIP_X - this.legOffX, HIP_Y - this.legOffY, 0);
    _v.applyMatrix4(this.group.matrixWorld);
    b.Body.parent.worldToLocal(_v);
    b.Body.position.copy(_v);

    // spine: pelvis takes a share of the lean, the rest rolls up the chain;
    // the hips tuck under (posterior tilt) as anyone seated does
    this.setLean('Body', lean * 0.30);
    this.setLean('Hips', lean * 0.30 + PELVIS_TILT);
    this.setLean('Abdomen', lean * 0.65);
    this.setLean('Torso', lean * 0.95 + hunch * 0.35);
    this.setLean('Chest', lean + hunch);
    this.setLean('Neck', (lean + hunch) * 0.55);
    this.setLean('Head', (lean + hunch) * 0.30);

    for (const sd of [1, -1]) {
      const k = sd > 0 ? 'L' : 'R';
      const hand = sd > 0 ? handL : handR;

      // legs: from wherever the posed pelvis put the hip, drive to the shoes
      this.boneBoatPos(`UpperLeg${k}`, _hip);
      _ankle.set(G.ankle.x, G.ankle.y + 0.02, sd * G.ankle.z);
      ik2(_hip, _ankle, this.thigh, this.shin, POLE_UP, _knee, _foot);
      // kneecaps face out of the hip-ankle line, toward the raised knee
      _line.subVectors(_ankle, _hip).normalize();
      _bend.subVectors(_knee, _hip);
      _bend.addScaledVector(_line, -_bend.dot(_line));
      if (_bend.lengthSq() < 1e-6) _bend.set(-0.3, 1, 0);
      this.aim(`UpperLeg${k}`, _dw.subVectors(_knee, _hip), _bend);
      this.aim(`LowerLeg${k}`, _dw.subVectors(_foot, _knee), _bend);
      // feet planted on the stretcher, toes up
      _v.copy(_ankle).applyMatrix4(this.group.matrixWorld);
      b[`Foot${k}`].parent.worldToLocal(_v);
      b[`Foot${k}`].position.copy(_v);
      this.setLean(`Foot${k}`, FOOT_PITCH);

      // arms: shoulder to oar handle; as the arms fold at the finish the
      // elbows track back past the body, slightly out and down
      this.boneBoatPos(`UpperArm${k}`, _sh);
      _pole.set(0.7, -0.3, sd * 0.8).normalize();
      ik2(_sh, hand, this.upperArm, this.foreArm, _pole, _elbow, _handEnd);
      _line.subVectors(_handEnd, _sh).normalize();
      _bend.subVectors(_elbow, _sh);
      _bend.addScaledVector(_line, -_bend.dot(_line));
      if (_bend.lengthSq() < 1e-6) _bend.set(0.3, -0.5, sd);
      this.aim(`UpperArm${k}`, _dw.subVectors(_elbow, _sh), _bend);
      this.aim(`LowerArm${k}`, _dw.subVectors(_handEnd, _elbow), _bend);
      // hands drape down over the handles, knuckles up
      _line.copy(_dw).normalize();
      _line.y -= 0.7;
      this.aim(`Wrist${k}`, _line, _v.set(0, 1, 0));
    }
  }
}
