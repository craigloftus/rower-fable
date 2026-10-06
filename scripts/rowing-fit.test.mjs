import test from 'node:test';
import assert from 'node:assert/strict';
import { Group, Vector3 } from 'three';
import { Boat } from '../src/boat.js';
import { Stroke, G } from '../src/stroke.js';
import { fitRowingPose } from '../src/rowing-fit.js';
import { oarPose } from '../src/oar-pose.js';

test('fitted boat meshes agree with hand targets, including character changes', () => {
  const boat=new Boat(new Group()),stroke=new Stroke();
  for(const character of ['kai','june','kai'])for(const time of [0,.4,1,1.1,1.4,1.7,2]) {
    stroke.mode=time<=1?'drive':'rec';stroke.p=time<=1?time:time-1;
    const pose=fitRowingPose(stroke.pose(),character);
    boat.setPose(pose);boat.group.updateMatrixWorld(true);
    assert.equal(boat.seat.position.x,pose.seat);
    for(const oar of [boat.oarL,boat.oarR]) {
      const target=oar.side>0?boat.handL:boat.handR;
      // The actual wood mesh puts the hand 10 cm from its inner end.
      const end=oar.grip.localToWorld(new Vector3(0,0,-G.inboard+.10));
      assert(end.distanceTo(target)<1e-10);
      const centre=oar.grip.localToWorld(new Vector3(0,0,-G.inboard+.15));
      const edge=oar.grip.localToWorld(new Vector3(.028,0,-G.inboard+.15));
      assert(Math.abs(edge.distanceTo(centre)-(character==='june'?.020:.028))<1e-10);
      assert.equal(oar.group.position.y,character==='june'?.45:G.pinY);
      oar.shaft.geometry.computeBoundingBox();
      const shaftEnd=oar.shaft.localToWorld(new Vector3(0,0,oar.shaft.geometry.boundingBox.min.z));
      const socket=oar.grip.localToWorld(new Vector3(0,0,-G.inboard+.27));
      assert(shaftEnd.distanceTo(socket)<1e-6,'Shaft must end inside the handle socket');
      oar.grip.geometry.computeBoundingBox();
      assert(Math.abs(oar.grip.geometry.boundingBox.min.z+G.inboard)<1e-7);
      assert(Math.abs(oar.grip.geometry.boundingBox.max.z+G.inboard-.30)<1e-7);
    }
  }
});


test('recovery keeps moving through hands-away and has no wrist snap at crossover', () => {
  const stroke=new Stroke();stroke.mode='rec';
  const pose=p=>{stroke.p=p;return fitRowingPose(stroke.pose(),'june');};
  const hand=p=>oarPose(pose(p),1).grip;
  const dt=1e-5;
  for(let p=.15;p<=.85;p+=.01){
    const speed=hand(p+dt).distanceTo(hand(p-dt))/(2*dt);
    assert(speed>.10,`Recovery pauses at ${p}`);
  }
  // Locate the actual crossing, rather than testing fixed animation samples.
  let low=0,high=1;
  for(let i=0;i<40;i++){
    const p=(low+high)/2;
    if(pose(p).oar<0)low=p;else high=p;
  }
  for(const p of [(low+high)/2,.30]){
    const left=hand(p).sub(hand(p-dt)).multiplyScalar(1/dt);
    const right=hand(p+dt).sub(hand(p)).multiplyScalar(1/dt);
    assert(left.distanceTo(right)<.002,`Handle velocity jumps at ${p}`);
  }
  const before=pose(.28),after=pose(.32);
  assert(after.seat<before.seat && after.lean>before.lean,'Body swing and slide should overlap');
});


test('boat contact surfaces retain the rig dimensions', () => {
  const boat=new Boat(new Group());
  boat.group.updateMatrixWorld(true);
  const seat=boat.group.getObjectByName('seat-top');
  seat.geometry.computeBoundingBox();
  const top=seat.localToWorld(new Vector3(0,0,seat.geometry.boundingBox.min.z));
  assert(Math.abs(top.y-G.seat.top)<1e-7);
  const rail=boat.group.getObjectByName('slide-rail');
  rail.geometry.computeBoundingBox();
  const railTop=rail.localToWorld(new Vector3(0,0,rail.geometry.boundingBox.min.z));
  assert(Math.abs(railTop.y-(boat.wheels[0].position.y-.026))<1e-7);
  const board=boat.group.getObjectByName('foot-stretcher');
  board.geometry.computeBoundingBox();
  assert(Math.abs(board.geometry.boundingBox.max.x-.0125)<1e-7);
  assert.equal(board.position.x,-.551);
  assert.equal(board.rotation.z,Math.atan2(.10,.14));
});
