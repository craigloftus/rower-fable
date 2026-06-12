import * as THREE from 'three';
import { mat, rng } from './util.js';
import { jitterGeo, makeTree, GREENS, DARKGREENS } from './scenery.js';

// The river: a meandering centreline parameterised by distance rowed (s).
// The boat travels through a static world; bank scenery is generated in
// deterministic chunks around the visible stretch and discarded behind.

export const RIVER_HALF = 15;   // centreline to bank waterline, metres
const CHUNK = 120;
const VIEW_AHEAD = 540;
const VIEW_BEHIND = 160;
const MARKER_EVERY = 100;
const START = 300;              // river behind the start line, so 0 m isn't a lake edge

// ----------------------------------------------------------- centreline ----
// gentle heading meanders; min turn radius ~180 m so an 8 m shell looks fine
const heading = (s) => 0.38 * Math.sin(s * 0.012 + 1.3) + 0.20 * Math.sin(s * 0.0047);

const STEP = 2;
const lut = [{ x: 0, z: 0 }];
function extend(toS) {
  while ((lut.length - 1) * STEP < toS + STEP) {
    const s = (lut.length - 1) * STEP;
    const th = heading(s + STEP / 2); // midpoint integration
    const p = lut[lut.length - 1];
    lut.push({ x: p.x + Math.cos(th) * STEP, z: p.z - Math.sin(th) * STEP });
  }
}

// position + heading at raw course parameter sw (metres from river source)
function rawFrame(sw, out = {}) {
  if (sw < 0) sw = 0;
  extend(sw);
  const i = Math.min(Math.floor(sw / STEP), lut.length - 2);
  const t = sw / STEP - i;
  const a = lut[i], b = lut[i + 1];
  out.x = a.x + (b.x - a.x) * t;
  out.z = a.z + (b.z - a.z) * t;
  out.th = heading(sw);
  return out;
}

// position + heading at distance rowed; heading is yaw about +Y
export function frame(s, out = {}) {
  return rawFrame(s + START, out);
}

const _f = {};
// lat: signed lateral offset, + to the boat's port side at that point
function place(obj, sw, lat, yaw = 0) {
  rawFrame(sw, _f);
  obj.position.x = _f.x + Math.sin(_f.th) * lat;
  obj.position.z = _f.z + Math.cos(_f.th) * lat;
  obj.rotation.y = _f.th + yaw;
}

// deterministic relief noise keyed on position, so chunk edges always match
const hash = (s, k) => {
  const v = Math.sin(s * 0.137 + k * 7.31) * 437.5853;
  return v - Math.floor(v);
};

