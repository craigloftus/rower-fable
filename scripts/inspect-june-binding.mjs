import {readFileSync} from 'node:fs';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {AnimationMixer,Vector3,Texture} from 'three';
const bytes=readFileSync('validation/reconstruction/rigged/june.glb');
const gltf=await new GLTFLoader().register(()=>({name:'GeometryOnly',loadTexture:()=>Promise.resolve(new Texture())})).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
new AnimationMixer(gltf.scene).clipAction(gltf.animations[0]).play();gltf.scene.updateMatrixWorld(true);
const mixer=new AnimationMixer(gltf.scene);mixer.clipAction(gltf.animations[0]).play();mixer.setTime(0);gltf.scene.updateMatrixWorld(true);
const bad=[];
gltf.scene.traverse(m=>{if(!m.isSkinnedMesh)return;
 const g=m.geometry,a=g.attributes;
 for(let i=0;i<a.position.count;i++){
  const p=m.getVertexPosition(i,new Vector3()).applyMatrix4(m.matrixWorld);
  if(p.y<.10)bad.push({material:m.material.name,index:i,posed:p.toArray(),rest:new Vector3().fromBufferAttribute(a.position,i).toArray(),weights:[0,1,2,3].map(k=>[m.skeleton.bones[a.skinIndex.array[i*4+k]].name,a.skinWeight.array[i*4+k]])});
 }
 if(m.material.name.includes('Skin'))for(const n of ['color','_color_1']){const attr=a[n];if(attr)console.log(n,Array.from(attr.array.slice(0,16)));}
});
console.log('Vertices below hull:',bad.length);console.log(JSON.stringify(bad.sort((a,b)=>a.posed[1]-b.posed[1]).slice(0,8),null,2));
