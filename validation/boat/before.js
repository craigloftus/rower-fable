import * as THREE from 'three';
import { mat, makeLimb, setLimb } from '../../src/util.js';
import { G } from '../../src/stroke.js';
import { oarPose } from '../../src/oar-pose.js';

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
  const riggers = [];
  for (const s of [-1, 1]) {
    const pin = new THREE.Vector3(G.pinX, G.pinY, s * G.pinZ);
    const struts = [[-.5,.21,.13,0,.014],[.45,.21,.13,0,.014],[0,.16,.14,-.02,.011]].map(([x,y,z,dy,r])=>{
      const base=new THREE.Vector3(G.pinX+x,y,s*z),end=pin.clone();end.y+=dy;
      return { base, end, dy, mesh:tube(group,base,end,r,m) };
    });
    // oarlock post
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.10, 6), m);
    post.position.copy(pin).y += 0.03;
    group.add(post);
    riggers.push({post,struts});
  }
  let height=G.pinY;
  return pinY=>{
    if(pinY===height)return;
    height=pinY;
    for(const {post,struts} of riggers){
      post.position.y=pinY+.03;
      for(const {mesh,base,end,dy} of struts){end.y=pinY+dy;setLimb(mesh,base,end);}
    }
  };
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
  const top = new THREE.Mesh(new THREE.BoxGeometry(G.seat.length, G.seat.thickness, G.seat.width), mat(COL.wood));
  top.position.y = G.seat.top - G.seat.thickness / 2;
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
  // soles toward them; the rower's own shoes rest against it
  const st = new THREE.Group();
  const board = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.32, 0.36), mat(COL.wood));
  board.position.set(-0.551, 0.245, 0);
  board.rotation.z = Math.atan2(0.10, 0.14);
  st.add(board);
  const beam = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.06, 0.30), mat(COL.gunwale));
  beam.position.set(-0.48, 0.20, 0);
  st.add(beam);
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
  const grip = new THREE.Mesh(gripGeo, mat(COL.grip));
  g.add(grip);

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

  return { group: g, blade, side, shaft, grip };
}

export class Boat {
  constructor(parent) {
    this.group = new THREE.Group();
    parent.add(this.group);

    makeHull(this.group);
    this.fitRiggers = makeRiggers(this.group);
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
    this.fitRiggers(pose.pinY ?? G.pinY);
    // seat slide + wheel spin
    const prevX = this.seat.position.x;
    this.seat.position.x = pose.seat;
    const spin = (pose.seat - prevX) / 0.026;
    for (const w of this.wheels) w.rotation.y += spin; // local y = world z after rotation.x

    for (const oar of [this.oarL, this.oarR]) {
      const inboard=pose.inboard ?? G.inboard;
      const radius=(pose.gripRadius ?? .028)/.028;
      oar.grip.scale.set(radius,radius,1);
      oar.shaft.scale.x=oar.shaft.scale.y=radius;
      oar.shaft.scale.z=(inboard+1.66)/(G.inboard+1.66);
      oar.shaft.position.z=1.66*(1-oar.shaft.scale.z);
      oar.grip.position.z=G.inboard-inboard;
      const frame = oarPose(pose, oar.side);
      oar.group.position.copy(frame.pin);
      oar.group.rotation.copy(frame.rotation);
      oar.blade.rotation.z = oar.side * pose.feather * 1.42;
      const hand = oar.side > 0 ? this.handL : this.handR;
      hand.copy(frame.grip);
      const tip = oar.side > 0 ? this.bladeL : this.bladeR;
      tip.set(0, 0, G.outboard - 0.10).applyQuaternion(frame.quaternion).add(frame.pin);
    }
  }
}
