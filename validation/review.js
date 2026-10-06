import { fitRowingPose as fitPreviousGripPose } from './reconstruction/fresh-rig/pre-recovery-fix/rowing-fit.js';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Boat } from '../src/boat.js';
import { Boat as PreviousBoat } from './boat/before.js';
import { Stroke, G } from '../src/stroke.js';
import { fitRowingPose } from '../src/rowing-fit.js';
import { Rower } from '../src/rower.js';
import { CHARACTERS } from '../src/characters.js';
import { Boat as OldBoat } from './original-boat.js';
import { Stroke as OldStroke } from './original-stroke.js';
import { Rower as OldRower } from './original-rower.js';
import { useDualQuaternion,prepareCharacterSkinning,updateCharacterSkinning } from '../src/volume-skinning.js';

// Compare against the first Blender body, or the original runtime rig.
const baseline=new URLSearchParams(location.search).get('baseline');
const reconstruction=baseline==='reconstruction';
const native=baseline==='native';
const boatStudy=baseline==='boat';
const skinning=baseline==='skinning';
const bindStudy=baseline==='bind';
const diagnostic=skinning || bindStudy;
const comparison=document.createElement('button');
document.querySelector('header').append(comparison);
const narrowPanel=matchMedia('(max-width: 900px)');
let single=narrowPanel.matches,viewChosen=false;
function showComparison(){document.body.classList.toggle('single',single);comparison.textContent=single?'Show comparison':'Current only';}
comparison.onclick=()=>{viewChosen=true;single=!single;showComparison();};
narrowPanel.onchange=e=>{if(!viewChosen){single=e.matches;showComparison();}};showComparison();
for(const [id,label] of [['torso','Torso profile'],['shoulders','Shoulders'],['hand','Hand detail'],...(native?[['thumb','Thumb detail']]:[]),...(boatStudy?[['shell','Whole boat'],['cockpit','Cockpit'],['blade','Blade']]:[])]) {
  const button=document.createElement('button');button.id=id;button.textContent=label;
  document.querySelector('header').append(button);
}
const bodyPass=['body','seat','sculpt','reconstruction','skinning','bind','native','boat'].includes(baseline);
class PreviousBody {
  constructor(scene, path=`validation/${baseline==='body'?'v2':baseline}/june-before.glb`, volume=false) {
    this.ready=false;
    new GLTFLoader().load(`${import.meta.env.BASE_URL}${path}?review=${Date.now()}`,gltf=>{
      scene.add(gltf.scene);
      gltf.scene.traverse(o=>{if(o.isMesh)o.frustumCulled=false;if(volume && o.isSkinnedMesh)useDualQuaternion(o);});
      if(!volume)prepareCharacterSkinning(gltf.scene);
      this.model=gltf.scene;
      this.mixer=new THREE.AnimationMixer(gltf.scene);
      this.action=this.mixer.clipAction(gltf.animations[0]);
      this.action.setLoop(THREE.LoopOnce,1);this.action.clampWhenFinished=true;this.action.play();
      this.ready=true;
    });
  }
  update(pose) {
    if(!this.ready)return;
    this.action.paused=false;this.mixer.setTime((pose.mode==='drive'?0:1)+pose.p);
    updateCharacterSkinning(this.model);
  }
}
class ReconstructedBody extends PreviousBody {
  constructor(scene) { super(scene,'characters/june.glb'); }
}
class BindBody {
  constructor(scene,source) {
    this.ready=false;
    const path=source?'june-final/mesh.glb':'rigged/june.glb';
    new GLTFLoader().load(`${import.meta.env.BASE_URL}validation/reconstruction/${path}`,gltf=>{
      const model=gltf.scene;
      if(source){
        model.rotation.y=-Math.PI/2;model.scale.setScalar(1.8);
        model.position.set(-.017*1.8,.415-.017*1.8,0);
      }else{
        model.updateMatrixWorld(true);
        model.traverse(o=>{if(o.isSkinnedMesh)o.skeleton.pose();});
      }
      model.traverse(o=>{if(o.isMesh)o.frustumCulled=false;});
      scene.add(model);this.ready=true;
    });
  }
  update() {}
}
if(bodyPass){
  document.querySelector('#before h2').textContent=baseline==='sculpt'?'June · before sculpt':baseline==='seat'?'June · before seat correction':'June · previous body';
  document.querySelector('#after h2').textContent=baseline==='sculpt'?'June · reference sculpt':baseline==='seat'?'Supported seat · current character':'Shared body pass · current character';
}
if(reconstruction){
  document.querySelector('#before h2').textContent='June · before rowing fit';
  document.querySelector('#after h2').textContent='June · corrected rowing fit';
}
if(native){
  document.querySelector('#before h2').textContent='Before · staged recovery';
  document.querySelector('#after h2').textContent='June · flowing recovery';
}
if(boatStudy){
  document.querySelector('h1').textContent='Boat review';
  document.querySelector('#before h2').textContent='Before · block forms';
  document.querySelector('#after h2').textContent='Refined shell and oars';
}
if(diagnostic){
  document.querySelector('#before h2').textContent=bindStudy?'Approved sculpt · uniform scale':'Previous rig · linear skinning';
  document.querySelector('#after h2').textContent=bindStudy?'Previous bind mesh · before animation':'Previous rig · volume-preserving experiment';
  const note=document.createElement('p');
  note.textContent=bindStudy?'No animation. The source has only one uniform scale and a rigid placement. The right shows the proportions and replacement parts already baked into the current rig.':'Same mesh, weights and stroke. This isolates the skinning method; it cannot undo the altered bind shape or replace the hands and shorts.';
  note.style.cssText='margin:0 24px 8px;max-width:90ch;line-height:1.5';
  const link=document.createElement('a');link.href=`?baseline=${bindStudy?'skinning':'bind'}`;
  link.textContent=bindStudy?' Compare skinning methods':' Compare unanimated shapes';
  note.append(link);
  document.querySelector('header').after(note);
}
const views=[];
for(const [id,B,S,R] of [['before',boatStudy?PreviousBoat:bodyPass?Boat:OldBoat,bodyPass?Stroke:OldStroke,bodyPass?PreviousBody:OldRower],['after',Boat,Stroke,reconstruction?ReconstructedBody:Rower]]) {
  const box=document.getElementById(id),scene=new THREE.Scene();
  scene.background=new THREE.Color('#e9e6dc');
  const renderer=new THREE.WebGLRenderer({antialias:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));box.append(renderer.domElement);
  const camera=new THREE.PerspectiveCamera(35,1,.01,100);
  const controls=new OrbitControls(camera,renderer.domElement);
  const light=new THREE.DirectionalLight(0xfff2df,2.4);light.position.set(-3,5,3);scene.add(light);
  scene.add(new THREE.HemisphereLight(0xe7f2f5,0x73806c,2));
  const boat=new B(scene),stroke=new S(),rower=boatStudy?{ready:true,update(){}}:native
    ? new PreviousBody(scene,`validation/reconstruction/fresh-rig/${id==='before'?'pre-recovery-fix/june':'june'}.glb`)
    : bindStudy ? new BindBody(scene,id==='before') : skinning
    ? new PreviousBody(scene,'validation/reconstruction/rigged/june.glb',id==='after') : reconstruction && id==='before'
    ? new PreviousBody(scene,'validation/reconstruction/rig-fit-before/june.glb') : new R(scene);
  if(bindStudy)boat.group.visible=false;
  views.push({box,scene,renderer,camera,controls,boat,stroke,rower});
}
const select=document.getElementById('character');
for(const c of CHARACTERS) {const o=document.createElement('option');o.value=c.id;o.textContent=c.name;select.add(o);}
select.onchange=()=>views[1].rower.select(select.value);
select.value=bodyPass?'june':'mira';
select.disabled=reconstruction || diagnostic || native || boatStudy;
if(!reconstruction && !diagnostic && !native && !boatStudy)await views[1].rower.select(select.value);
let time=0,playing=false,previous=performance.now();
const slider=document.getElementById('phase');
slider.oninput=()=>{time=Number(slider.value);playing=false;document.getElementById('play').textContent='Play cycle';};
document.getElementById('play').onclick=e=>{playing=!playing;e.target.textContent=playing?'Pause cycle':'Play cycle';};
let followSeat=false,followGrip=false,followHand=false;
function cameraView(position,target) {followSeat=false;followGrip=false;followHand=false;for(const v of views){v.camera.position.set(...position);v.controls.target.set(...target);v.controls.update();}}
function bodyView(offset,height=.75) {
  const x=views[1].stroke.pose().seat;
  cameraView([x+offset[0],offset[1],offset[2]],[x,height,0]);followSeat=true;
}
document.getElementById('side').onclick=()=>bodyView([0,1.1,3]);
document.getElementById('front').onclick=()=>bodyView([-3,1.4,.2]);
document.getElementById('grip').onclick=()=>{cameraView([0,1.1,1.25],[0,0,0]);followGrip=true;};
document.getElementById('hand').onclick=()=>{const p=views[1].boat.handL;cameraView([p.x+.18,p.y+.18,p.z+.50],p.toArray());followHand=true;};
if(native)document.getElementById('thumb').onclick=()=>{
  const p=views[1].boat.handL;
  const q=views[1].rower.model.getObjectByName('handL').getWorldQuaternion(new THREE.Quaternion());
  const eye=new THREE.Vector3(.42,-.1,.24).applyQuaternion(q).add(p);
  cameraView(eye.toArray(),p.toArray());followHand=true;
};
document.getElementById('rear').onclick=()=>bodyView([2,1.2,1.8]);
document.getElementById('torso').onclick=()=>bodyView([0,.92,1.8]);
document.getElementById('shoulders').onclick=()=>bodyView([1.7,1.05,0],.82);
document.getElementById('face').onclick=()=>cameraView([-1.25,1.35,.45],[-.09,1.15,0]);
document.getElementById('feet').onclick=()=>cameraView([-1.15,.8,.65],[-.46,.28,0]);
document.getElementById('knees').onclick=()=>cameraView([-.85,.95,1.25],[-.32,.46,0]);
document.getElementById('seat').onclick=()=>{const x=views[1].stroke.pose().seat;cameraView([x-.55,.48,.85],[x,.36,0]);followSeat=true;};
bodyView([-.7,1.15,3],.65);
if(baseline==='seat')document.getElementById('seat').click();
if(baseline==='sculpt')document.getElementById('face').click();
if(bindStudy){
  slider.disabled=true;document.getElementById('play').disabled=true;
  for(const id of ['grip','feet','knees','seat','shoulders','hand'])document.getElementById(id).hidden=true;
  document.getElementById('side').onclick=()=>cameraView([0,.5,3.5],[0,.45,0]);
  document.getElementById('front').onclick=()=>cameraView([-3.5,.5,0],[0,.45,0]);
  document.getElementById('rear').onclick=()=>cameraView([3.5,.5,0],[0,.45,0]);
  document.getElementById('torso').onclick=()=>cameraView([0,.9,1.8],[0,.8,0]);
  document.getElementById('front').click();
}
if(boatStudy){
  for(const id of ['front','grip','rear','face','feet','knees','seat','torso','shoulders','hand'])document.getElementById(id).hidden=true;
  document.getElementById('side').onclick=()=>cameraView([0,2,12],[0,.1,0]);
  document.getElementById('shell').onclick=()=>cameraView([7,7,10],[0,.1,0]);
  document.getElementById('cockpit').onclick=()=>cameraView([1.7,2.6,2.2],[-.05,.22,0]);
  document.getElementById('blade').onclick=()=>{
    time=.65;
    for(const v of views){v.stroke.mode='drive';v.stroke.p=time;v.boat.setPose(fitRowingPose(v.stroke.pose(),'june'));}
    const p=views[1].boat.bladeL;
    cameraView([p.x-.65,p.y+.65,p.z+.7],p.toArray());
  };
  time=.65;document.getElementById('shell').click();
}
function tick(now){
  if(playing){
    const elapsed=time<=1?time*G.driveDur:G.driveDur+(time-1)*G.recDur;
    const next=(elapsed+(now-previous)/1000)%(G.driveDur+G.recDur);
    time=next<=G.driveDur?next/G.driveDur:1+(next-G.driveDur)/G.recDur;
  }
  previous=now;slider.value=time;
  const mode=time<=1?'drive':'rec',p=time<=1?time:time-1;
  document.getElementById('phaseLabel').textContent=bindStudy?'Rest shape':`${mode==='drive'?'Drive':'Recovery'} · ${Math.round(p*100)}%`;
  for(const v of views){
    v.stroke.mode=mode;v.stroke.p=p;
    const character=native || boatStudy || (v.box.id==='after' && reconstruction)?'june':v.rower.character;
    const pose=(native && v.box.id==='before'?fitPreviousGripPose:fitRowingPose)(v.stroke.pose(),character);
    v.boat.setPose(pose);v.rower.update(pose,v.boat.handL,v.boat.handR,0);
    if(v.box.hidden || v.box.clientWidth===0)continue;
    const w=v.box.clientWidth,h=v.box.clientHeight;
    if(v.renderer.domElement.width!==Math.floor(w*v.renderer.getPixelRatio()) || v.renderer.domElement.height!==Math.floor(h*v.renderer.getPixelRatio())){
      v.renderer.setSize(w,h,false);v.camera.aspect=w/h;v.camera.updateProjectionMatrix();
    }
    if(followSeat){v.camera.position.x+=pose.seat-v.controls.target.x;v.controls.target.x=pose.seat;}
    if(followGrip){
      const target=v.boat.handL.clone().add(v.boat.handR).multiplyScalar(.5);
      v.camera.position.add(target.clone().sub(v.controls.target));v.controls.target.copy(target);
    }
    if(followHand){const target=v.boat.handL;v.camera.position.add(target.clone().sub(v.controls.target));v.controls.target.copy(target);}
    v.controls.update();v.renderer.render(v.scene,v.camera);
  }
  document.getElementById('status').textContent=views.every(v=>v.rower.ready)?`${boatStudy?'Both boats':'Both rigs'} loaded · drag to orbit · scroll to zoom`:'Loading rigs…';
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
