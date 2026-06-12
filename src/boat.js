import * as THREE from 'three';
import { mat, makeLimb, setLimb, clamp } from './util.js';
import { G } from './stroke.js';

const COL = {
  hull: 0xe9e2cf,
  gunwale: 0x9a7a55,
  cockpit: 0x4a4238,
  wood: 0xa07c52,
  steel: 0x8a8f93,
  shaft: 0xd6c9a6,
  grip: 0x8a6a48,
  collar: 0x3c3a36,
  blade: 0x5e8f86,
  bladeTip: 0xe9e2cf,
};

const _e = new THREE.Euler();
const _q = new THREE.Quaternion();
const _v = new THREE.Vector3();

function tube(parent, a, b, r, material) {
  const m = makeLimb(parent, r, r, material, 6);
  setLimb(m, a, b);
  return m;
}

function makeHull(group) {
  const len = 8.3;
  const geo = new THREE.BoxGeometry(len, 0.26, 0.40, 16, 1, 1);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const t = Math.abs(x) / (len / 2);
    const p = Math.pow(Math.max(1 - t * t, 0), 0.8) * 0.94 + 0.06;
    // taper plan-form toward the ends, pinch the bottom into a shallow V,
    // and lift the keel line at bow/stern
    pos.setZ(i, z * p * (y < 0 ? 0.5 : 1));
    if (y < 0) pos.setY(i, y * (0.35 + 0.65 * p));
  }
  geo.computeVertexNormals();
  const hull = new THREE.Mesh(geo, mat(COL.hull));
  hull.position.y = 0.095;
  group.add(hull);

  // cockpit inset
  const pit = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.02, 0.24), mat(COL.cockpit));
  pit.position.set(0.05, 0.222, 0);
  group.add(pit);

  // gunwale strips along the cockpit
  for (const s of [-1, 1]) {
    const gw = new THREE.Mesh(new THREE.BoxGeometry(2.1, 0.035, 0.035), mat(COL.gunwale));
    gw.position.set(0.05, 0.235, s * 0.145);
    group.add(gw);
  }

  // bow ball + stern fin
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.035, 6, 5), mat(0xf2efe4));
  ball.position.set(len / 2 + 0.02, 0.16, 0);
  group.add(ball);
  const fin = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.16, 0.012), mat(COL.steel));
  fin.position.set(-2.9, -0.05, 0);
  group.add(fin);
}

function makeRiggers(group) {
  const m = mat(COL.steel, { roughness: 0.6 });
  for (const s of [-1, 1]) {
    const pin = new THREE.Vector3(G.pinX, G.pinY, s * G.pinZ);
    tube(group, new THREE.Vector3(G.pinX - 0.5, 0.21, s * 0.13), pin, 0.014, m);
    tube(group, new THREE.Vector3(G.pinX + 0.45, 0.21, s * 0.13), pin, 0.014, m);
    tube(group, new THREE.Vector3(G.pinX, 0.16, s * 0.14), new THREE.Vector3(G.pinX, G.pinY - 0.02, s * G.pinZ), 0.011, m);
    // oarlock post
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.10, 6), m);
    post.position.copy(pin).y += 0.03;
    group.add(post);
  }
}

function makeSeatAndStretcher(group) {
  // slide rails
  for (const s of [-1, 1]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.018, 0.02), mat(COL.steel, { roughness: 0.55 }));
    rail.position.set(0.13, 0.245, s * 0.05);
    group.add(rail);
  }
  // seat (animated in x)
  const seat = new THREE.Group();
  const top = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.035, 0.30), mat(COL.wood));
  top.position.y = 0.30;
  seat.add(top);
  const wheels = [];
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    const w = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.026, 0.02, 8), mat(COL.collar));
    w.rotation.x = Math.PI / 2;
    w.position.set(sx * 0.10, 0.262, sz * 0.05);
    seat.add(w);
    wheels.push(w);
  }
  group.add(seat);

  // foot stretcher: the board's top leans away from the rower (sternward),
  // soles toward them; shoes lie flush on the board face, toes up
  const st = new THREE.Group();
  const board = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.24, 0.30), mat(COL.wood));
  board.position.set(-0.56, 0.21, 0);
  board.rotation.z = 0.65;
  st.add(board);
  const beam = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.06, 0.30), mat(COL.gunwale));
  beam.position.set(-0.48, 0.20, 0);
  st.add(beam);
  for (const s of [-1, 1]) {
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.20, 0.055, 0.085), mat(0x6b4a33));
    shoe.position.set(G.ankle.x - 0.062, G.ankle.y + 0.016, s * G.ankle.z);
    shoe.rotation.z = -(Math.PI / 2 - 0.65);
    st.add(shoe);
  }
  group.add(st);

  return { seat, wheels };
}

