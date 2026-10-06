// Fit the intact body to the seat by moving the pelvis, never reshaping shorts.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Matrix4,Vector3,Quaternion,Texture} from 'three';
import {makePalette,deformPoint} from '../src/volume-skinning.js';
import {nativeFrame} from './sample-june-native.mjs';

const root='validation/reconstruction/fresh-rig',bytes=readFileSync(`${root}/june.glb`);
const gltf=await new GLTFLoader().register(()=>({name:'Geometry',loadTexture:()=>Promise.resolve(new Texture())}))
  .parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
let shorts;gltf.scene.traverse(o=>{if(o.isSkinnedMesh && o.material.name.includes('_shorts'))shorts=o;});
const skeleton=shorts.skeleton;
// Use the desired world frames directly, independent of Blender's pose cache.
const bones=skeleton.bones.map(b=>({name:b.name,matrixWorld:new Matrix4()}));
const palette=makePalette({bones,boneInverses:skeleton.boneInverses});
const pos=shorts.geometry.attributes.position,p=new Vector3(),q=new Quaternion(),one=new Vector3(1,1,1);
function support(sample) {
  bones.forEach(b=>{const frame=sample.bones[b.name];b.matrixWorld.compose(new Vector3(...frame.a),q.fromArray(frame.q),one);});
  palette.update();const low=[Infinity,Infinity];
  for(let i=0;i<pos.count;i++) {
    p.fromBufferAttribute(pos,i);deformPoint(shorts,palette,i,p);
    if(Math.abs(p.x-sample.pose.seat)<.138 && Math.abs(p.z)<.148)low[p.z<0?0:1]=Math.min(low[p.z<0?0:1],p.y);
  }
  return low;
}
const frames=[],report=[];
for(let i=0;i<=240;i++) {
  let height=.462,roll=0,sample,low;
  for(let iteration=0;iteration<8;iteration++) {
    sample=nativeFrame(i/120,height,roll);low=support(sample);
    const error=low.map(y=>y-.3179);
    if(Math.max(...error.map(Math.abs))<1e-6)break;
    // Match both sitting contacts with pelvis translation and a small roll.
    // Numeric derivatives include the influence of the fixed feet on the IK.
    const dh=support(nativeFrame(i/120,height+.0001,roll)).map((y,j)=>(y-low[j])/.0001);
    const dr=support(nativeFrame(i/120,height,roll+.0001)).map((y,j)=>(y-low[j])/.0001);
    const determinant=dh[0]*dr[1]-dh[1]*dr[0];
    height-=(error[0]*dr[1]-error[1]*dr[0])/determinant;
    roll-=(dh[0]*error[1]-dh[1]*error[0])/determinant;
  }
  assert(Math.max(...low.map(y=>Math.abs(y-.3179)))<1e-5,'Pelvis contact solve did not converge');
  assert(Math.abs(roll)<.04,`Seat fit requires roll ${roll} at time ${i/120}, low ${low}, height ${height}`);
  frames.push(sample);report.push({time:sample.time,hipHeight:height,hipRoll:roll,clearance:low.map(y=>y-.3175)});
}
writeFileSync(`${root}/samples.json`,JSON.stringify(frames));
writeFileSync(`${root}/seat-fit.json`,JSON.stringify(report,null,2)+'\n');
console.log({poses:frames.length,hipHeight:[Math.min(...report.map(r=>r.hipHeight)),Math.max(...report.map(r=>r.hipHeight))],
  maximumRollDegrees:Math.max(...report.map(r=>Math.abs(r.hipRoll)))*180/Math.PI,
  maximumSideClearance:Math.max(...report.flatMap(r=>r.clearance))});
