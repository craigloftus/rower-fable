import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';
import {AnimationMixer,LoopOnce,Vector3,Quaternion,Texture,Group} from 'three';
import {prepareCharacterSkinning,updateCharacterSkinning} from '../src/volume-skinning.js';
import {Stroke,G} from '../src/stroke.js';
import {oarPose} from '../src/oar-pose.js';
import {adaPose} from './ada-fit.mjs';
import {pathToFileURL} from 'node:url';

const root='validation/characters/ada';
// Clip large facets to the contact band instead of requiring their whole
// triangle to be below it. A curved seat contact often crosses a facet.
function clippedArea(vertices, planes) {
  let polygon=vertices;
  for(const distance of planes) {
    const next=[];
    for(let i=0;i<polygon.length;i++) {
      const a=polygon[i],b=polygon[(i+1)%polygon.length],da=distance(a),db=distance(b);
      if(da>=0)next.push(a);
      if((da>=0)!==(db>=0))next.push(a.clone().lerp(b,da/(da-db)));
    }
    polygon=next;
  }
  return Math.abs(polygon.reduce((sum,a,i)=>{const b=polygon[(i+1)%polygon.length];return sum+a.x*b.z-a.z*b.x;},0))/2;
}

export async function validateNativeAda(asset='art/characters/candidates/ada/ada.glb', reportRoot=root) {
const bytes=readFileSync(asset),layout=JSON.parse(readFileSync(`${root}/layout.json`));
let maxRestKneePlaneDeviation=0;
for(const k of ['L','R'])for(const joint of ['thigh','shin']) {
  const hinge=new Vector3(0,0,1).applyQuaternion(new Quaternion(...layout.rest[joint+k].q));
  const bone=layout.rest[joint+k],axis=new Vector3(...bone.b).sub(new Vector3(...bone.a)).normalize();
  const lateral=new Vector3(0,0,1).addScaledVector(axis,-axis.z).normalize();
  maxRestKneePlaneDeviation=Math.max(maxRestKneePlaneDeviation,hinge.angleTo(lateral));
  assert(hinge.dot(lateral)>1-1e-7,'Rest knee axes must match the projected lateral axis of this source limb');
}
const gltf=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).register(()=>({name:'GeometryValidation',loadTexture:()=>Promise.resolve(new Texture())}))
  .parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
prepareCharacterSkinning(gltf.scene);
const bones={},meshes=[];
gltf.scene.traverse(o=>{if(o.isBone)bones[o.name]=o;if(o.isSkinnedMesh)meshes.push(o);});
assert(meshes.every(m=>m.userData.volumePalette),'Every part of the new rig must use the declared skinning method.');
const clip=gltf.animations[0],mixer=new AnimationMixer(gltf.scene),action=mixer.clipAction(clip);
assert.equal(gltf.animations.length,1);assert.equal(clip.name,'RowingCycle');assert.equal(clip.duration,2);
assert(!clip.tracks.some(t=>t.name.includes('morphTarget')),'The body has no reshaping/morph animation.');
for(const track of clip.tracks.filter(t=>t.name.endsWith('.scale'))){
  assert([...track.values].every((v,i)=>Math.abs(v-track.values[i%3])<1e-6),'Animated bone scale');
  assert([...track.values].every(v=>Math.abs(v-1)<.00005),'Bone scale exceeds exporter rounding');
}
action.setLoop(LoopOnce,1).play();action.clampWhenFinished=true;
const surfaces=meshes.filter(m=>m.material.name.includes('_shorts'));
const soles=meshes.filter(m=>m.material.name.includes('Shoe soles'));
const points=new Map([...surfaces,...soles].map(m=>[m,Array.from({length:m.geometry.attributes.position.count},()=>new Vector3())]));
const key=p=>p.toArray().map(c=>Math.round(c*1e6)).join(',');
const sourcePositions=new Map();
for(const mesh of meshes)for(let i=0;i<mesh.geometry.attributes.position.count;i++) {
  const p=new Vector3().fromBufferAttribute(mesh.geometry.attributes.position,i),id=key(p);
  if(!sourcePositions.has(id))sourcePositions.set(id,[]);
  sourcePositions.get(id).push([mesh,i]);
}
// A material boundary must remain a shared surface throughout deformation.
const seams=[...sourcePositions.values()].filter(items=>new Set(items.map(([m])=>m.material.name)).size>1);
const stroke=new Stroke(),normal=new Vector3(.14,.10,0).normalize(),stretcher=new Vector3(-.551,.245,0);
const report={maxRestKneePlaneDeviation,restKneePlaneDefinition:'Source lateral axis projected perpendicular to each measured thigh/shin',sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,bones:Object.keys(bones).length,
  triangles:meshes.reduce((n,m)=>n+m.geometry.index.count/3,0),samples:1201,sourceScale:layout.scale,
  maxGripError:0,maxBoneLengthError:0,maxAngularStep:0,maxSeamGap:0,minSeatClearance:Infinity,maxSeatGap:0,
  minSeatContactArea:Infinity,minSoleClearance:Infinity,maxSoleClearance:-Infinity,maxSoleDrift:0,maxKneeTwist:0,
  maxRigidPlacementError:0};
