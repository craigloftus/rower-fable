import * as THREE from 'three';
import { mat, rng, lerp } from './util.js';

export const FOG_COLOR = 0xdfe5d4;
const TILE = 200;        // shoreline tile length; two variants -> 400 m period
const SCROLL_WRAP = 400;

// ---------------------------------------------------------------- water ----
// CPU-cheap GPU water: sine displacement in the vertex shader, flat-facet
// normals from screen-space derivatives in the fragment shader.
// Wave numbers along X are multiples of 2*pi/512 so the scroll wraps cleanly.
function makeWater(scene) {
  const geo = new THREE.PlaneGeometry(1000, 1000, 150, 150);
  geo.rotateX(-Math.PI / 2);
  const uniforms = {
    uTime: { value: 0 },
    uScroll: { value: 0 },
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
      uniform float uTime; uniform float uScroll;
      varying vec3 vW;
      void main(){
        vec3 p = position;
        float X = p.x + uScroll;
        float Z = p.z;
        p.y =
          0.036*sin(X*0.11045 + Z*0.21  + uTime*0.9)
        + 0.050*sin(X*0.04909 - Z*0.117 + uTime*0.55)
        + 0.030*sin(X*0.28225 + Z*0.04  - uTime*1.25)
        + 0.016*sin(X*0.49087 - Z*0.36  + uTime*1.7);
        vec4 w = modelMatrix * vec4(p, 1.0);
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
  return uniforms;
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
}

// ------------------------------------------------------------- scenery -----
function jitterGeo(geo, r, amt) {
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    pos.setXYZ(i,
      pos.getX(i) * (1 + (r() - 0.5) * amt),
      pos.getY(i) * (1 + (r() - 0.5) * amt),
      pos.getZ(i) * (1 + (r() - 0.5) * amt));
  }
  geo.computeVertexNormals();
  return geo;
}

const GREENS = [0x7ca35f, 0x93b56e, 0x6f9d57, 0x84ad62];
const DARKGREENS = [0x5d8a4c, 0x648f55];

function makeTree(r, scale) {
  const t = new THREE.Group();
  const trunkH = (0.8 + r() * 0.6) * scale;
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.07 * scale, 0.11 * scale, trunkH, 5), mat(0x7a5f48));
  trunk.position.y = trunkH / 2;
  t.add(trunk);
  const n = 2 + ((r() * 2) | 0);
  for (let i = 0; i < n; i++) {
    const fr = (0.55 - i * 0.13 + r() * 0.12) * scale;
    const blob = new THREE.Mesh(
      new THREE.IcosahedronGeometry(fr, 0),
      mat(GREENS[(r() * GREENS.length) | 0]));
    blob.position.set((r() - 0.5) * 0.3 * scale, trunkH + i * fr * 0.95, (r() - 0.5) * 0.3 * scale);
    blob.rotation.y = r() * Math.PI;
    t.add(blob);
  }
  return t;
}

