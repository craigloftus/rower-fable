import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {AnimationMixer,LoopOnce,Vector3,Texture} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';
import {compressCharacter} from './compress-character.mjs';
import {prepareCharacterSkinning,updateCharacterSkinning} from '../src/volume-skinning.js';

async function load(path) {
  const bytes=await readFile(path);
  const gltf=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder)
    .register(()=>({name:'GeometryValidation',loadTexture:()=>Promise.resolve(new Texture())}))
    .parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  prepareCharacterSkinning(gltf.scene);
  const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o);});
  const mixer=new AnimationMixer(gltf.scene),action=mixer.clipAction(gltf.animations[0]);
  action.setLoop(LoopOnce,1).play();action.clampWhenFinished=true;
  return {gltf,meshes,mixer};
}

test('lossless delivery preserves the approved rig and decoded DQ surfaces across the cycle',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'rower-compression-'));
  try {
    const source='validation/reconstruction/fresh-rig/june.glb',output=join(dir,'june.glb');
    const report=await compressCharacter(source,output);
    assert(report.bytes<report.sourceBytes*.6,'Compression must provide a useful size reduction');
    const a=await load(source),b=await load(output);
    assert.equal(a.meshes.length,b.meshes.length);
    assert.equal(b.gltf.animations[0].name,'RowingCycle');
    assert.equal(b.gltf.animations[0].duration,2);
    for(const time of [0,.25,.75,1,1.25,1.5,1.75,2]) {
      for(const model of [a,b]){model.mixer.setTime(time);updateCharacterSkinning(model.gltf.scene);}
      a.meshes.forEach((mesh,m)=>{
        const other=b.meshes[m];
        assert(other.userData.volumePalette,'DQ extras must survive compression');
        assert.equal(mesh.geometry.attributes.position.count,other.geometry.attributes.position.count);
        const count=mesh.geometry.attributes.position.count;
        for(let i=0;i<count;i+=Math.max(1,Math.floor(count/200))) {
          const p=mesh.applyBoneTransform(i,new Vector3().fromBufferAttribute(mesh.geometry.attributes.position,i));
          const q=other.applyBoneTransform(i,new Vector3().fromBufferAttribute(other.geometry.attributes.position,i));
          assert(p.distanceTo(q)<1e-12,`${mesh.name} vertex ${i} changed at ${time}`);
        }
      });
    }
  } finally {await rm(dir,{recursive:true,force:true});}
});