// ---------------------------------------------------------------- banks ----
// a ground ribbon following the curve between two lateral offsets
function ribbon(side, s0, s1, latA, latB, yFn, color) {
  const segs = Math.ceil((s1 - s0) / 12);
  const pos = [];
  for (let k = 0; k <= segs; k++) {
    const s = s0 + (s1 - s0) * (k / segs);
    rawFrame(s, _f);
    for (const [lat, edge] of [[latA, 0], [latB, 1]]) {
      const l = side * lat;
      pos.push(_f.x + Math.sin(_f.th) * l, yFn(s, edge), _f.z + Math.cos(_f.th) * l);
    }
  }
  const idx = [];
  for (let k = 0; k < segs; k++) {
    const i = k * 2;
    idx.push(i, i + 1, i + 2, i + 1, i + 3, i + 2);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return new THREE.Mesh(g, mat(color, { side: THREE.DoubleSide }));
}

// reeds are instanced: one mesh per chunk keeps draw calls sane
const reedGeo = new THREE.ConeGeometry(0.045, 1, 4);
reedGeo.translate(0, 0.5, 0);
const reedMat = mat(0x87a06b);
const _m4 = new THREE.Matrix4();
const _q4 = new THREE.Quaternion();
const _e4 = new THREE.Euler();
const _s4 = new THREE.Vector3();
const _p4 = new THREE.Vector3();

function buildChunk(ci) {
  const r = rng(4242 + ci * 131);
  const g = new THREE.Group();
  const s0 = ci * CHUNK, s1 = s0 + CHUNK;
  const W = RIVER_HALF;
  const reedXf = [];

  for (const side of [-1, 1]) {
    // shore slope rises out of the water, then the near shelf and far band;
    // shared edge expressions keep everything continuous across chunks
    const shoreTop = (s) => 0.34 + hash(s, side + 2) * 0.22;
    const shelfTop = (s) => 1.5 + hash(s, side) * 1.4;
    g.add(ribbon(side, s0, s1, W - 4.5, W - 1,
      (s, edge) => edge ? shoreTop(s) : -0.55, 0x7da25e));
    g.add(ribbon(side, s0, s1, W - 1, W + 42,
      (s, edge) => edge ? shelfTop(s) : shoreTop(s), 0x86ac63));
    g.add(ribbon(side, s0, s1, W + 42, W + 150,
      (s, edge) => edge ? 4.0 + hash(s, side + 4) * 3.0 : shelfTop(s), 0x6f9d57));

    // bank mounds
    for (let i = 0; i < 4; i++) {
      const mound = new THREE.Mesh(
        jitterGeo(new THREE.IcosahedronGeometry(1, 1), r, 0.18),
        mat(GREENS[(r() * GREENS.length) | 0]));
      mound.scale.set(9 + r() * 10, 2.2 + r() * 2.6, 5 + r() * 5);
      place(mound, s0 + (i + r() * 0.9) * (CHUNK / 4), side * (W + 5 + r() * 12), r() * Math.PI);
      mound.position.y = -0.5;
      g.add(mound);
    }
    // darker band behind for depth
    for (let i = 0; i < 3; i++) {
      const mound = new THREE.Mesh(
        jitterGeo(new THREE.IcosahedronGeometry(1, 1), r, 0.2),
        mat(DARKGREENS[(r() * DARKGREENS.length) | 0]));
      mound.scale.set(20 + r() * 20, 5 + r() * 6, 12 + r() * 10);
      place(mound, s0 + (i + r()) * (CHUNK / 3), side * (W + 45 + r() * 40));
      mound.position.y = -0.8;
      g.add(mound);
    }
    // trees: a couple of denser groves plus scattered singles
    const grove = [s0 + r() * CHUNK, s0 + r() * CHUNK];
    for (let i = 0; i < 8; i++) {
      const tree = makeTree(r, 1.6 + r() * 2.4);
      const sT = i < 5
        ? grove[i % 2] + (r() - 0.5) * 22
        : s0 + r() * CHUNK;
      place(tree, sT, side * (W + 3.5 + r() * 24), r() * Math.PI * 2);
      tree.position.y = 0.5 + r() * 1.5;
      g.add(tree);
    }
    // rocks settled into the shore slope, half in the water
    for (let i = 0; i < 4; i++) {
      const rock = new THREE.Mesh(
        jitterGeo(new THREE.IcosahedronGeometry(1, 0), r, 0.3),
        mat(0x8d8f7e));
      rock.scale.setScalar(0.4 + r() * 1.3);
      place(rock, s0 + r() * CHUNK, side * (W - 3 + r() * 3.5));
      rock.position.y = -0.12 * rock.scale.x;
      g.add(rock);
    }
    // reed beds: broad patches rooted in the shallows
    for (let i = 0; i < 4; i++) {
      const sR = s0 + (i + r()) * (CHUNK / 4);
      const latR = W - 3 + r() * 2.5;
      const along = 2.5 + r() * 4, deep = 1.2 + r() * 1.6;
      const n = 12 + (r() * 10) | 0;
      for (let k = 0; k < n; k++) {
        rawFrame(sR + (r() - 0.5) * along, _f);
        const l = side * (latR + (r() - 0.5) * deep);
        _p4.set(_f.x + Math.sin(_f.th) * l, -0.1 + r() * 0.15, _f.z + Math.cos(_f.th) * l);
        _e4.set((r() - 0.5) * 0.22, r() * Math.PI, (r() - 0.5) * 0.22);
        _q4.setFromEuler(_e4);
        _s4.setScalar(1).y = 0.6 + r() * 0.9;
        reedXf.push(_m4.compose(_p4, _q4, _s4).clone());
      }
    }
  }

  const reeds = new THREE.InstancedMesh(reedGeo, reedMat, reedXf.length);
  for (let i = 0; i < reedXf.length; i++) reeds.setMatrixAt(i, reedXf[i]);
  g.add(reeds);
  return g;
}

function disposeGroup(g) {
  g.traverse((m) => {
    if (!m.isMesh) return;
    if (m.geometry !== reedGeo) m.geometry.dispose();
    if (m.material !== reedMat) m.material.dispose();
  });
}

// -------------------------------------------------------------- markers ----
// subtle floating course markers every 100 m along the centreline; they
// pop (sound via callback) and dissolve as the boat passes
class Markers {
  constructor(parent, onPop) {
    this.parent = parent;
    this.onPop = onPop;
    this.list = [];
    this.next = MARKER_EVERY;
    this.finish = null;
  }

  // the goal line: paper poles with golden pennants either side of the
  // course and a wide ring on the water; dissolves once crossed
  setFinish(s) {
    if (this.finish) this.disposeFinish();
    if (s == null) return;
    const g = new THREE.Group();
    const fade = [];
    const poleM = new THREE.MeshStandardMaterial({
      color: 0xf2efe4, roughness: 0.9, flatShading: true, transparent: true,
    });
    const flagM = new THREE.MeshStandardMaterial({
      color: 0xf2c87e, roughness: 0.8, flatShading: true, transparent: true,
    });
    const flags = [];
    for (const sd of [-1, 1]) {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.028, 1.5, 6), poleM);
      pole.position.set(0, 0.72, sd * 4);
      g.add(pole);
      const flag = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.13, 0.30), flagM);
      flag.position.set(0, 1.36, sd * (4 - 0.17));
      g.add(flag);
      flags.push(flag);
    }
    const ringM = new THREE.MeshBasicMaterial({
      color: 0xf2c87e, transparent: true, opacity: 0.30, depthWrite: false,
    });
    const ringGeo = new THREE.RingGeometry(3.4, 3.75, 36);
    ringGeo.rotateX(-Math.PI / 2);
    const ring = new THREE.Mesh(ringGeo, ringM);
    ring.position.y = 0.05;
    g.add(ring);
    fade.push({ m: poleM, base: 1 }, { m: flagM, base: 1 }, { m: ringM, base: 0.30 });
    place(g, s + START, 0);
    this.parent.add(g);
    this.finish = { g, s, flags, fade, pop: -1 };
  }

  disposeFinish() {
    this.parent.remove(this.finish.g);
    this.finish.g.traverse((m) => { if (m.isMesh) m.geometry.dispose(); });
    for (const f of this.finish.fade) f.m.dispose();
    this.finish = null;
  }

  spawn(s) {
    const g = new THREE.Group();
    const ringM = new THREE.MeshBasicMaterial({
      color: 0xfdf6e3, transparent: true, opacity: 0.32, depthWrite: false,
    });
    const ringGeo = new THREE.RingGeometry(0.95, 1.14, 24);
    ringGeo.rotateX(-Math.PI / 2);
    const ring = new THREE.Mesh(ringGeo, ringM);
    ring.position.y = 0.05;
    g.add(ring);
    const gemM = new THREE.MeshBasicMaterial({
      color: 0xf2c87e, transparent: true, opacity: 0.85, depthWrite: false,
    });
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.16, 0), gemM);
    gem.position.y = 0.5;
    g.add(gem);
    place(g, s + START, 0);
    this.parent.add(g);
    this.list.push({ g, gem, ring, s, pop: -1, phase: s * 0.7 });
  }

  update(dt, dist, time) {
    while (this.next < dist + VIEW_AHEAD) { this.spawn(this.next); this.next += MARKER_EVERY; }
    if (this.finish) {
      const f = this.finish;
      if (f.pop < 0) {
        for (const fl of f.flags) fl.rotation.x = Math.sin(time * 2.2 + fl.position.z) * 0.14;
        if (dist >= f.s - 1.5) { f.pop = 0; this.onPop?.(f.g.position); }
      } else {
        f.pop += dt;
        const k = f.pop / 0.9;
        if (k >= 1) this.disposeFinish();
        else {
          f.g.position.y = k * 0.8;
          for (const fd of f.fade) fd.m.opacity = fd.base * (1 - k);
        }
      }
    }
    for (let i = this.list.length - 1; i >= 0; i--) {
      const m = this.list[i];
      if (m.pop < 0) {
        m.gem.position.y = 0.5 + Math.sin(time * 1.5 + m.phase) * 0.06;
        m.gem.rotation.y = time * 0.8 + m.phase;
        if (dist >= m.s - 1.5) {
          m.pop = 0;
          this.onPop?.(m.g.position);
        }
      } else {
        m.pop += dt;
        const k = m.pop / 0.55;
        if (k >= 1) {
          this.parent.remove(m.g);
          m.gem.geometry.dispose(); m.gem.material.dispose();
          m.ring.geometry.dispose(); m.ring.material.dispose();
          this.list.splice(i, 1);
          continue;
        }
        m.gem.position.y = 0.5 + k * 0.5;
        m.gem.scale.setScalar(1 + k * 1.3);
        m.gem.material.opacity = 0.85 * (1 - k);
        m.ring.scale.setScalar(1 + k * 1.6);
        m.ring.material.opacity = 0.32 * (1 - k);
      }
    }
  }

  reset() {
    for (const m of this.list) {
      this.parent.remove(m.g);
      m.gem.geometry.dispose(); m.gem.material.dispose();
      m.ring.geometry.dispose(); m.ring.material.dispose();
    }
    this.list = [];
    this.next = MARKER_EVERY;
    if (this.finish) this.disposeFinish();
  }
}

// --------------------------------------------------------------- course ----
export class Course {
  constructor(scene, onMarker) {
    this.group = new THREE.Group();
    scene.add(this.group);
    this.chunks = new Map();
    this.markers = new Markers(this.group, onMarker);
  }

  update(dt, dist, time) {
    const sw = dist + START;
    const lo = Math.max(0, Math.floor((sw - VIEW_BEHIND) / CHUNK));
    const hi = Math.floor((sw + VIEW_AHEAD) / CHUNK);
    for (let i = lo; i <= hi; i++) {
      if (!this.chunks.has(i)) {
        const c = buildChunk(i);
        this.chunks.set(i, c);
        this.group.add(c);
      }
    }
    for (const [i, c] of this.chunks) {
      if (i < lo || i > hi) {
        this.group.remove(c);
        disposeGroup(c);
        this.chunks.delete(i);
      }
    }
    this.markers.update(dt, dist, time);
  }

  // place (or clear, with null) the goal-line marker at a distance rowed
  setFinish(dist) {
    this.markers.setFinish(dist);
  }

  reset() {
    this.markers.reset();
  }
}
