import * as THREE from 'three';
import { mat, makeLimb, setLimb } from './util.js';
import { G } from './stroke.js';
import { oarPose } from './oar-pose.js';
import { panel, shell, spoonBlade, facets } from './boat-shapes.js';

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
  const hull = shell([
    mat(COL.hull, { roughness: .58 }), mat(0xf2ecd9, { roughness: .6 }),
    mat(COL.gunwale, { roughness: .72 }), mat(0x595c50),
  ]);
  hull.name = 'shell';
  group.add(hull);
  const fin = facets([
    [0,[-3.0,.07,-.007],[-2.72,.07,-.007],[-2.82,-.15,-.007],[-2.94,-.15,-.007]],
    [0,[-2.94,-.15,.007],[-2.82,-.15,.007],[-2.72,.07,.007],[-3.0,.07,.007]],
    [0,[-3.0,.07,.007],[-3.0,.07,-.007],[-2.94,-.15,-.007],[-2.94,-.15,.007]],
    [0,[-2.72,.07,-.007],[-2.72,.07,.007],[-2.82,-.15,.007],[-2.82,-.15,-.007]],
    [0,[-2.94,-.15,-.007],[-2.82,-.15,-.007],[-2.82,-.15,.007],[-2.94,-.15,.007]],
  ], [mat(COL.collar)]);
  group.add(fin);
}

function makeRiggers(group) {
  const metal = mat(0xa8adb0, { roughness: .42, metalness: .45 });
  const dark = mat(COL.collar, { roughness: .65 });
  const riggers = [];
  for (const side of [-1, 1]) {
    const pin = new THREE.Vector3(G.pinX, G.pinY, side * G.pinZ);
    const struts = [[-.48,.233,.215,0,.012],[.45,.233,.215,0,.012],[0,.16,.226,-.024,.009]].map(([x,y,z,dy,r]) => {
      const base=new THREE.Vector3(G.pinX+x,y,side*z),end=pin.clone();end.y+=dy;
      const pad=new THREE.Mesh(panel(.065,.045,.012,.008,.002),dark);
      pad.rotation.x=Math.PI/2;pad.position.copy(base);group.add(pad);
      return {base,end,dy,mesh:tube(group,base,end,r,metal)};
    });
    const lock = new THREE.Group();
    lock.position.copy(pin);
    const post=new THREE.Mesh(new THREE.CylinderGeometry(.009,.009,.10,8),metal);
    post.position.y=.02;lock.add(post);
    // A socket below the pitch axis and a small retaining cap above it.
    for(const [y,r,h] of [[-.027,.030,.023],[.068,.017,.009]]) {
      const ring=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,8),dark);
      ring.position.y=y;lock.add(ring);
    }
    group.add(lock);riggers.push({lock,struts});
  }
  let height=G.pinY;
  return pinY => {
    if(pinY===height)return;
    height=pinY;
    for(const {lock,struts} of riggers) {
      lock.position.y=pinY;
      for(const {mesh,base,end,dy} of struts){end.y=pinY+dy;setLimb(mesh,base,end);}
    }
  };
}

function makeSeatAndStretcher(group) {
  const metal=mat(COL.steel,{roughness:.48,metalness:.35});
  const wood=mat(COL.wood,{roughness:.72}),dark=mat(COL.collar);
  for(const x of [-.27,.57]) {
    const support=new THREE.Mesh(panel(.05,.30,.12,.006,.002),dark);
    support.rotation.x=Math.PI/2;support.position.set(x,.166,0);group.add(support);
  }
  for(const side of [-1,1]) {
    const rail=new THREE.Mesh(panel(1,.023,.018,.004,.002),metal);
    rail.name='slide-rail';rail.rotation.x=Math.PI/2;
    rail.position.set(.13,.227,side*.075);group.add(rail);
  }
  const seat=new THREE.Group();
  const top=new THREE.Mesh(panel(G.seat.length,G.seat.width,G.seat.thickness,.025,.004),wood);
  top.name='seat-top';top.rotation.x=Math.PI/2;
  top.position.y=G.seat.top-G.seat.thickness/2;seat.add(top);
  const wheels=[];
  for(const sx of [-1,1]) for(const sz of [-1,1]) {
    const wheel=new THREE.Mesh(new THREE.CylinderGeometry(.026,.026,.018,12),dark);
    wheel.rotation.x=Math.PI/2;wheel.position.set(sx*.10,.262,sz*.075);
    seat.add(wheel);wheels.push(wheel);
    const hub=new THREE.Mesh(new THREE.CylinderGeometry(.010,.010,.021,8),metal);
    hub.rotation.x=Math.PI/2;hub.position.copy(wheel.position);seat.add(hub);
  }
  group.add(seat);
  const board=new THREE.Mesh(panel(.36,.32,.025,.025,.003),wood);
  board.name='foot-stretcher';board.geometry.rotateY(Math.PI/2);
  board.position.set(-.551,.245,0);board.rotation.z=Math.atan2(.10,.14);group.add(board);
  for(const side of [-1,1]) {
    tube(group,new THREE.Vector3(-.48,.12,side*.15),new THREE.Vector3(-.62,.34,side*.15),.011,metal);
  }
  return {seat,wheels};
}

function makeOar(side) {
  // side +1 -> pin at z = +pinZ. Local +Z always points outboard;
  // group euler order YXZ gives sweep (y) then blade-depth pitch (x).
  const g = new THREE.Group();
  g.position.set(G.pinX, G.pinY, side * G.pinZ);
  g.rotation.order = 'YXZ';

  // The shaft ends inside the outer 3 cm of the handle. It must not run to
  // the butt cap, where coplanar end faces used to flicker through the wood.
  const shaftLen = G.inboard - .27 + 1.66;
  const shaftGeo = new THREE.CylinderGeometry(.016,.023,shaftLen,8);
  shaftGeo.rotateX(Math.PI/2);
  shaftGeo.translate(0,0,1.66-shaftLen/2);
  const shaft = new THREE.Mesh(shaftGeo,mat(COL.shaft,{roughness:.55}));
  g.add(shaft);

  const profile=[[0,0],[.024,0],[.028,.008],[.028,.288],[.025,.30],[0,.30]];
  const gripGeo=new THREE.LatheGeometry(profile.map(p=>new THREE.Vector2(...p)),12);
  gripGeo.rotateX(Math.PI/2);gripGeo.translate(0,0,-G.inboard);
  const grip=new THREE.Mesh(gripGeo,mat(COL.grip,{roughness:.78}));
  g.add(grip);

  const collarGeo=new THREE.CylinderGeometry(.036,.036,.085,10);
  collarGeo.rotateX(Math.PI/2);collarGeo.translate(0,0,-.012);
  g.add(new THREE.Mesh(collarGeo,mat(COL.collar)));
  const sleeveGeo=new THREE.CylinderGeometry(.027,.027,.14,10);
  sleeveGeo.rotateX(Math.PI/2);sleeveGeo.translate(0,0,.085);
  g.add(new THREE.Mesh(sleeveGeo,mat(0x797e70,{roughness:.65})));

  const blade = new THREE.Group();
  blade.position.z=G.outboard-.44;
  blade.add(spoonBlade(side,[mat(COL.blade,{roughness:.5}),mat(COL.bladeTip,{roughness:.5})]));
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
      oar.shaft.scale.z=(inboard-.27+1.66)/(G.inboard-.27+1.66);
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
