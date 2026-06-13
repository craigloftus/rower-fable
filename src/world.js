import * as THREE from 'three';
import { mat, rng, clamp, lerp } from './util.js';
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
const ROCK_DARK = new THREE.Color(0x4a525c);
const ROCK_LIGHT = new THREE.Color(0x7b8691);
const SNOW = new THREE.Color(0xf1f4f6);
const _fc = new THREE.Color();

// rugged peak: cone with height rings to displace (so slopes bow and ridge
// instead of running straight), coloured per facet — rock shading lighter
// with altitude, snow above a noisy snowline on peaks tall enough to carry it
function peakGeo(r, base, h) {
  let geo = jitterGeo(new THREE.ConeGeometry(base, h, 6 + ((r() * 3) | 0), 4), r, 0.3);
  geo = geo.toNonIndexed(); // per-facet colour needs unshared corners
  const pos = geo.attributes.position;
  const col = new Float32Array(pos.count * 3);
  const snowline = h > 75 ? lerp(0.8, 0.55, (h - 75) / 50) : 2;
  for (let i = 0; i < pos.count; i += 3) {
    const cy = (pos.getY(i) + pos.getY(i + 1) + pos.getY(i + 2)) / 3;
    const t = clamp((cy + h / 2) / h, 0, 1);
    if (t > snowline + (r() - 0.5) * 0.12) {
      _fc.copy(SNOW).offsetHSL(0, 0, (r() - 0.5) * 0.05);
    } else {
      _fc.lerpColors(ROCK_DARK, ROCK_LIGHT, t).offsetHSL(0, 0, (r() - 0.5) * 0.06);
    }
    for (let k = 0; k < 3; k++) col.set([_fc.r, _fc.g, _fc.b], (i + k) * 3);
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  geo.computeVertexNormals();
  return geo;
}

function makeMountains(scene) {
  const r = rng(99);
  const g = new THREE.Group();
  const rock = new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.95, metalness: 0, flatShading: true,
  });
  for (let i = 0; i < 14; i++) {
    let a = r() * Math.PI * 2;
    // keep fore/aft corridors clear so the river reads as long
    if (Math.abs(Math.sin(a)) < 0.3) a += 0.45;
    const dist = 240 + r() * 90;
    const h = 45 + r() * 75;
    const base = 40 + r() * 40;
    const massif = new THREE.Group();
    const peak = new THREE.Mesh(peakGeo(r, base, h), rock);
    peak.position.y = h * 0.42;
    peak.rotation.y = r() * Math.PI;
    massif.add(peak);
    // shoulder peaks break the lone-triangle silhouette
    const shoulders = 1 + ((r() * 2) | 0);
    for (let s = 0; s < shoulders; s++) {
      const sh = h * (0.4 + r() * 0.3);
      const sb = base * (0.5 + r() * 0.3);
      const sa = r() * Math.PI * 2;
      const shoulder = new THREE.Mesh(peakGeo(r, sb, sh), rock);
      shoulder.position.set(
        Math.cos(sa) * base * (0.6 + r() * 0.4), sh * 0.38,
        Math.sin(sa) * base * (0.6 + r() * 0.4));
      shoulder.rotation.y = r() * Math.PI;
      massif.add(shoulder);
    }
    massif.position.set(Math.cos(a) * dist, 0, Math.sin(a) * dist);
    g.add(massif);
  }
  // nearer green hills
  const hillMats = [mat(0x7a9a64), mat(0x88a868)];
  for (let i = 0; i < 8; i++) {
    let a = r() * Math.PI * 2;
    if (Math.abs(Math.sin(a)) < 0.35) a += 0.5;
    const dist = 160 + r() * 60;
    const hill = new THREE.Mesh(
      jitterGeo(new THREE.IcosahedronGeometry(1, 1), r, 0.15), hillMats[i % 2]);
    hill.scale.set(40 + r() * 35, 12 + r() * 14, 30 + r() * 25);
    hill.position.set(Math.cos(a) * dist, -2, Math.sin(a) * dist);
    g.add(hill);
  }
  scene.add(g);
  return g;
}

// puff with a flattened underside so clouds read as cumulus, not saucers
function puffGeo(r, rad) {
  const geo = jitterGeo(new THREE.IcosahedronGeometry(rad, 1), r, 0.22);
  const pos = geo.attributes.position;
  const floor = -rad * 0.32;
  for (let i = 0; i < pos.count; i++) {
    if (pos.getY(i) < floor) pos.setY(i, floor + (r() - 0.5) * rad * 0.05);
  }
  geo.computeVertexNormals();
  return geo;
}

function makeClouds(scene) {
  const r = rng(7);
  // emissive lift keeps the shaded undersides white instead of picking up
  // the green ground bounce from the hemisphere light
  const cm = mat(0xfbfdff, { roughness: 1, emissive: 0x8d99a4, emissiveIntensity: 0.22 });
  const g = new THREE.Group();
  const clouds = [];
  for (let i = 0; i < 20; i++) {
    const c = new THREE.Group();
    const n = 3 + ((r() * 3) | 0);
    const rad = 5 + r() * 5;
    for (let k = 0; k < n; k++) {
      // big puffs amidships, smaller toward the ends, bases on one plane
      const t = k / (n - 1);
      const pr = rad * (0.55 + Math.sin(t * Math.PI) * 0.45) * (0.9 + r() * 0.2);
      const puff = new THREE.Mesh(puffGeo(r, pr), cm);
      puff.scale.set(1.15, 0.62 + r() * 0.16, 0.9 + r() * 0.25);
      puff.position.set(
        (t - 0.5) * n * rad * 1.05 + (r() - 0.5) * rad * 0.4,
        pr * 0.32 * puff.scale.y,
        (r() - 0.5) * rad * 0.8);
      puff.rotation.y = r() * Math.PI;
      c.add(puff);
      // the odd topper puff gives the middle some cumulus height
      if (k > 0 && k < n - 1 && r() < 0.55) {
        const tr = pr * (0.45 + r() * 0.25);
        const top = new THREE.Mesh(puffGeo(r, tr), cm);
        top.position.set(puff.position.x + (r() - 0.5) * pr * 0.6,
          pr * 0.75, (r() - 0.5) * pr * 0.5);
        top.rotation.y = r() * Math.PI;
        c.add(top);
      }
    }
    const a = r() * Math.PI * 2;
    const d = 120 + r() * 160;
    c.position.set(Math.cos(a) * d, 50 + r() * 60, Math.sin(a) * d);
    c.scale.setScalar(0.8 + r() * 0.6);
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
