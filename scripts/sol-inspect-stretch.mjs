import {readFileSync,writeFileSync} from 'node:fs';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {AnimationMixer,Vector3,Texture} from 'three';
import {prepareCharacterSkinning,updateCharacterSkinning} from '../src/volume-skinning.js';
const root='validation/characters/sol',layout=JSON.parse(readFileSync(`${root}/layout.json`));
const bytes=readFileSync('art/characters/candidates/sol/sol.glb');
const g=await new GLTFLoader().register(()=>({name:'Geometry',loadTexture:()=>Promise.resolve(new Texture())})).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
prepareCharacterSkinning(g.scene);const mix=new AnimationMixer(g.scene);mix.clipAction(g.animations[0]).play();mix.setTime(0);updateCharacterSkinning(g.scene);
const results=[];
g.scene.traverse(m=>{if(!m.isSkinnedMesh)return;const a=m.geometry.attributes,p=a.position,f=m.geometry.index.array;
 const src=i=>{const v=new Vector3().fromBufferAttribute(p,i);return[v.z/layout.scale,(v.y-layout.hipRest[1])/layout.scale+layout.hipSource[1],-v.x/layout.scale+layout.hipSource[2]]};
 const weights=i=>Object.fromEntries([0,1,2,3].map(j=>[m.skeleton.bones[a.skinIndex.getComponent(i,j)].name,a.skinWeight.getComponent(i,j)]));
 for(let t=0;t<f.length;t+=3)for(let j=0;j<3;j++){const i=f[t+j],k=f[t+(j+1)%3],v=new Vector3().fromBufferAttribute(p,i),w=new Vector3().fromBufferAttribute(p,k),rest=v.distanceTo(w),posed=m.getVertexPosition(i,v).distanceTo(m.getVertexPosition(k,w));if(rest>.0005&&posed/rest>1.5)results.push({material:m.material.name,ratio:posed/rest,extra:posed-rest,a:src(i),b:src(k),wa:weights(i),wb:weights(k)});}
});
results.sort((a,b)=>b.extra-a.extra);writeFileSync(`${root}/stretch-study.json`,JSON.stringify(results.slice(0,50),null,2));console.log(results.slice(0,5));
const samples=JSON.parse(readFileSync(`${root}/samples.json`));
for (const i of [0,60,120,180,239]) {mix.setTime(i/120);updateCharacterSkinning(g.scene);const errors=[];g.scene.traverse(b=>{if(!b.isBone)return;const expected=samples[i].bones[b.name];errors.push([b.name,b.getWorldPosition(new Vector3()).distanceTo(new Vector3(...expected.a))]);});console.log('BONE_FRAME',i,errors.sort((a,b)=>b[1]-a[1]).slice(0,5));}
mix.setTime(0);updateCharacterSkinning(g.scene);
for(const k of ['L','R']) {
const b=[];g.scene.traverse(o=>{if(o.isBone&&o.name==='foot'+k)b.push(o)});
const bone=b[0],normal=new Vector3(.14,.10,0).normalize();
console.log('FOOT',k,'pos',bone.getWorldPosition(new Vector3()).toArray(),'sample',samples[0].bones['foot'+k].a,'offset',layout.anatomy.sides[k].soleOffset);
let low=Infinity,sourceY=Infinity;
g.scene.traverse(m=>{if(!m.isSkinnedMesh||m.material.name!=='Shoe soles')return;const p=m.geometry.attributes.position;for(let i=0;i<p.count;i++){const q=new Vector3().fromBufferAttribute(p,i);if((q.z>0)!==(k==='L'))continue;sourceY=Math.min(sourceY,(q.y-layout.hipRest[1])/layout.scale+layout.hipSource[1]);low=Math.min(low,m.getVertexPosition(i,new Vector3()).sub(bone.getWorldPosition(new Vector3())).dot(normal));}});
console.log('SOLE',k,{sourceY,relativeLow:low,expected:(sourceY-layout.anatomy.sides[k].ankle[1])*layout.scale});
}
