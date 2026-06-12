import * as THREE from 'three';
import { mat, rng } from './util.js';
import { jitterGeo } from './scenery.js';

export const FOG_COLOR = 0xdfe5d4;

// ---------------------------------------------------------------- water ----
// CPU-cheap GPU water: sine displacement in the vertex shader, flat-facet
// normals from screen-space derivatives in the fragment shader. Waves are
// computed from world-space position, so the plane can be recentred on the
// boat each frame without the pattern swimming.
function makeWater(scene) {
  const geo = new THREE.PlaneGeometry(1000, 1000, 150, 150);
  geo.rotateX(-Math.PI / 2);
  const uniforms = {
    uTime: { value: 0 },
    uDeep: { value: new THREE.Color(0x2f6470) },
    uShallow: { value: new THREE.Color(0x6fa8a4) },
    uSky: { value: new THREE.Color(0xcfe3da) },
    uSunDir: { value: new THREE.Vector3(-0.5, 0.75, 0.35).normalize() },
    uFogColor: { value: new THREE.Color(FOG_COLOR) },
    uFogNear: { value: 120 },
    uFogFar: { value: 620 },
  };
  const matw = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: /* glsl */`
      uniform float uTime;
      varying vec3 vW;
      void main(){
        vec4 w = modelMatrix * vec4(position, 1.0);
        float X = w.x;
        float Z = w.z;
        w.y +=
          0.036*sin(X*0.11045 + Z*0.21  + uTime*0.9)
        + 0.050*sin(X*0.04909 - Z*0.117 + uTime*0.55)
        + 0.030*sin(X*0.28225 + Z*0.04  - uTime*1.25)
        + 0.016*sin(X*0.49087 - Z*0.36  + uTime*1.7);
        vW = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uDeep, uShallow, uSky, uSunDir, uFogColor;
      uniform float uFogNear, uFogFar;
      varying vec3 vW;
      void main(){
        vec3 n = normalize(cross(dFdx(vW), dFdy(vW)));
        if (n.y < 0.0) n = -n;
        float diff = clamp(dot(n, uSunDir), 0.0, 1.0);
        vec3 col = mix(uDeep, uShallow, 0.22 + 0.78*diff);
        vec3 vdir = normalize(cameraPosition - vW);
        float fres = pow(1.0 - clamp(dot(n, vdir), 0.0, 1.0), 2.5);
        col = mix(col, uSky, fres*0.7);
        vec3 r = reflect(-uSunDir, n);
        float spec = pow(clamp(dot(r, vdir), 0.0, 1.0), 90.0);
        col += vec3(1.0, 0.95, 0.82) * spec * 0.45;
        float fog = smoothstep(uFogNear, uFogFar, distance(cameraPosition, vW));
        col = mix(col, uFogColor, fog);
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  const mesh = new THREE.Mesh(geo, matw);
  mesh.frustumCulled = false;
  scene.add(mesh);
  return { uniforms, mesh };
}

// ------------------------------------------------------------------ sky ----
function makeSky(scene) {
  const geo = new THREE.SphereGeometry(700, 24, 14);
  const m = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      uTop: { value: new THREE.Color(0x6fa3c4) },
      uMid: { value: new THREE.Color(0xa8c8cf) },
      uHorizon: { value: new THREE.Color(FOG_COLOR) },
      uSunDir: { value: new THREE.Vector3(-0.5, 0.75, 0.35).normalize() },
    },
    vertexShader: /* glsl */`
      varying vec3 vP;
      void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: /* glsl */`
      uniform vec3 uTop, uMid, uHorizon, uSunDir;
      varying vec3 vP;
      void main(){
        vec3 d = normalize(vP);
        float h = d.y;
        vec3 col = mix(uHorizon, uMid, smoothstep(-0.02, 0.18, h));
        col = mix(col, uTop, smoothstep(0.15, 0.65, h));
        float s = clamp(dot(d, uSunDir), 0.0, 1.0);
        col += vec3(1.0, 0.9, 0.7) * (pow(s, 350.0)*0.5 + pow(s, 8.0)*0.10);
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  const mesh = new THREE.Mesh(geo, m);
  mesh.frustumCulled = false;
  scene.add(mesh);
  return mesh;
}

// ------------------------------------------------------------- backdrop ----
function makeMountains(scene) {
  const r = rng(99);
  const g = new THREE.Group();
  for (let i = 0; i < 14; i++) {
    let a = r() * Math.PI * 2;
    // keep fore/aft corridors clear so the river reads as long
    if (Math.abs(Math.sin(a)) < 0.3) a += 0.45;
    const dist = 240 + r() * 90;
    const h = 45 + r() * 75;
    const base = 40 + r() * 40;
    const geo = jitterGeo(new THREE.ConeGeometry(base, h, 6 + ((r() * 3) | 0)), r, 0.24);
    const peak = new THREE.Mesh(geo, mat(0x5f6b76));
    peak.position.set(Math.cos(a) * dist, h * 0.42, Math.sin(a) * dist);
    peak.rotation.y = r() * Math.PI;
    g.add(peak);
  }
  // nearer green hills
  for (let i = 0; i < 8; i++) {
    let a = r() * Math.PI * 2;
    if (Math.abs(Math.sin(a)) < 0.35) a += 0.5;
    const dist = 160 + r() * 60;
    const hill = new THREE.Mesh(jitterGeo(new THREE.IcosahedronGeometry(1, 1), r, 0.15), mat(0x7a9a64));
    hill.scale.set(40 + r() * 35, 12 + r() * 14, 30 + r() * 25);
    hill.position.set(Math.cos(a) * dist, -2, Math.sin(a) * dist);
    g.add(hill);
  }
  scene.add(g);
  return g;
}

function makeClouds(scene) {
  const r = rng(7);
  const cm = mat(0xf4f6ef, { roughness: 1 });
  const g = new THREE.Group();
  const clouds = [];
  for (let i = 0; i < 8; i++) {
    const c = new THREE.Group();
    const n = 2 + ((r() * 3) | 0);
    for (let k = 0; k < n; k++) {
      const blob = new THREE.Mesh(new THREE.IcosahedronGeometry(6 + r() * 9, 1), cm);
      blob.scale.set(1.6, 0.45, 1);
      blob.position.set(k * 9 + (r() - 0.5) * 6, (r() - 0.5) * 3, (r() - 0.5) * 6);
      c.add(blob);
    }
    const a = r() * Math.PI * 2;
    const d = 120 + r() * 160;
    c.position.set(Math.cos(a) * d, 55 + r() * 55, Math.sin(a) * d);
    g.add(c);
    clouds.push(c);
  }
  scene.add(g);
  return { group: g, clouds };
}

// ---------------------------------------------------------------- FX -------
class FXPools {
  constructor(scene) {
    this.scene = scene;
    this.splashes = [];
    const sGeo = new THREE.OctahedronGeometry(0.035, 0);
    const sMat = mat(0xeef4ee, { roughness: 0.5 });
    for (let i = 0; i < 90; i++) {
      const m = new THREE.Mesh(sGeo, sMat.clone());
      m.visible = false;
      m.material.transparent = true;
      scene.add(m);
      this.splashes.push({ m, vel: new THREE.Vector3(), life: 0, max: 1 });
    }
    this.rings = [];
    const rGeo = new THREE.RingGeometry(0.82, 1.0, 18);
    rGeo.rotateX(-Math.PI / 2);
    for (let i = 0; i < 24; i++) {
      const m = new THREE.Mesh(rGeo, new THREE.MeshBasicMaterial({
        color: 0xdfeee6, transparent: true, opacity: 0, depthWrite: false,
      }));
      m.visible = false;
      scene.add(m);
      this.rings.push({ m, life: 0, max: 1, grow: 1 });
    }
  }

  splash(pos, n, power) {
    for (let i = 0; i < n; i++) {
      const p = this.splashes.find(s => !s.m.visible);
      if (!p) return;
      p.m.visible = true;
      p.m.position.copy(pos);
      p.m.position.y += 0.02;
      p.m.scale.setScalar(0.6 + Math.random() * 0.9);
      p.vel.set((Math.random() - 0.5) * 1.6 * power,
        (0.9 + Math.random() * 1.6) * power,
        (Math.random() - 0.5) * 1.6 * power);
      p.life = p.max = 0.5 + Math.random() * 0.35;
    }
  }

  ring(pos, scale, grow, life = 2.0) {
    const p = this.rings.find(s => !s.m.visible);
    if (!p) return;
    p.m.visible = true;
    p.m.position.set(pos.x, 0.03, pos.z);
    p.m.scale.setScalar(scale);
    p.grow = grow;
    p.life = p.max = life;
  }

  // splashes and rings are water-fixed; the boat moves through them
  update(dt) {
    for (const p of this.splashes) {
      if (!p.m.visible) continue;
      p.life -= dt;
      if (p.life <= 0) { p.m.visible = false; continue; }
      p.vel.y -= 5.5 * dt;
      p.m.position.addScaledVector(p.vel, dt);
      p.m.material.opacity = Math.min(1, p.life / p.max * 1.6);
      if (p.m.position.y < -0.15) p.m.visible = false;
    }
    for (const p of this.rings) {
      if (!p.m.visible) continue;
      p.life -= dt;
      if (p.life <= 0) { p.m.visible = false; continue; }
      const t = 1 - p.life / p.max;
      p.m.scale.setScalar(p.m.scale.x + p.grow * dt);
      p.m.material.opacity = 0.55 * (1 - t) * (1 - t);
    }
  }
}

// ---------------------------------------------------------------- world ----
// Water, sky, distant mountains and clouds are a backdrop that recentres on
// the boat each frame; the riverbanks themselves live in course.js.
export class World {
  constructor(scene) {
    this.water = makeWater(scene);
    this.sky = makeSky(scene);
    this.mountains = makeMountains(scene);
    this.cloudsG = makeClouds(scene);
    this.fx = new FXPools(scene);
    this.time = 0;
  }

  update(dt, anchor) {
    this.time += dt;
    this.water.uniforms.uTime.value = this.time;
    this.water.mesh.position.set(anchor.x, 0, anchor.z);
    this.sky.position.set(anchor.x, 0, anchor.z);
    this.mountains.position.set(anchor.x, 0, anchor.z);
    this.cloudsG.group.position.set(anchor.x, 0, anchor.z);
    for (let i = 0; i < this.cloudsG.clouds.length; i++) {
      const c = this.cloudsG.clouds[i];
      c.position.x -= (0.3 + (i % 3) * 0.18) * dt;
      if (c.position.x < -320) c.position.x = 320;
    }
    this.fx.update(dt);
  }
}
