import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Texture} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';
import {CHARACTERS} from '../src/characters.js';

async function rig(path) {
  const bytes=await readFile(path);
  const gltf=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder)
    .register(()=>({name:'GeometryValidation',loadTexture:()=>Promise.resolve(new Texture())}))
    .parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  const bones=[];
  gltf.scene.traverse(node=>{
    if(node.isBone) bones.push({name:node.name,position:node.position.toArray(),
      quaternion:node.quaternion.toArray(),scale:node.scale.toArray()});
  });
  return {bones:bones.sort((a,b)=>a.name.localeCompare(b.name)),clips:gltf.animations.map(clip=>({
    name:clip.name,duration:clip.duration,tracks:clip.tracks.map(track=>({
      name:track.name,type:track.ValueTypeName,interpolation:track.getInterpolation(),
      times:Array.from(track.times),values:Array.from(track.values),
    })).sort((a,b)=>a.name.localeCompare(b.name)),
  }))};
}

test('every delivered character retains the exact approved June skeleton and rowing clip',async()=>{
  const approved=await rig('validation/reconstruction/fresh-rig/june.glb');
  for(const {id} of CHARACTERS) {
    assert.deepEqual(await rig(`public/characters/${id}.glb`),approved,`${id} changed the approved rig or motion`);
  }
});
