// Verify the independent head rebuild preserves the body and lower neck below its cut.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Texture,Vector3} from 'three';

const [baseline,candidate]=process.argv.slice(2).map(path=>resolve(path));
async function load(path) {
  const bytes=readFileSync(path);
  return new GLTFLoader().register(()=>({name:'StudyValidation',loadTexture:()=>Promise.resolve(new Texture())}))
    .parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
}
function measure(scene) {
  const body=[],point=new Vector3();
  let triangles=0,vertices=0;
  scene.updateMatrixWorld(true);
  scene.traverse(mesh=>{
    if(!mesh.isMesh)return;
    const positions=mesh.geometry.attributes.position,index=mesh.geometry.index;
    vertices+=positions.count;triangles+=index.count/3;
    for(let i=0;i<positions.count;i++)assert(Number.isFinite(positions.getX(i)+positions.getY(i)+positions.getZ(i)));
    for(let i=0;i<index.count;i+=3) {
      const corners=[0,1,2].map(j=>point.fromBufferAttribute(positions,index.getX(i+j)).applyMatrix4(mesh.matrixWorld).clone());
      if(corners.every(p=>p.y<.322999))body.push(mesh.material.name+'|'+corners.map(p=>p.toArray().map(n=>n.toFixed(7)).join(',')).sort().join('|'));
    }
  });
  return {body:body.sort(),triangles,vertices};
}
const before=measure((await load(baseline)).scene),after=measure((await load(join(candidate,'mesh.glb'))).scene);
assert.deepEqual(after.body,before.body,'The approved body or lower neck geometry changed');
const report={bodyAndLowerNeckTrianglesPreserved:before.body.length,beforeTriangles:before.triangles,afterTriangles:after.triangles,afterVertices:after.vertices};
writeFileSync(join(candidate,'preservation-report.json'),JSON.stringify(report,null,2)+'\n');
console.log(report);
