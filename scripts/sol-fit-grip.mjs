// Export the original simplified hand, in its wrist frame, for contact fitting.
import {readFileSync,writeFileSync} from 'node:fs';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Matrix4,Quaternion,Vector3,Texture} from 'three';
const root='validation/characters/sol',layout=JSON.parse(readFileSync(`${root}/layout.json`)),bytes=readFileSync('art/characters/candidates/sol/sol.glb');
const gltf=await new GLTFLoader().register(()=>({name:'Geometry',loadTexture:()=>Promise.resolve(new Texture())})).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const matrix=n=>{const b=layout.rest[n];return new Matrix4().compose(new Vector3(...b.a),new Quaternion(...b.q),new Vector3(1,1,1))};
for(const side of ['L','R']) {
const hand=matrix('hand'+side).invert(),bones=Object.fromEntries(['hand','mitt','mittTip','thumb','thumbTip'].map(n=>[n,new Matrix4().multiplyMatrices(hand,matrix(n+side)).toArray()])),points=[],triangles=[];
gltf.scene.traverse(m=>{
 if(!m.isSkinnedMesh)return;const {position,skinWeight,skinIndex}=m.geometry.attributes;
 const unique=new Map(),remap=new Map();
 for(let i=0;i<position.count;i++){
  const r=new Vector3().fromBufferAttribute(position,i),s=[r.z/layout.scale,(r.y-layout.hipRest[1])/layout.scale+layout.hipSource[1],-r.x/layout.scale+layout.hipSource[2]];
  const a=layout.anatomy.sides[side];
  if(s[0]*(side==='L'?1:-1)<.17||s[1]>a.wrist[1]-.010||s[1]<a.fingerTip[1]-.015)continue;
  const key=s.map(v=>v.toFixed(6)).join(',');if(unique.has(key)){remap.set(i,unique.get(key));continue;}
  const weights={};for(let j=0;j<4;j++){const n=m.skeleton.bones[skinIndex.array[i*4+j]].name;weights[n.slice(0,-1)]=skinWeight.array[i*4+j];}
  if(Object.entries(weights).some(([n,w])=>w>.001&&!bones[n]))continue;
  unique.set(key,points.length);remap.set(i,points.length);
  points.push({p:r.applyMatrix4(hand).toArray(),weights,source:s});
 }
 const ids=m.geometry.index.array;for(let i=0;i<ids.length;i+=3){const t=[ids[i],ids[i+1],ids[i+2]].map(j=>remap.get(j));if(t.every(j=>j!==undefined))triangles.push(t);}
});
writeFileSync(`${root}/grip-input-${side}.json`,JSON.stringify({bones,points,triangles,side,anatomy:layout.anatomy.sides[side]}));console.log(points.length);

}
