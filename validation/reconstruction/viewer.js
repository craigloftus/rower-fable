import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const box = document.querySelector('#viewer');
const renderer = new THREE.WebGLRenderer({antialias: true});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.08;
box.append(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#f0e9db');
const camera = new THREE.PerspectiveCamera(32, 1, .01, 100);
const controls = new OrbitControls(camera, renderer.domElement);
scene.add(new THREE.HemisphereLight(0xfff5e6, 0xbfc2bb, 1.65));
const light = new THREE.DirectionalLight(0xffffff, 3.5);
light.position.set(-3, 4, 5);
scene.add(light);
const clay = new THREE.MeshStandardMaterial({color: '#ac9e89', roughness: .9});
const study = document.querySelector('#study');
const requested = new URLSearchParams(location.search).get('study');
study.value = [...study.options].some(o => o.value === requested) ? requested : 'trellis-assembled';
document.body.classList.toggle('head-study', study.value.endsWith('head'));
study.onchange = () => { location.search = `study=${study.value}`; };

const gltf = await new GLTFLoader().loadAsync(`./${study.value}/mesh.glb?review=${Date.now()}`);
const model = gltf.scene;
if (study.value.startsWith('triposr')) model.rotation.x = -Math.PI / 2;
scene.add(model);
const bounds = new THREE.Box3().setFromObject(model);
const center = bounds.getCenter(new THREE.Vector3());
const height = bounds.getSize(new THREE.Vector3()).y;
model.position.sub(center);
const materials = new Map();
const baseColours = new Map();
let triangles = 0;
model.traverse(o => {
  if (!o.isMesh) return;
  materials.set(o, o.material);
  baseColours.set(o, new THREE.MeshBasicMaterial({
    color: o.material.color, map: o.material.map,
    vertexColors: o.material.vertexColors, side: o.material.side,
    transparent: o.material.transparent, opacity: o.material.opacity,
    alphaTest: o.material.alphaTest, toneMapped: false,
  }));
  triangles += (o.geometry.index?.count ?? o.geometry.attributes.position.count) / 3;
});
const surface = document.querySelector('#surface');
const lightDirection = document.querySelector('#light-direction');
const moveLight = document.querySelector('#move-light');
let movingLight = false, lightAngle = 0;
function updateLight() {
  const angle = Math.atan2(-3, 5) + THREE.MathUtils.degToRad(lightAngle);
  light.position.set(Math.sin(angle) * Math.sqrt(34), 4, Math.cos(angle) * Math.sqrt(34));
}
lightDirection.oninput = () => { lightAngle = Number(lightDirection.value); updateLight(); };
moveLight.onclick = () => {
  movingLight = !movingLight;
  moveLight.textContent = movingLight ? 'Pause light' : 'Move light';
  moveLight.setAttribute('aria-pressed', String(movingLight));
};
surface.onchange = () => {
  for (const [mesh, material] of materials) {
    mesh.material = surface.value === 'clay' ? clay : surface.value === 'base' ? baseColours.get(mesh) : material;
  }
  lightDirection.disabled = moveLight.disabled = surface.value === 'base';
  updateStatus();
};
let focusHeight=height, focusY=0;
function view(angle) {
  camera.position.set(Math.cos(angle) * focusHeight * 2.2, focusY + focusHeight * .02, Math.sin(angle) * focusHeight * 2.2);
  controls.target.set(0, focusY, 0);
  controls.update();
}
const inputAngle = (study.value.startsWith('trellis') || study.value.startsWith('june-')) ? Math.PI / 2 + Math.PI / 8 : 0;
document.querySelector('#front').onclick = () => view(inputAngle);
document.querySelector('#side').onclick = () => view((study.value.startsWith('trellis') || study.value.startsWith('june-')) ? Math.PI : inputAngle + Math.PI / 2);
document.querySelector('#rear').onclick = () => view(-Math.PI/2);
const neckButton=document.querySelector('#neck');
const armsButton=document.querySelector('#arms');
neckButton.disabled=!['trellis-assembled','june-final'].includes(study.value);
armsButton.disabled=neckButton.disabled;
let focus='whole';
function focusOn(part) {
  focus = focus === part ? 'whole' : part;
  document.body.classList.toggle('detail-study',focus === 'neck');
  focusHeight=height*(focus === 'neck' ? .27 : focus === 'arms' ? .38 : 1);
  focusY=focus === 'neck' ? .386-center.y : focus === 'arms' ? .17-center.y : 0;
  neckButton.textContent=focus === 'neck' ? 'Whole character' : 'Neck close-up';
  armsButton.textContent=focus === 'arms' ? 'Whole character' : 'Arms close-up';
  view(inputAngle);
}
neckButton.onclick=()=>focusOn('neck');
armsButton.onclick=()=>focusOn('arms');
view(inputAngle);
function updateStatus() {
  const hint = surface.value === 'base' ? 'Base colours only · no lighting or reflections' : 'Drag to inspect · move the light to check shading';
  document.querySelector('#status').textContent = `${triangles.toLocaleString()} triangles · ${hint}`;
}
updateStatus();
new ResizeObserver(() => {
  const w = box.clientWidth, h = box.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}).observe(box);
let previousTime=performance.now();
renderer.setAnimationLoop(time => {
  const elapsed=Math.min((time-previousTime)/1000,.1);previousTime=time;
  if(movingLight && surface.value !== 'base') {
    lightAngle=(lightAngle+elapsed*30+180)%360-180;
    lightDirection.value=String(Math.round(lightAngle));updateLight();
  }
  controls.update();renderer.render(scene,camera);
});
