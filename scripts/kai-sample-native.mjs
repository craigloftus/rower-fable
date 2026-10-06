// Kai's measured source landmarks define the rest skeleton; no limb scaling.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { Vector3, Quaternion, Matrix4, Euler } from 'three';
import { Stroke, G } from '../src/stroke.js';
import { oarPose } from '../src/oar-pose.js';
import { smooth } from '../src/util.js';
import { kaiPose } from './kai-fit.mjs';

const out='validation/characters/kai';mkdirSync(out,{recursive:true});
const anatomy=JSON.parse(readFileSync('art/characters/candidates/kai/anatomy.json'));
const v=(x=0,y=0,z=0)=>new Vector3(x,y,z),up=v(0,1,0),scale=anatomy.scale;
const hipSource=v(...anatomy.hipSource),hipRest=v(0,.415,0);
const source=(x,y,z)=>v(-(z-hipSource.z)*scale,(y-hipSource.y)*scale,x*scale).add(hipRest);
function frame(a,b,z=v(0,0,1)) {
  const y=b.clone().sub(a).normalize();
  z=z.clone().addScaledVector(y,-z.dot(y)).normalize();
  return new Quaternion().setFromRotationMatrix(new Matrix4().makeBasis(y.clone().cross(z),y,z));
}
const rest={},hands={};
function bone(name,a,b,parent,z) {rest[name]={a:a.toArray(),b:b.toArray(),q:frame(a,b,z).toArray(),parent};}
const center=anatomy.center;
bone('pelvis',hipRest,hipRest.clone().add(v(0,.10,0)),null);
bone('spine',hipRest,source(...center.waist),'pelvis');
bone('torso',source(...center.waist),source(...center.neck),'spine');
bone('head',source(...center.neck),source(...center.crown),'torso');
for(const [side,k] of [[1,'L'],[-1,'R']]) {
  const a=anatomy.sides[k],p=name=>source(...a[name]);
  const hip=p('hip'),knee=p('knee'),ankle=p('ankle'),shoulder=p('shoulder');
  const elbow=p('elbow'),wrist=p('wrist'),clavicle=p('clavicle');
  const hinge=v(0,0,1),palmBack=v(...a.palmBack);
  bone('clavicle'+k,clavicle,shoulder,'torso');
  bone('upperArm'+k,shoulder,elbow,'clavicle'+k,hinge);
  for(const [i,name] of ['forearm','forearmTwist','forearmWrist'].entries())
    bone(name+k,elbow.clone().lerp(wrist,i/3),elbow.clone().lerp(wrist,(i+1)/3),i?['forearm','forearmTwist'][i-1]+k:'upperArm'+k,hinge);
  bone('hand'+k,wrist,p('knuckle'),'forearmWrist'+k,palmBack);
  bone('mitt'+k,p('knuckle'),p('fingerJoint'),'hand'+k,palmBack);
  bone('mittTip'+k,p('fingerJoint'),p('fingerTip'),'mitt'+k,palmBack);
  bone('thumb'+k,p('thumbBase'),p('thumbJoint'),'hand'+k,palmBack);
  bone('thumbTip'+k,p('thumbJoint'),p('thumbTip'),'thumb'+k,palmBack);
  bone('thigh'+k,hip,knee,'pelvis',hinge);
  bone('shin'+k,knee,ankle,'thigh'+k,hinge);
  bone('foot'+k,ankle,p('toe'),'shin'+k,v(0,1,0));
  hands[k]=a.grip;
}
const restPoint=name=>v(...rest[name].a),restEnd=name=>v(...rest[name].b),restQ=name=>new Quaternion(...rest[name].q);
const len=name=>restPoint(name).distanceTo(restEnd(name));
function joint(a,b,l1,l2,pole) {
  const d=a.distanceTo(b);
  if(d>=l1+l2)throw Error(`Unreachable native joint: ${d} >= ${l1+l2}`);
  const axis=b.clone().sub(a).normalize(),along=(l1*l1-l2*l2+d*d)/(2*d);
  return a.clone().addScaledVector(axis,along).addScaledVector(pole.clone().addScaledVector(axis,-pole.dot(axis)).normalize(),Math.sqrt(l1*l1-along*along));
}
const stroke=new Stroke();
export function nativeFrame(time,hipHeight=.462,hipRoll=0) {
  stroke.mode=time<=1?'drive':'rec';stroke.p=time<=1?time:time-1;
  const pose=kaiPose(stroke.pose()),bones={};
  const hip=v(pose.seat+.01,hipHeight,0),lean=pose.lean;
  const tilt=angle=>new Quaternion().setFromAxisAngle(v(0,0,1),angle);
  const pelvisQ=tilt(lean*.12).multiply(new Quaternion().setFromAxisAngle(v(1,0,0),hipRoll));
  const spineQ=tilt(lean*.72),torsoQ=tilt(lean);
  const add=(name,a,q)=>{bones[name]={a:a.toArray(),b:a.clone().add(v(0,len(name),0).applyQuaternion(q)).toArray(),q:q.toArray()};};
  add('pelvis',hip,pelvisQ);
  add('spine',hip,spineQ);
  const waist=hip.clone().add(restEnd('spine').sub(restPoint('spine')).applyQuaternion(spineQ));
  add('torso',waist,torsoQ.clone().multiply(restQ('torso')));
  const neck=waist.clone().add(restEnd('torso').sub(restPoint('torso')).applyQuaternion(torsoQ));
  add('head',neck,tilt(lean*.25));
  for(const [side,k] of [[1,'L'],[-1,'R']]) {
    const h=hip.clone().add(restPoint('thigh'+k).sub(hipRest).applyQuaternion(pelvisQ));
    const footNormal=v(.14,.10,0).normalize(),footTangent=v(-.10,.14,0).normalize();
    // Source soles are fitted precisely after the first geometry evaluation.
    const foot=v(-.551,.245,side*.115).addScaledVector(footNormal,anatomy.sides[k].soleOffset).addScaledVector(footTangent,-.055);
    const knee=joint(h,foot,len('thigh'+k),len('shin'+k),v(-.12,1,side*.03));
    const hinge=knee.clone().sub(h).cross(foot.clone().sub(knee)).normalize();
    add('thigh'+k,h,frame(h,knee,hinge));add('shin'+k,knee,frame(knee,foot,hinge));
    add('foot'+k,foot,new Quaternion().setFromUnitVectors(up,footNormal).multiply(restQ('foot'+k)));
    const clavicle=waist.clone().add(restPoint('clavicle'+k).sub(restPoint('torso')).applyQuaternion(torsoQ));
    const protraction=-.04+.26*smooth(-.25,.32,lean);
    const clavicleQ=torsoQ.clone().multiply(new Quaternion().setFromAxisAngle(up,-side*protraction));
    const shoulder=clavicle.clone().add(restEnd('clavicle'+k).sub(restPoint('clavicle'+k)).applyQuaternion(clavicleQ));
    add('clavicle'+k,clavicle,clavicleQ.clone().multiply(restQ('clavicle'+k)));
    const oar=oarPose(pose,side),x=v(0,0,-side).applyQuaternion(oar.quaternion);
    const z=up.clone().addScaledVector(x,-up.dot(x)).normalize(),y=z.clone().cross(x);
    const forward=smooth(-.2,.25,lean);
    // Rotate around the handle until the wrist follows the forearm. The
    // grip fixes the palm, not the roll of the entire upper arm.
    let handQ=new Quaternion().setFromRotationMatrix(new Matrix4().makeBasis(x,y,z));
    const upperLength=len('upperArm'+k),foreLength=restPoint('forearm'+k).distanceTo(restEnd('forearmWrist'+k));
    let wrist,elbow;
    const pole=v(.75,-1,side*(.35+.40*forward));
    for(let iteration=0;iteration<16;iteration++) {
      wrist=oar.grip.clone().sub(v(...hands[k]).applyQuaternion(handQ));
      elbow=joint(shoulder,wrist,upperLength,foreLength,pole);
      const along=wrist.clone().sub(elbow).normalize();
      const handY=along.addScaledVector(x,-along.dot(x)).normalize();
      const neutral=new Quaternion().setFromRotationMatrix(new Matrix4().makeBasis(x,handY,x.clone().cross(handY)));
      handQ.slerp(neutral,.6);
    }
    wrist=oar.grip.clone().sub(v(...hands[k]).applyQuaternion(handQ));
    elbow=joint(shoulder,wrist,upperLength,foreLength,pole);
    const armHinge=elbow.clone().sub(shoulder).cross(wrist.clone().sub(elbow)).normalize().negate();
    add('upperArm'+k,shoulder,frame(shoulder,elbow,armHinge));
    const foreQ=frame(elbow,wrist,armHinge),foreAxis=wrist.clone().sub(elbow).normalize();
    const handMappedForearm=handQ.clone().multiply(restQ('hand'+k).invert()).multiply(restQ('forearm'+k));
    const handAligned=new Quaternion().setFromUnitVectors(up.clone().applyQuaternion(handMappedForearm),foreAxis).multiply(handMappedForearm);
    for(const [j,name] of ['forearm','forearmTwist','forearmWrist'].entries()) {
      add(name+k,elbow.clone().lerp(wrist,j/3),foreQ.clone().slerp(handAligned,j/2));
    }
    add('hand'+k,wrist,handQ);
    const handTransform=new Matrix4().compose(wrist,handQ,v(1,1,1))
      .multiply(new Matrix4().compose(restPoint('hand'+k),restQ('hand'+k),v(1,1,1)).invert());
    const transforms={hand:handTransform};
    for(const [name,parent,curl] of [['mitt','hand',anatomy.sides[k].curl[0]],['mittTip','mitt',anatomy.sides[k].curl[1]],['thumb','hand',anatomy.sides[k].curl[2]],['thumbTip','thumb',anatomy.sides[k].curl[3]]]) {
      const a=restPoint(name+k).applyMatrix4(transforms[parent]);
      const q=new Quaternion().setFromRotationMatrix(transforms[parent]).multiply(restQ(name+k))
        .multiply(name==='thumb' ? new Quaternion().setFromEuler(new Euler(curl,side*anatomy.sides[k].thumbSpread,side*anatomy.sides[k].thumbRoll,'XYZ')) : new Quaternion().setFromAxisAngle(v(1,0,0),curl));
      add(name+k,a,q);
      transforms[name]=new Matrix4().compose(a,q,v(1,1,1))
        .multiply(new Matrix4().compose(restPoint(name+k),restQ(name+k),v(1,1,1)).invert());
    }
    bones['grip'+k]={a:oar.grip.toArray(),b:oar.grip.clone().addScaledVector(up,.08).toArray(),q:oar.quaternion.toArray()};
  }
  return {time,pose,bones};
}
if(process.argv[1]?.endsWith('kai-sample-native.mjs')) {
  const frames=Array.from({length:241},(_,i)=>nativeFrame(i/120));
  writeFileSync(`${out}/layout.json`,JSON.stringify({anatomy,scale,hipSource:hipSource.toArray(),hipRest:hipRest.toArray(),rest,hands},null,2));
  writeFileSync(`${out}/samples.json`,JSON.stringify(frames));
  console.log(`Native rig: ${Object.keys(rest).length} bones, ${frames.length} poses; no limb resizing.`);
}
