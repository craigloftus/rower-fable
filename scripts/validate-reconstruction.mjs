import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AnimationMixer, LoopOnce, Vector3, Quaternion, Texture } from 'three';
import { CHARACTERS } from '../src/characters.js';
import { seatSurface } from './seat-contact.mjs';
import { Stroke, G } from '../src/stroke.js';
import { oarPose } from '../src/oar-pose.js';
import { distance } from './rig-geometry.mjs';

const report=[];
const profile=JSON.parse(readFileSync('validation/reconstruction/rig-profile.json'));
for(const id of ['june']){
  const bytes=readFileSync('validation/reconstruction/rigged/june.glb');
  const gltf=await new GLTFLoader().register(()=>({name:'GeometryOnlyValidation',loadTexture:()=>Promise.resolve(new Texture())})).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  const clip=gltf.animations.find(c=>c.name==='RowingCycle');
  assert.equal(gltf.animations.length,1);assert(clip);assert(Math.abs(clip.duration-2)<.001);
  const mixer=new AnimationMixer(gltf.scene),action=mixer.clipAction(clip);
  action.setLoop(LoopOnce,1).play();action.clampWhenFinished=true;
  const bones={};gltf.scene.traverse(o=>{if(o.isBone)bones[o.name]=o;});
  const measureSeat=seatSurface(gltf.scene);
  let maxSurfaceSeatGap=0,minSeatClearance=Infinity,minContactArea=Infinity,maxCentreDrop=0;
  let maxGripError=0,maxFootError=0,maxJointStep=0,maxSeatError=0;
  let minExportedClearance=Infinity,maxKneeTwist=0;
  let previous=null,previousRotations=null,maxBoneAngularStep=0;const stroke=new Stroke();
  for(let i=0;i<=1200;i++){
    const t=i/600;action.paused=false;mixer.setTime(t);gltf.scene.updateMatrixWorld(true);
    stroke.mode=t<=1?'drive':'rec';stroke.p=t<=1?t:t-1;
    for(const [side,k] of [[1,'L'],[-1,'R']]) {
      const grip=bones['grip'+k].getWorldPosition(new Vector3());
      maxGripError=Math.max(maxGripError,grip.distanceTo(oarPose(stroke.pose(),side).grip));
      const footTarget=new Vector3(-.47,.235,side*.115).addScaledVector(new Vector3(.14,.10,0).normalize(),profile.footOffset);
      maxFootError=Math.max(maxFootError,bones['foot'+k].getWorldPosition(new Vector3()).distanceTo(footTarget));
    }
    const support=measureSeat(stroke.pose().seat,G.seat);
    maxSurfaceSeatGap=Math.max(maxSurfaceSeatGap,support.gap);
    minSeatClearance=Math.min(minSeatClearance,support.minimumClearance);
    minContactArea=Math.min(minContactArea,support.contactArea);
    maxCentreDrop=Math.max(maxCentreDrop,support.centreDrop);
    // Both sides of each knee must share a lateral hinge axis. This catches
    // the ~142 degree shin-roll error that position-only tests did not detect.
    for(const k of ['L','R']) {
      const lateral=name=>new Vector3(0,0,1).applyQuaternion(bones[name+k].getWorldQuaternion(new Quaternion()));
      const thigh=lateral('thigh'),shin=lateral('shin');
      maxKneeTwist=Math.max(maxKneeTwist,thigh.angleTo(shin));
      assert(thigh.z>.98 && shin.z>.98,`${id}: knee hinge points away from the lateral axis`);
    }
    const pos=name=>bones[name].getWorldPosition(new Vector3());
    const legs=['L','R'].flatMap(k=>[[pos('thigh'+k),pos('shin'+k),.084],[pos('shin'+k),pos('foot'+k),.049]]);
    for(const k of ['L','R']) {
      const sh=pos('upperArm'+k),elbow=pos('forearm'+k);
      const wrist=new Vector3(0,.30,0).applyQuaternion(bones['forearm'+k].getWorldQuaternion(new Quaternion())).add(elbow);
      for(const [a,b,r] of legs) minExportedClearance=Math.min(minExportedClearance,distance(sh,elbow,a,b)-r-.055,distance(elbow,wrist,a,b)-r-.039);
    }
    maxSeatError=Math.max(maxSeatError,pos('pelvis').distanceTo(new Vector3(stroke.pose().seat+.01,.415,0)));
    const joints=Object.values(bones).map(b=>b.getWorldPosition(new Vector3()));
    assert(joints.every(v=>v.toArray().every(Number.isFinite)));
    if(previous)for(let n=0;n<joints.length;n++)maxJointStep=Math.max(maxJointStep,joints[n].distanceTo(previous[n]));
    const rotations=Object.values(bones).map(b=>b.getWorldQuaternion(new Quaternion()));
    if(previousRotations)for(let n=0;n<rotations.length;n++)maxBoneAngularStep=Math.max(maxBoneAngularStep,rotations[n].angleTo(previousRotations[n]));
    previousRotations=rotations;previous=joints;
  }
  writeFileSync('validation/reconstruction/rigged/measurements.json',JSON.stringify({maxSurfaceSeatGap,minSeatClearance,minContactArea,maxCentreDrop,maxBoneAngularStep,maxKneeTwist,minExportedClearance,maxGripError,maxFootError,maxSeatError},null,2));
  assert(maxSurfaceSeatGap<.001,`${id}: shorts float ${maxSurfaceSeatGap} m above the seat`);
  assert(minSeatClearance>-.001,`${id}: shorts penetrate the seat ${minSeatClearance} m`);
  assert(minContactArea>.0001,`${id}: sitting contact is only ${minContactArea} square metres`);
  assert(maxCentreDrop<.001,`${id}: centre of shorts hangs below the sitting pads`);
  assert(maxBoneAngularStep<.05,`${id}: bone rotation discontinuity ${maxBoneAngularStep}`);
  assert(maxKneeTwist<Math.PI/180,`${id}: knee twist ${maxKneeTwist*180/Math.PI} degrees`);
  assert(minExportedClearance>.01,`${id}: clearance ${minExportedClearance}`);
  assert(maxSeatError<.001,`${id}: seat drift ${maxSeatError}`);
  assert(maxGripError<.002,`${id}: grip error ${maxGripError}`);
  assert(maxFootError<.001,`${id}: foot drift ${maxFootError}`);
  assert(maxJointStep<.025,`${id}: discontinuity ${maxJointStep}`);
  report.push({id,sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,bones:Object.keys(bones).length,samples:1201,maxGripError,maxFootError,maxJointStep,maxSeatError,maxSurfaceSeatGap,minSeatClearance,minContactArea,maxCentreDrop,minExportedClearance,maxKneeTwistDegrees:maxKneeTwist*180/Math.PI,maxBoneAngularStepDegrees:maxBoneAngularStep*180/Math.PI});
}
const samples=JSON.parse(readFileSync('validation/reconstruction/stroke-samples.json'));
const minimumCapsuleClearance=Math.min(...samples.map(s=>s.clearance));
assert(minimumCapsuleClearance>.01);
writeFileSync('validation/reconstruction/rigged/report.json',JSON.stringify({minimumCapsuleClearance,characters:report},null,2));
console.log(JSON.stringify({minimumCapsuleClearance,characters:report},null,2));
