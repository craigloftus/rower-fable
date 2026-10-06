// Exported protected surfaces and every animation sample must match approved June.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';
import {Matrix4,Vector3,Texture} from 'three';
import {validateNativeJune} from './validate-native-june.mjs';
const root='art/characters/shared-cast',out='validation/characters/shared-cast';
const manifest=JSON.parse(readFileSync(`${root}/manifest.json`));
const config=JSON.parse(readFileSync(`${root}/cast.json`));
const layout=JSON.parse(readFileSync('validation/reconstruction/fresh-rig/layout.json'));
const B=new Matrix4().set(0,0,-1,0,0,1,0,0,1,0,0,0,0,0,0,1);
const hip=new Vector3(...layout.hipSource).applyMatrix4(B);
const inverse=new Matrix4().makeTranslation(...layout.hipRest).multiply(new Matrix4().makeScale(layout.scale,layout.scale,layout.scale)).multiply(new Matrix4().makeTranslation(-hip.x,-hip.y,-hip.z)).multiply(B).invert();
async function load(file){const b=readFileSync(file);return new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).register(()=>({name:'NoTextures',loadTexture:()=>Promise.resolve(new Texture())})).parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');}
const base=await load(`${root}/june.glb`);
function protectedSurface(scene,chestVariant){
 const vertices=new Map(),triangles=new Set();let count=0;
 scene.updateMatrixWorld(true);
 scene.traverse(mesh=>{if(!mesh.isSkinnedMesh)return;
  const g=mesh.geometry,p=g.attributes.position,w=g.attributes.skinWeight,j=g.attributes.skinIndex;
  const keys=[];
  for(let i=0;i<p.count;i++){
   const position=[p.getX(i),p.getY(i),p.getZ(i)],source=new Vector3(...position).applyMatrix4(inverse);
   const weights=Array.from({length:4},(_,k)=>[mesh.skeleton.bones[j.array[i*4+k]].name,w.array[i*4+k]]).filter(v=>v[1]>0).sort((a,b)=>a[0].localeCompare(b[0]));
   const torso=weights.filter(v=>['spine','torso'].includes(v[0])).reduce((n,v)=>n+v[1],0);
   const chest=chestVariant==='flat'&&torso>.998&&Math.abs(source.x)<.087001&&source.y>.114999&&source.y<.270001&&source.z>.017999;
   const protect=source.y<config.neckCut-.000001&&!chest;
   if(!protect){keys.push(null);continue;}
   const key=position.join(',');keys.push(key);vertices.set(key,weights);count++;
  }
  for(let i=0;i<g.index.count;i+=3){const ids=[0,1,2].map(k=>keys[g.index.array[i+k]]);if(ids.every(Boolean))triangles.add(ids.sort().join('|'));}
 });return{vertices,triangles,count};
}
for(const c of manifest.characters){
 const asset=await load(`${root}/${c.file}`);
 assert.equal(asset.animations.length,1);assert.equal(asset.animations[0].name,'RowingCycle');assert.equal(asset.animations[0].duration,2);
 const a=new Map(base.animations[0].tracks.map(t=>[t.name,t])),b=new Map(asset.animations[0].tracks.map(t=>[t.name,t]));
 assert.equal(a.size,b.size);
 for(const[name,t]of a){const u=b.get(name);assert(u,`Missing June track ${name}`);assert.deepEqual(u.times,t.times,`${c.id} track times ${name}`);assert.deepEqual(u.values,t.values,`${c.id} track values ${name}`);}
 const source=protectedSurface(base.scene,c.chestVariant),target=protectedSurface(asset.scene,c.chestVariant);
 let maxWeightDelta=0;
 for(const[p,weights]of source.vertices){const actual=target.vertices.get(p);assert(actual,`${c.id} altered approved body position ${p}`);assert.deepEqual(actual,weights,`${c.id} altered approved weights at ${p}`);}
 for(const tri of source.triangles)assert(target.triangles.has(tri),`${c.id} altered approved body triangle`);
 for(const p of target.vertices.keys())assert(source.vertices.has(p),`${c.id} added geometry outside head/chest`);
 const clip={passed:true,tracks:a.size,method:'Exact Float32 equality of every approved June track time and value'};
 const identity={...c.bodyIdentityCheck,passed:true,exportedProtectedVertices:source.vertices.size,exportedProtectedTriangles:source.triangles.size,exportedPositionDelta:0,exportedWeightDelta:maxWeightDelta};
 c.clipIdentityCheck=clip;c.bodyIdentityCheck=identity;
 assert.equal(c.sha256,createHash('sha256').update(readFileSync(`${root}/${c.file}`)).digest('hex'));
 mkdirSync(`${out}/${c.id}`,{recursive:true});writeFileSync(`${out}/${c.id}/export-identity.json`,JSON.stringify({body:identity,clip},null,2)+'\n');
 await validateNativeJune(`${root}/${c.file}`,`${out}/${c.id}`);
 console.log(c.id,'exact body + clip identity and 1,201 June native poses passed');
}
writeFileSync(`${root}/manifest.json`,JSON.stringify(manifest,null,2)+'\n');
