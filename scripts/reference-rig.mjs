import { Vector3, Quaternion, Matrix4 } from 'three';
import { Stroke, G } from '../src/stroke.js';
import { oarPose } from '../src/oar-pose.js';
import { distance } from './rig-geometry.mjs';
import { smooth } from '../src/util.js';

const v = (x, y, z) => new Vector3(x, y, z);
const up = v(0, 1, 0);
function joint(a, b, l1, l2, pole) {
  const d = a.distanceTo(b);
  if (d >= l1 + l2) throw Error(`Unreachable joint ${d}`);
  const axis = b.clone().sub(a).normalize();
  const along = (l1*l1 - l2*l2 + d*d) / (2*d);
  const normal = pole.clone().addScaledVector(axis, -pole.dot(axis)).normalize();
  return a.clone().addScaledVector(axis, along).addScaledVector(normal, Math.sqrt(l1*l1-along*along));
}

// Preserve the anatomical bend plane. A shortest-arc rotation from world-up
// alone cannot determine bone roll and flips near a vertically downward shin.
function hingeRotations(a,b,c,sign=1) {
  const upper=b.clone().sub(a).normalize(),lower=c.clone().sub(b).normalize();
  const z=upper.clone().cross(lower).normalize().multiplyScalar(sign);
  return [upper,lower].map(y=>new Quaternion().setFromRotationMatrix(
    new Matrix4().makeBasis(y.clone().cross(z).normalize(),y,z)));
}

export function sampleReferenceRig({shoulderHeight, neckHeight, upperArm, forearm, elbowOut, finishElbowOut=elbowOut, footOffset=0,thigh=.45,shin=.44}) {
const frames=[]; let minClearance=Infinity; let maxReach=0;
const stroke = new Stroke();
for(let i=0;i<=240;i++) {
  stroke.mode=i<=120?'drive':'rec'; stroke.p=i<=120?i/120:(i-120)/120;
  const pose=stroke.pose(), bones={};
  const hip=v(pose.seat+0.01,0.415,0);
  const spine=v(-Math.sin(pose.lean),Math.cos(pose.lean),0);
  const shoulder=hip.clone().addScaledVector(spine,shoulderHeight);
  const neck=hip.clone().addScaledVector(spine,neckHeight);
  const legs=[];
  const add=(name,a,b,q)=>{ bones[name]={a:a.toArray(),b:b.toArray(),q:(q||new Quaternion().setFromUnitVectors(up,b.clone().sub(a).normalize())).toArray()}; };
  // The sitting surface stays supported while the torso hinges above it.
  add('pelvis',hip,hip.clone().addScaledVector(up,0.12));
  add('torso',hip.clone().addScaledVector(spine,0.10),neck);
  add('head',neck,neck.clone().add(v(-Math.sin(pose.lean*0.25),Math.cos(pose.lean*0.25),0).multiplyScalar(.30)));
  for(const sd of [1,-1]) {
    const k=sd>0?'L':'R';
    const h=hip.clone().add(v(0,0,sd*.105)), foot=v(G.ankle.x,G.ankle.y+.02,sd*G.ankle.z);
    foot.addScaledVector(v(.14,.10,0).normalize(),footOffset);
    const knee=joint(h,foot,thigh,shin,v(-.12,1,sd*.05));
    const [thighRotation,shinRotation]=hingeRotations(h,knee,foot);
    add('thigh'+k,h,knee,thighRotation); add('shin'+k,knee,foot,shinRotation);
    add('foot'+k,foot,foot.clone().add(v(-.10,.14,0)));
    legs.push([h,knee,.084],[knee,foot,.049]);
  }
  let frameClearance=Infinity;
  for(const sd of [1,-1]) {
    const k=sd>0?'L':'R'; const oar=oarPose(pose,sd);
    const sh=shoulder.clone().add(v(0,0,sd*.185));
    // Palm sits above the cylinder; wrist is on its rower-facing side.
    const wrist=oar.grip.clone().add(v(sd*.045,.045,0).applyQuaternion(oar.quaternion));
    maxReach=Math.max(maxReach,sh.distanceTo(wrist));
    // Bring the elbows down and behind the ribs at the finish, then open
    // their bend planes as the body comes forward over the returning knees.
    const splay=finishElbowOut+(elbowOut-finishElbowOut)*smooth(-.20,.25,pose.lean);
    const pole=v(Math.cos(-0.5),Math.sin(-0.5),sd*splay);
    const elbow=joint(sh,wrist,upperArm,forearm,pole);
    const clearance=Math.min(...legs.flatMap(([a,b,r])=>[
      distance(sh,elbow,a,b)-r-.055, distance(elbow,wrist,a,b)-r-.039]));
    frameClearance=Math.min(frameClearance,clearance);
    const [armRotation,forearmRotation]=hingeRotations(sh,elbow,wrist,-1);
    add('upperArm'+k,sh,elbow,armRotation); add('forearm'+k,elbow,wrist,forearmRotation);
    add('grip'+k,oar.grip,oar.grip.clone().addScaledVector(up,.1),oar.quaternion);
  }
  minClearance=Math.min(minClearance,frameClearance);
  frames.push({time:i/120,pose,bones,clearance:frameClearance});
}
return {frames,minClearance,maxReach};
}