function makeTile(variant) {
  const r = rng(1234 + variant * 777);
  const g = new THREE.Group();

  for (const s of [-1, 1]) {
    // grassy bank mounds
    for (let i = 0; i < 7; i++) {
      const mound = new THREE.Mesh(
        jitterGeo(new THREE.IcosahedronGeometry(1, 1), r, 0.18),
        mat(GREENS[(r() * GREENS.length) | 0]));
      mound.scale.set(16 + r() * 18, 3 + r() * 4, 9 + r() * 9);
      mound.position.set((i + r() * 0.8) * (TILE / 7) - TILE / 2, -0.6, s * (56 + r() * 14));
      g.add(mound);
    }
    // second darker band for depth
    for (let i = 0; i < 5; i++) {
      const mound = new THREE.Mesh(
        jitterGeo(new THREE.IcosahedronGeometry(1, 1), r, 0.2),
        mat(DARKGREENS[(r() * DARKGREENS.length) | 0]));
      mound.scale.set(26 + r() * 26, 6 + r() * 8, 16 + r() * 12);
      mound.position.set((i + r()) * (TILE / 5) - TILE / 2, -0.8, s * (95 + r() * 35));
      g.add(mound);
    }
    // trees on the banks
    for (let i = 0; i < 9; i++) {
      const tree = makeTree(r, 2.2 + r() * 2.6);
      tree.position.set(r() * TILE - TILE / 2, 1.2 + r() * 2.4, s * (50 + r() * 22));
      tree.rotation.y = r() * Math.PI * 2;
      g.add(tree);
    }
    // rocks at the waterline
    for (let i = 0; i < 4; i++) {
      const rock = new THREE.Mesh(
        jitterGeo(new THREE.IcosahedronGeometry(1, 0), r, 0.3),
        mat(0x8d8f7e));
      rock.scale.setScalar(0.6 + r() * 1.6);
      rock.position.set(r() * TILE - TILE / 2, 0, s * (42 + r() * 6));
      g.add(rock);
    }
    // reed clusters
    for (let i = 0; i < 6; i++) {
      const cx = r() * TILE - TILE / 2, cz = s * (40 + r() * 5);
      for (let k = 0; k < 5; k++) {
        const reed = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.7 + r() * 0.7, 4), mat(0x87a06b));
        reed.position.set(cx + (r() - 0.5) * 1.2, 0.3, cz + (r() - 0.5) * 1.2);
        reed.rotation.z = (r() - 0.5) * 0.2;
        g.add(reed);
      }
    }
    // lane buoys
    const buoyGeo = new THREE.IcosahedronGeometry(0.10, 0);
    const buoyMat = mat(0xc97a4a);
    for (let x = 0; x < TILE; x += 12.5) {
      const b = new THREE.Mesh(buoyGeo, buoyMat);
      b.position.set(x - TILE / 2, 0.02, s * 16);
      g.add(b);
    }
  }
  return g;
}

function makeMountains(scene) {
  const r = rng(99);
  const g = new THREE.Group();
  for (let i = 0; i < 14; i++) {
    let a = r() * Math.PI * 2;
    // keep fore/aft corridors clear so the lake reads as long
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
}

function makeClouds(scene) {
  const r = rng(7);
  const cm = mat(0xf4f6ef, { roughness: 1 });
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
    scene.add(c);
    clouds.push(c);
  }
  return clouds;
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

  update(dt, v) {
    for (const p of this.splashes) {
      if (!p.m.visible) continue;
      p.life -= dt;
      if (p.life <= 0) { p.m.visible = false; continue; }
      p.vel.y -= 5.5 * dt;
      p.m.position.addScaledVector(p.vel, dt);
      p.m.position.x -= v * dt; // water-fixed: drifts astern as the boat moves
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
      p.m.position.x -= v * dt;
    }
  }
}

// ---------------------------------------------------------------- world ----
export class World {
  constructor(scene) {
    this.waterU = makeWater(scene);
    makeSky(scene);
    makeMountains(scene);
    this.clouds = makeClouds(scene);

    this.scroll = new THREE.Group();
    scene.add(this.scroll);
    const variants = [makeTile(0), makeTile(1)];
    for (let i = -2; i <= 4; i++) {
      const tile = variants[((i % 2) + 2) % 2].clone();
      tile.position.x = i * TILE;
      this.scroll.add(tile);
    }

    this.fx = new FXPools(scene);
    this.time = 0;
  }

  update(dt, dist, v) {
    this.time += dt;
    this.waterU.uTime.value = this.time;
    this.waterU.uScroll.value = dist % 512;
    this.scroll.position.x = -(dist % SCROLL_WRAP);
    for (let i = 0; i < this.clouds.length; i++) {
      this.clouds[i].position.x -= (0.3 + (i % 3) * 0.18) * dt;
      if (this.clouds[i].position.x < -320) this.clouds[i].position.x = 320;
    }
    this.fx.update(dt, v);
  }
}
