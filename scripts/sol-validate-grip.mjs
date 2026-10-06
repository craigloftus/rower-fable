// Check the actual hand triangles against each cylindrical handle, including
// face interiors. Bone anchors alone cannot establish a convincing grip.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AnimationMixer, LoopOnce, Vector3, Quaternion, Texture } from 'three';
import { prepareCharacterSkinning, updateCharacterSkinning } from '../src/volume-skinning.js';

const root='validation/characters/sol';
const layout=JSON.parse(readFileSync(`${root}/layout.json`));
const bytes=readFileSync('art/characters/candidates/sol/sol.glb');
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
  const source=i=>{
    const p=new Vector3().fromBufferAttribute(pos,i);
    return new Vector3(p.z/layout.scale,(p.y-layout.hipRest[1])/layout.scale+layout.hipSource[1],-p.x/layout.scale+layout.hipSource[2]);
  };
  const region=(p,k)=>{
    const a=layout.anatomy.sides[k];
    const distance=(start,end)=>{
      const from=new Vector3(...a[start]),to=new Vector3(...a[end]),d=to.sub(from);
      const t=Math.max(0,Math.min(1,p.clone().sub(from).dot(d)/d.lengthSq()));
      return p.distanceTo(from.addScaledVector(d,t));
    };
    const thumb=distance('thumbBase','thumbTip')<distance('knuckle','fingerTip')&&p.y<a.thumbBase[1]&&p.y>a.thumbTip[1]-.008&&Math.abs(p.x)<a.thumbOuterX;
    return thumb?'thumb':p.y<a.fingerJoint[1]+.005?'fingers':p.y<a.wrist[1]-.006&&p.y>a.knuckle[1]+.003?'palm':null;
  };
  const sides=Array.from({length:pos.count},(_,i)=>{
    const p=source(i),k=p.x>0?'L':'R',a=layout.anatomy.sides[k],r=layout.anatomy.regions;
    const edge=r.armBase+Math.max(0,r.armSlopeStart-Math.max(p.y,r.armFloorY))*r.armSlope;
    return Math.abs(p.x)>edge&&p.y<a.wrist[1]+.002&&p.y>a.fingerTip[1]-.015?k:null;
  });
  for(let i=0;i<index.length;i+=3){
    const ids=[index[i],index[i+1],index[i+2]],side=sides[ids[0]];
    if(side&&ids.every(j=>sides[j]===side)) {
      const p=ids.map(source),c=p.reduce((sum,p)=>sum.add(p),new Vector3()).multiplyScalar(1/3),label=region(c,side);
      hands[side].push({mesh,ids,region:label});
      if(p.some(p=>region(p,side)==='thumb'))for(let edge=0;edge<3;edge++){
        const a=ids[edge],b=ids[(edge+1)%3];
        const length=new Vector3().fromBufferAttribute(pos,a).distanceTo(new Vector3().fromBufferAttribute(pos,b));
        thumbEdges[side].push({mesh,a,b,length});
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
  let minimum=Infinity,contactTriangles=0,minimumPalmUp=1,maximumThumbEdgeStretch=0,worstThumbEdge=null;
  const regionGap={palm:Infinity,fingers:Infinity,thumb:Infinity},maximumRegionGap={palm:-Infinity,fingers:-Infinity,thumb:-Infinity};
  // The normal is measured from the sculpt's broad palm sections, independently
  // of the rig's chosen roll. This catches the old 90-degree frame mistake.
  const anatomicalBack=new Vector3(...layout.anatomy.sides[side].palmBack).normalize()
    .applyQuaternion(new Quaternion(...layout.rest['hand'+side].q).invert());
  for(let i=0;i<=20;i++){
    action.paused=false;mixer.setTime(i/10);updateCharacterSkinning(gltf.scene);
    minimumPalmUp=Math.min(minimumPalmUp,anatomicalBack.clone().applyQuaternion(bones['hand'+side].getWorldQuaternion(new Quaternion())).y);
    for(const {mesh,a,b,length} of thumbEdges[side]) {
      const posed=mesh.getVertexPosition(a,new Vector3()).distanceTo(mesh.getVertexPosition(b,new Vector3()));
      if(posed/length>maximumThumbEdgeStretch){maximumThumbEdgeStretch=posed/length;worstThumbEdge={a,b,restLength:length,posedLength:posed,restA:new Vector3().fromBufferAttribute(mesh.geometry.attributes.position,a).toArray(),restB:new Vector3().fromBufferAttribute(mesh.geometry.attributes.position,b).toArray()};}
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
  report.hands[side]={triangles:hands[side].length,minimumSurfaceClearance:minimum,contactTrianglesWithin3mm:contactTriangles,minimumPalmUp,maximumThumbEdgeStretch,worstThumbEdge,regionSurfaceClearance:regionGap,maximumRegionSurfaceClearance:maximumRegionGap};
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
