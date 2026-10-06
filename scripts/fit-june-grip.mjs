// Export the original simplified hand, in its wrist frame, for contact fitting.
import {readFileSync,writeFileSync} from 'node:fs';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Matrix4,Quaternion,Vector3,Texture} from 'three';
const root='validation/reconstruction/fresh-rig',layout=JSON.parse(readFileSync(`${root}/layout.json`)),bytes=readFileSync(`${root}/june.glb`);
const gltf=await new GLTFLoader().register(()=>({name:'Geometry',loadTexture:()=>Promise.resolve(new Texture())})).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const matrix=n=>{const b=layout.rest[n];return new Matrix4().compose(new Vector3(...b.a),new Quaternion(...b.q),new Vector3(1,1,1))};
const hand=matrix('handL').invert(),bones=Object.fromEntries(['hand','mitt','mittTip','thumb','thumbTip'].map(n=>[n,new Matrix4().multiplyMatrices(hand,matrix(n+'L')).toArray()])),points=[],triangles=[];
gltf.scene.traverse(m=>{
 if(!m.isSkinnedMesh)return;const {position,skinWeight,skinIndex}=m.geometry.attributes;
 const unique=new Map(),remap=new Map();
 for(let i=0;i<position.count;i++){
  const r=new Vector3().fromBufferAttribute(position,i),s=[r.z/1.8,(r.y-.415)/1.8+.017,-r.x/1.8-.017];
  if(s[0]<.17||s[1]>-.012||s[1]<-.11)continue;
  const key=s.map(v=>v.toFixed(6)).join(',');if(unique.has(key)){remap.set(i,unique.get(key));continue;}
  const weights={};for(let j=0;j<4;j++){const n=m.skeleton.bones[skinIndex.array[i*4+j]].name;weights[n.slice(0,-1)]=skinWeight.array[i*4+j];}
  if(Object.entries(weights).some(([n,w])=>w>.001&&!bones[n]))continue;
  unique.set(key,points.length);remap.set(i,points.length);
  points.push({p:r.applyMatrix4(hand).toArray(),weights,source:s});
 }
 const ids=m.geometry.index.array;for(let i=0;i<ids.length;i+=3){const t=[ids[i],ids[i+1],ids[i+2]].map(j=>remap.get(j));if(t.every(j=>j!==undefined))triangles.push(t);}
});
writeFileSync(`${root}/grip-input.json`,JSON.stringify({bones,points,triangles}));console.log(points.length);
