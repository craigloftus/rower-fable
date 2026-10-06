import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AnimationMixer, LoopOnce, Vector3, Matrix4, Texture } from 'three';
import { makePalette, deformPoint } from '../src/volume-skinning.js';

const out='validation/rig-audit';
mkdirSync(out,{recursive:true});
const bytes=readFileSync('public/characters/june.glb');
const gltf=await new GLTFLoader().register(()=>({name:'AuditGeometry',loadTexture:()=>Promise.resolve(new Texture())}))
  .parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const mixer=new AnimationMixer(gltf.scene),clip=gltf.animations[0],action=mixer.clipAction(clip);
action.setLoop(LoopOnce,1).play();action.clampWhenFinished=true;
const meshes=[];
const point=new Vector3(),a=new Vector3(),b=new Vector3(),matrix=new Matrix4();
function region(mesh,index) {
  const {skinIndex,skinWeight}=mesh.geometry.attributes;
  const ws=Array.from({length:4},(_,j)=>[mesh.skeleton.bones[skinIndex.array[4*index+j]].name,skinWeight.array[4*index+j]]);
  const weight=name=>ws.reduce((sum,[bone,w])=>sum+(bone.startsWith(name)?w:0),0);
  if(mesh.material.name.includes('shorts'))return 'shorts';
  if(weight('upperArm')>.15 && weight('forearm')>.15)return 'elbows';
  if(weight('upperArm')>.1 && weight('torso')>.1)return 'shoulders';
  if(weight('upperArm')>.5 || weight('forearm')>.5)return 'arm shafts';
  if(weight('thigh')>.5)return 'thighs';
  if(weight('torso')+weight('pelvis')>.5)return 'trunk';
  return 'other';
}
gltf.scene.traverse(mesh=>{
  if(!mesh.isSkinnedMesh)return;
  const {geometry:g}=mesh, positions=g.attributes.position;
  const edges=[],seen=new Set();
  const ids=g.index.array;
  for(let i=0;i<ids.length;i+=3)for(let j=0;j<3;j++) {
    const ia=ids[i+j],ib=ids[i+(j+1)%3];
    a.fromBufferAttribute(positions,ia);b.fromBufferAttribute(positions,ib);
    const length=a.distanceTo(b);
    if(length<.005)continue;
    const ends=[a.toArray().map(x=>x.toFixed(6)).join(','),b.toArray().map(x=>x.toFixed(6)).join(',')].sort();
    const key=ends.join('/');if(seen.has(key))continue;seen.add(key);
    const ra=region(mesh,ia),rb=region(mesh,ib);
    if(ra!==rb || ra==='other')continue;
    edges.push({ia,ib,length,region:ra,min:[Infinity,Infinity],max:[0,0]});
  }
  meshes.push({mesh,edges,palette:makePalette(mesh.skeleton),posed:[new Float64Array(positions.count*3),new Float64Array(positions.count*3)]});
});
let maxBoneScaleError=0;
const witness=[];
for(let frame=0;frame<=48;frame++) {
  const time=frame/24;action.paused=false;mixer.setTime(time);gltf.scene.updateMatrixWorld(true);
  for(const data of meshes) {
    const {mesh,edges,palette,posed}=data,{position}=mesh.geometry.attributes;palette.update();
    mesh.skeleton.bones.forEach((bone,i)=>{
      matrix.multiplyMatrices(bone.matrixWorld,mesh.skeleton.boneInverses[i]);
      const scale=new Vector3().setFromMatrixScale(matrix);
      maxBoneScaleError=Math.max(maxBoneScaleError,...scale.toArray().map(v=>Math.abs(v-1)));
    });
    for(let i=0;i<position.count;i++) {
      mesh.getVertexPosition(i,point).toArray(posed[0],3*i);
      point.fromBufferAttribute(position,i);deformPoint(mesh,palette,i,point).toArray(posed[1],3*i);
    }
    for(const e of edges)for(let method=0;method<2;method++) {
      const p=posed[method];a.fromArray(p,3*e.ia);b.fromArray(p,3*e.ib);
      const ratio=a.distanceTo(b)/e.length;e.min[method]=Math.min(e.min[method],ratio);e.max[method]=Math.max(e.max[method],ratio);
    }
    // Blender independently checks these same rest points/weights and poses.
    if([0,12,24,38,48].includes(frame))for(let i=0;i<position.count;i+=251) {
      const attrs=mesh.geometry.attributes;
      witness.push({time,material:mesh.material.name,rest:point.fromBufferAttribute(position,i).toArray(),
        weights:Array.from({length:4},(_,j)=>[mesh.skeleton.bones[attrs.skinIndex.array[4*i+j]].name,attrs.skinWeight.array[4*i+j]]),
        lbs:Array.from(posed[0].slice(3*i,3*i+3)),dq:Array.from(posed[1].slice(3*i,3*i+3))});
    }
  }
}
const percentile=(values,p)=>values.sort((a,b)=>a-b)[Math.floor((values.length-1)*p)];
const scaleTracks=clip.tracks.filter(t=>t.name.endsWith('.scale'));
const report={sha256:createHash('sha256').update(bytes).digest('hex'),samples:49,
  scaleTracks:scaleTracks.map(t=>({name:t.name,maximumChange:Math.max(...Array.from(t.values,(v,i)=>Math.abs(v-t.values[i%3])))})),
  morphTracks:clip.tracks.filter(t=>t.name.includes('morphTarget')).map(t=>t.name),maxBoneScaleError,
  metric:'Unique mesh edges at least 5 mm long. Ratios are relative to the existing, already altered bind mesh. Ranges include all 49 cycle samples. These are surface-edge measurements, not body volume or likeness.',regions:{}};