let previous=null,firstSoles=null;const witness=[];
for(let frame=0;frame<=1200;frame++) {
  const time=frame/600;action.paused=false;mixer.setTime(time);updateCharacterSkinning(gltf.scene);
  stroke.mode=time<=1?'drive':'rec';stroke.p=time<=1?time:time-1;const pose=adaPose(stroke.pose());
  for(const [side,k] of [[1,'L'],[-1,'R']]) {
    const hand=bones['hand'+k],anchor=new Vector3(...layout.hands[k]).applyQuaternion(hand.getWorldQuaternion(new Quaternion())).add(hand.getWorldPosition(new Vector3()));
    report.maxGripError=Math.max(report.maxGripError,anchor.distanceTo(oarPose(pose,side).grip));
    for(const [start,end,tip] of [['clavicle','upperArm','clavicle'],['upperArm','forearm','upperArm'],
      ['forearm','hand','forearmWrist'],['thigh','shin','thigh'],['shin','foot','shin']]) {
      const expected=new Vector3(...layout.rest[start+k].a).distanceTo(new Vector3(...layout.rest[tip+k].b));
      const actual=bones[start+k].getWorldPosition(new Vector3()).distanceTo(bones[end+k].getWorldPosition(new Vector3()));
      report.maxBoneLengthError=Math.max(report.maxBoneLengthError,Math.abs(actual-expected));
    }
    const thigh=new Vector3(0,0,1).applyQuaternion(bones['thigh'+k].getWorldQuaternion(new Quaternion()));
    const shin=new Vector3(0,0,1).applyQuaternion(bones['shin'+k].getWorldQuaternion(new Quaternion()));
    report.maxKneeTwist=Math.max(report.maxKneeTwist,thigh.angleTo(shin));assert(thigh.z>.98&&shin.z>.98);
  }
  const rotations=Object.values(bones).map(b=>b.getWorldQuaternion(new Quaternion()));
  if(previous)for(let i=0;i<rotations.length;i++)report.maxAngularStep=Math.max(report.maxAngularStep,rotations[i].angleTo(previous[i]));
  previous=rotations;
  const low=[Infinity,Infinity],area=[0,0];
  const inside=p=>Math.abs(p.x-pose.seat)<G.seat.length/2-.002&&Math.abs(p.z)<G.seat.width/2-.002;
  for(const mesh of surfaces) {
    const vertices=points.get(mesh),indices=mesh.geometry.index.array;
    for(let i=0;i<vertices.length;i++) {
      const p=mesh.getVertexPosition(i,vertices[i]).applyMatrix4(mesh.matrixWorld);
      if(inside(p))low[p.z<0?0:1]=Math.min(low[p.z<0?0:1],p.y-G.seat.top);
    }
    const planes=[p=>G.seat.top+.003-p.y,p=>p.x-pose.seat+G.seat.length/2-.002,
      p=>pose.seat+G.seat.length/2-.002-p.x,p=>p.z+G.seat.width/2-.002,p=>G.seat.width/2-.002-p.z];
    for(let i=0;i<indices.length;i+=3) {
      const [a,b,c]=[vertices[indices[i]],vertices[indices[i+1]],vertices[indices[i+2]]];
      if(Math.min(a.y,b.y,c.y)>G.seat.top+.003)continue;
      area[0]+=clippedArea([a,b,c],[...planes,p=>-p.z]);
      area[1]+=clippedArea([a,b,c],[...planes,p=>p.z]);
    }
  }
  report.minSeatClearance=Math.min(report.minSeatClearance,...low);report.maxSeatGap=Math.max(report.maxSeatGap,...low);
  report.minSeatContactArea=Math.min(report.minSeatContactArea,...area);
  const solePoints=[],soleLow=[Infinity,Infinity];
  for(const mesh of soles)for(let i=0;i<mesh.geometry.attributes.position.count;i++) {
    const p=mesh.getVertexPosition(i,points.get(mesh)[i]).applyMatrix4(mesh.matrixWorld);solePoints.push(p.clone());
    const gap=p.clone().sub(stretcher).dot(normal)-.0125;
    report.minSoleClearance=Math.min(report.minSoleClearance,gap);
    soleLow[p.z<0?0:1]=Math.min(soleLow[p.z<0?0:1],gap);
  }
  report.maxSoleClearance=Math.max(report.maxSoleClearance,...soleLow);
  if(!firstSoles)firstSoles=solePoints;
  else for(let i=0;i<solePoints.length;i++)report.maxSoleDrift=Math.max(report.maxSoleDrift,solePoints[i].distanceTo(firstSoles[i]));
  if(frame%30===0)for(const items of seams) {
    const [mesh,i]=items[0],p=mesh.getVertexPosition(i,new Vector3());
    for(const [other,j] of items.slice(1))report.maxSeamGap=Math.max(report.maxSeamGap,p.distanceTo(other.getVertexPosition(j,new Vector3())));
  }
  if([0,300,600,960,1200].includes(frame))for(const mesh of meshes)for(let i=0;i<mesh.geometry.attributes.position.count;i+=199) {
    witness.push({time,rest:new Vector3().fromBufferAttribute(mesh.geometry.attributes.position,i).toArray(),posed:mesh.getVertexPosition(i,new Vector3()).toArray()});
  }
}
// The game moves and rolls the entire boat. That parent transform must not
// be applied twice by the custom skin or change the body's deformation.
const placementWitness=meshes.flatMap(mesh=>Array.from({length:Math.ceil(mesh.geometry.attributes.position.count/499)},(_,n)=>{
  const index=n*499;return {mesh,index,point:mesh.getVertexPosition(index,new Vector3()).applyMatrix4(mesh.matrixWorld)};
}));
const boat=new Group();boat.add(gltf.scene);boat.position.set(123,.15,-5);boat.rotation.set(.05,.73,-.03);
boat.updateMatrixWorld(true);updateCharacterSkinning(gltf.scene);
for(const {mesh,index,point} of placementWitness) {
  const actual=mesh.getVertexPosition(index,new Vector3()).applyMatrix4(mesh.matrixWorld);
  report.maxRigidPlacementError=Math.max(report.maxRigidPlacementError,actual.distanceTo(point.applyMatrix4(boat.matrixWorld)));
}
writeFileSync(`${reportRoot}/measurements.json`,JSON.stringify(report,null,2)+'\n');
writeFileSync(`${reportRoot}/parity-witness.json`,JSON.stringify(witness));
console.log(JSON.stringify(report,null,2));
assert(report.maxGripError<.002,'Grip anchors drift');
assert(report.maxBoneLengthError<.00001,'Limb length changes');
assert(report.maxAngularStep<.04,'Bone motion jumps');
assert(report.maxSeamGap<.00005,'Material boundaries separate');
assert(report.minSeatClearance>-.0001&&report.maxSeatGap<.002,'Seat support lost');
assert(report.minSeatContactArea>.00005,'Insufficient seat proximity area within 3 mm');
assert(report.minSoleClearance>0&&report.maxSoleClearance<.001,'Soles miss stretcher');
// Sub-frame glTF interpolation of the parent chain may move a shoe by a few
// hundredths of a millimetre; measured across the surface, not a foot marker.
assert(report.maxSoleDrift<.0001,'Feet move');
assert(report.maxKneeTwist<.01,'Knee axes disagree');
assert(report.maxRigidPlacementError<.0001,'Moving the boat changes the skin deformation');
writeFileSync(`${reportRoot}/report.json`,JSON.stringify(report,null,2)+'\n');
return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await validateNativeAda(process.argv[2]);
