// Check the actual hand triangles against each cylindrical handle, including
// face interiors. Bone anchors alone cannot establish a convincing grip.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AnimationMixer, LoopOnce, Vector3, Quaternion, Texture } from 'three';
import { prepareCharacterSkinning, updateCharacterSkinning } from '../src/volume-skinning.js';

const root='validation/reconstruction/fresh-rig';
const layout=JSON.parse(readFileSync(`${root}/layout.json`));
const bytes=readFileSync(`${root}/june.glb`);
const gltf=await new GLTFLoader().register(()=>({name:'Geometry',loadTexture:()=>Promise.resolve(new Texture())}))
  .parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
prepareCharacterSkinning(gltf.scene);
const mixer=new AnimationMixer(gltf.scene),action=mixer.clipAction(gltf.animations[0]);
action.setLoop(LoopOnce,1).play();action.clampWhenFinished=true;
const bones={},hands={L:[],R:[]},thumbEdges={L:[],R:[]};
gltf.scene.traverse(mesh=>{
  if(mesh.isBone)bones[mesh.name]=mesh;
  if(!mesh.isSkinnedMesh)return;
  const pos=mesh.geometry.attributes.position,index=mesh.geometry.index.array;
  const sides=Array.from({length:pos.count},(_,i)=>{
    const p=new Vector3().fromBufferAttribute(pos,i),x=p.z/1.8,y=(p.y-.415)/1.8+.017;
    return Math.abs(x)>.17&&y<-.012&&y>-.11?(x>0?'L':'R'):null;
  });
  for(let i=0;i<index.length;i+=3){
    const ids=[index[i],index[i+1],index[i+2]],side=sides[ids[0]];
    if(side&&ids.every(j=>sides[j]===side)) {
      const source=ids.map(j=>{const p=new Vector3().fromBufferAttribute(pos,j);return [Math.abs(p.z/1.8),(p.y-.415)/1.8+.017,-p.x/1.8-.017];});
      const c=[0,1,2].map(k=>source.reduce((sum,p)=>sum+p[k],0)/3);
      const region=c[1]>-.040&&c[1]<-.015&&c[0]<.198&&c[2]<.028?'palm':c[1]<-.075?'fingers':c[0]<.197&&c[1]<-.040&&c[2]>.023?'thumb':null;
      hands[side].push({mesh,ids,region});
      if(source.some(p=>p[0]<.199&&p[1]<-.042&&p[1]>-.073&&p[2]>.023)) {
        for(let edge=0;edge<3;edge++){
          const a=ids[edge],b=ids[(edge+1)%3];
          const length=new Vector3().fromBufferAttribute(pos,a).distanceTo(new Vector3().fromBufferAttribute(pos,b));
          thumbEdges[side].push({mesh,a,b,length});
        }
      }
    }
  }
});
function radialDistance(polygon){
  let inside=true,distance=Infinity,sign=0;
  for(let i=0;i<polygon.length;i++){
    const a=polygon[i],b=polygon[(i+1)%polygon.length],cross=a.x*b.y-a.y*b.x;
    if(sign&&Math.sign(cross)!==sign)inside=false;
    if(Math.abs(cross)>1e-14)sign=Math.sign(cross);
    const dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,-(a.x*dx+a.y*dy)/(dx*dx+dy*dy)));
    distance=Math.min(distance,Math.hypot(a.x+t*dx,a.y+t*dy));
  }
  return inside?0:distance;
}
function clip(polygon,distance){
  const out=[];
  for(let i=0;i<polygon.length;i++){
    const a=polygon[i],b=polygon[(i+1)%polygon.length],da=distance(a),db=distance(b);
    if(da>=0)out.push(a);
    if((da>=0)!==(db>=0))out.push(a.clone().lerp(b,da/(da-db)));
  }
  return out;
}
const report={poses:21,handleRadius:.020,hands:{}};
for(const side of ['L','R']){
  let minimum=Infinity,contactTriangles=0,minimumPalmUp=1,maximumThumbEdgeStretch=0;
  const regionGap={palm:Infinity,fingers:Infinity,thumb:Infinity},maximumRegionGap={palm:-Infinity,fingers:-Infinity,thumb:-Infinity};
  // The normal is measured from the sculpt's broad palm sections, independently
  // of the rig's chosen roll. This catches the old 90-degree frame mistake.
  const anatomicalBack=new Vector3(-.31,0,side==='L'?.95:-.95).normalize()
    .applyQuaternion(new Quaternion(...layout.rest['hand'+side].q).invert());
  for(let i=0;i<=20;i++){
    action.paused=false;mixer.setTime(i/10);updateCharacterSkinning(gltf.scene);
    minimumPalmUp=Math.min(minimumPalmUp,anatomicalBack.clone().applyQuaternion(bones['hand'+side].getWorldQuaternion(new Quaternion())).y);
    for(const {mesh,a,b,length} of thumbEdges[side]) {
      const posed=mesh.getVertexPosition(a,new Vector3()).distanceTo(mesh.getVertexPosition(b,new Vector3()));
      maximumThumbEdgeStretch=Math.max(maximumThumbEdgeStretch,posed/length);
    }
    const poseGaps={palm:Infinity,fingers:Infinity,thumb:Infinity};
    const grip=bones['grip'+side],centre=grip.getWorldPosition(new Vector3()),q=grip.getWorldQuaternion(new Quaternion()).invert();
    for(const {mesh,ids,region} of hands[side]){
      let triangle=ids.map(j=>mesh.getVertexPosition(j,new Vector3()).sub(centre).applyQuaternion(q));
      triangle=clip(clip(triangle,p=>p.z+.1),p=>.2-p.z);
      if(triangle.length<3)continue;
      const gap=radialDistance(triangle)-report.handleRadius;
      minimum=Math.min(minimum,gap);
      if(region)poseGaps[region]=Math.min(poseGaps[region],gap);
      if(i===10&&gap<.003)contactTriangles++;
    }
    for(const region of Object.keys(poseGaps)){
      regionGap[region]=Math.min(regionGap[region],poseGaps[region]);
      maximumRegionGap[region]=Math.max(maximumRegionGap[region],poseGaps[region]);
    }
  }
  report.hands[side]={triangles:hands[side].length,minimumSurfaceClearance:minimum,contactTrianglesWithin3mm:contactTriangles,minimumPalmUp,maximumThumbEdgeStretch,regionSurfaceClearance:regionGap,maximumRegionSurfaceClearance:maximumRegionGap};
}
writeFileSync(`${root}/grip-report.json`,JSON.stringify(report,null,2)+'\n');
console.log(report);
for(const hand of Object.values(report.hands)){
  assert(hand.minimumSurfaceClearance>-.002,'The simplified hand penetrates its handle by more than 2 mm');
  assert(hand.contactTrianglesWithin3mm>=2,'The hand floats off its handle');
  assert(hand.maximumThumbEdgeStretch<1.5,'The thumb/web is being stretched into a flap');
  assert(hand.minimumPalmUp>.5,'The broad palm is turned sideways instead of facing down onto the handle');
  assert(hand.maximumRegionSurfaceClearance.palm<.004,'The palm floats above the handle despite fingertip contact');
}