for(const region of ['shoulders','elbows','arm shafts','trunk','shorts','thighs']) {
  const edges=meshes.flatMap(d=>d.edges.filter(e=>e.region===region));
  report.regions[region]={edges:edges.length};
  for(const [method,name] of ['linear','dualQuaternion'].entries())report.regions[region][name]={
    minimumRatioP01:percentile(edges.map(e=>e.min[method]),.01),
    maximumRatioP99:percentile(edges.map(e=>e.max[method]),.99),
    cycleRangeP95:percentile(edges.map(e=>e.max[method]-e.min[method]),.95),
    edgesEverOutside25Percent:edges.filter(e=>e.min[method]<.75 || e.max[method]>1.25).length/edges.length};
}
// These are the landmarks/scales in rig-final-june.py, not new anatomy estimates.
const hip=new Vector3(0,.017,-.017),neck=new Vector3(0,.31,-.02);
const shoulder=new Vector3(.185/1.8,.017+.50/.55*(.31-.017),-.017),elbow=new Vector3(.123,.140,-.021),wrist=new Vector3(.198,-.014,.011);
report.bindScaling={uniformScale:1.8,torsoHeightRelativeToWidth:(.55/(neck.y-hip.y))/1.8,
  upperArm:{sourceLength:shoulder.distanceTo(elbow),uniformLength:shoulder.distanceTo(elbow)*1.8,retargetedLength:.30,axialToRadialScale:.30/(shoulder.distanceTo(elbow)*1.8)},
  forearm:{sourceLength:elbow.distanceTo(wrist),uniformLength:elbow.distanceTo(wrist)*1.8,retargetedLength:.30,axialToRadialScale:.30/(elbow.distanceTo(wrist)*1.8)}};
const frames=JSON.parse(readFileSync('validation/reconstruction/stroke-samples.json'));
const originalReach=(shoulder.distanceTo(elbow)+elbow.distanceTo(wrist))*1.8;
const reaches=frames.flatMap(frame=>['L','R'].map(k=>new Vector3(...frame.bones['upperArm'+k].a).distanceTo(new Vector3(...frame.bones['forearm'+k].b))));
report.originalArmReach={available:originalReach,maximumRequired:Math.max(...reaches),
  unreachableTargets:reaches.filter(d=>d>=originalReach).length,targets:reaches.length,
  caveat:'Reach only, retaining the current shoulder and wrist targets. This does not validate elbow clearance or a newly bound mesh.'};
writeFileSync(`${out}/deformation.json`,JSON.stringify(report,null,2)+'\n');
writeFileSync(`${out}/witness.json`,JSON.stringify(witness));
console.log(JSON.stringify(report,null,2));