function makeOar(side) {
  // side +1 -> pin at z = +pinZ. Local +Z always points outboard;
  // group euler order YXZ gives sweep (y) then blade-depth pitch (x).
  const g = new THREE.Group();
  g.position.set(G.pinX, G.pinY, side * G.pinZ);
  g.rotation.order = 'YXZ';

  const shaftLen = G.inboard + 1.66;
  const shaftGeo = new THREE.CylinderGeometry(0.021, 0.024, shaftLen, 6);
  shaftGeo.rotateX(Math.PI / 2);
  shaftGeo.translate(0, 0, shaftLen / 2 - G.inboard);
  const shaft = new THREE.Mesh(shaftGeo, mat(COL.shaft));
  g.add(shaft);

  const gripGeo = new THREE.CylinderGeometry(0.028, 0.028, 0.30, 6);
  gripGeo.rotateX(Math.PI / 2);
  gripGeo.translate(0, 0, -G.inboard + 0.15);
  g.add(new THREE.Mesh(gripGeo, mat(COL.grip)));

  const collarGeo = new THREE.CylinderGeometry(0.036, 0.036, 0.10, 6);
  collarGeo.rotateX(Math.PI / 2);
  collarGeo.translate(0, 0, -0.02);
  g.add(new THREE.Mesh(collarGeo, mat(COL.collar)));

  // blade, hung at its root so feathering rotates about the shaft axis
  const blade = new THREE.Group();
  blade.position.z = G.outboard - 0.44;
  const b1 = new THREE.Mesh(new THREE.BoxGeometry(0.016, 0.19, 0.24), mat(COL.blade));
  b1.position.set(0.0, -0.02, 0.11);
  blade.add(b1);
  const b2 = new THREE.Mesh(new THREE.BoxGeometry(0.016, 0.22, 0.24), mat(COL.blade));
  b2.position.set(0.015, -0.025, 0.33);
  b2.rotation.y = 0.10 * side;
  blade.add(b2);
  const tip = new THREE.Mesh(new THREE.BoxGeometry(0.018, 0.22, 0.05), mat(COL.bladeTip));
  tip.position.set(0.02, -0.025, 0.455);
  blade.add(tip);
  g.add(blade);

  return { group: g, blade, side };
}

export class Boat {
  constructor(parent) {
    this.group = new THREE.Group();
    parent.add(this.group);

    makeHull(this.group);
    makeRiggers(this.group);
    const { seat, wheels } = makeSeatAndStretcher(this.group);
    this.seat = seat;
    this.wheels = wheels;

    this.oarL = makeOar(-1);
    this.oarR = makeOar(1);
    this.group.add(this.oarL.group, this.oarR.group);

    // boat-local attachment points, recomputed each frame
    this.handL = new THREE.Vector3();
    this.handR = new THREE.Vector3();
    this.bladeL = new THREE.Vector3();
    this.bladeR = new THREE.Vector3();
  }

  setPose(pose) {
    // seat slide + wheel spin
    const prevX = this.seat.position.x;
    this.seat.position.x = pose.seat;
    const spin = (pose.seat - prevX) / 0.026;
    for (const w of this.wheels) w.rotation.y += spin; // local y = world z after rotation.x

    const phi = pose.oar;
    const pitch = Math.asin(clamp((G.pinY - pose.blade) / 1.9, -0.6, 0.6));

    for (const oar of [this.oarL, this.oarR]) {
      const yRot = oar.side > 0 ? phi : Math.PI - phi;
      oar.group.rotation.set(pitch, yRot, 0);
      oar.blade.rotation.z = oar.side * pose.feather * 1.42;

      _e.set(pitch, yRot, 0, 'YXZ');
      _q.setFromEuler(_e);
      // rower faces -X, so the +Z pin is their left side
      const hand = oar.side > 0 ? this.handL : this.handR;
      hand.set(0, 0.035, -(G.inboard - 0.07)).applyQuaternion(_q).add(oar.group.position);
      const tip = oar.side > 0 ? this.bladeL : this.bladeR;
      tip.set(0, 0, G.outboard - 0.10).applyQuaternion(_q).add(oar.group.position);
    }

    // sculling crossover: hands overlap mid-stroke, left rides over right
    const w = Math.max(0, 1 - Math.abs(phi) / 0.5);
    const lift = w * w;
    this.handL.y += 0.055 * lift; // +z side is the rower's left
    this.handR.y -= 0.012 * lift;
  }
}
