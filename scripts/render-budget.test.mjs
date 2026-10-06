import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { batchScenery } from '../src/static-batch.js';
import { createFramePacer } from '../src/render-budget.js';
import { packChunk, unpackChunk } from '../src/course-chunks.js';
import { Course, buildChunk } from '../src/course.js';

test('60/120/240 Hz displays deliver up to 120 evenly spaced frames without catch-up bursts', () => {
  for (const hz of [60,120,240]) {
    const pace=createFramePacer(), times=[];
    for(let i=0;i<hz*10;i++) if(pace(i*1000/hz,120)) times.push(i*1000/hz);
    assert.equal(times.length,Math.min(hz,120)*10);
    for(let i=1;i<times.length;i++) assert.ok(Math.abs(times[i]-times[i-1]-1000/Math.min(hz,120))<.001);
    assert.equal(pace(100_000,120),true);
    assert.equal(pace(100_001,120),false);
  }
});

test('setup renders at 30 Hz and a workout returns immediately to 120 Hz', () => {
  const pace=createFramePacer();let count=0;
  for(let i=0;i<120;i++) if(pace(i*1000/120,30)) count++;
  assert.equal(count,30);
  assert.equal(pace(1001,120),true);
  assert.equal(pace(1005,120),false);
});

function facets(root) {
  root.updateWorldMatrix(true,true);
  const result=[];
  root.traverse(mesh=>{
    if(!mesh.isMesh)return;
    const p=mesh.geometry.attributes.position, idx=mesh.geometry.index;
    for(let i=0;i<(idx?.count??p.count);i++) {
      const v=new THREE.Vector3().fromBufferAttribute(p,idx?idx.getX(i):i).applyMatrix4(mesh.matrixWorld);
      result.push(`${mesh.material.uuid}:${v.toArray().map(x=>x.toFixed(4)).join(',')}`);
    }
  });
  return result.sort();
}
test('batching preserves world-space triangles/materials under nested transforms',()=>{
  const g=new THREE.Group();g.position.set(4,3,5);g.rotation.y=.4;
  const m=new THREE.MeshStandardMaterial();let disposed=0;
  for(let i=0;i<4;i++){
    const child=new THREE.Group();child.position.set(i*2,1,2);child.rotation.z=.2;
    const geo=new THREE.BoxGeometry();geo.addEventListener('dispose',()=>disposed++);
    const mesh=new THREE.Mesh(geo,m);mesh.scale.set(1,2,.8);child.add(mesh);g.add(child);
  }
  const before=facets(g);batchScenery(g);
  assert.deepEqual(facets(g),before);
  assert.equal(g.children.length,1);assert.equal(disposed,4);
});

test('streamed course stays bounded and disposes retired batches',async()=>{
  const scene=new THREE.Scene(), course=new Course(scene, null, async index=>unpackChunk(packChunk(buildChunk(index))));let disposed=0;
  course.update(0,0,0);
  await new Promise(resolve=>setImmediate(resolve));
  for(const c of course.chunks.values()) c.traverse(m=>{if(m.isMesh&&!m.isInstancedMesh)m.geometry.addEventListener('dispose',()=>disposed++);});
  for(let distance=500;distance<=10000;distance+=500){
    course.update(.016,distance,distance/4);
    await new Promise(resolve=>setImmediate(resolve));
    assert.ok(course.chunks.size<=9);
    let meshes=0;for(const c of course.chunks.values())c.traverse(m=>{if(m.isMesh)meshes++;});
    assert.ok(meshes<1000);
  }
  assert.ok(disposed>0);
});

test('worker transfer keeps geometry, materials and reed transforms intact',()=>{
  const original=buildChunk(4), packed=packChunk(original);
  const transferred=structuredClone(packed,{transfer:packed.flatMap(p=>[
    ...Object.values(p.attributes).map(a=>a.array.buffer),
    ...(p.index?[p.index.buffer]:[]),...(p.instances?[p.instances.buffer]:[]),
  ])});
  const restored=unpackChunk(transferred);
  assert.equal(restored.children.length,original.children.length);
  for(let i=0;i<original.children.length;i++){
    const a=original.children[i],b=restored.children[i];
    assert.deepEqual(b.geometry.attributes.position.array,a.geometry.attributes.position.array);
    assert.deepEqual(b.geometry.attributes.normal.array,a.geometry.attributes.normal.array);
    assert.equal(b.material.color.getHex(),a.material.color.getHex());
    assert.equal(b.material.side,a.material.side);
    if(a.isInstancedMesh)assert.deepEqual(b.instanceMatrix.array,a.instanceMatrix.array);
  }
  assert.ok(buildChunk(5).children.at(-1).geometry.attributes.position.array.byteLength>0);
});

test('late worker results after resetting the course are discarded',async()=>{
  const jobs=new Map(),course=new Course(new THREE.Scene(),null,index=>new Promise(resolve=>jobs.set(index,resolve)));
  course.update(0,0,0);const first=[...jobs.keys()];
  course.update(0,5000,0);
  let disposed=0;
  for(const index of first){const g=buildChunk(index);g.traverse(m=>m.geometry?.addEventListener('dispose',()=>disposed++));jobs.get(index)(g);}
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(course.chunks.size,0);assert.ok(disposed>0);
});
