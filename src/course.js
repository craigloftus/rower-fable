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

const buoyGeo = new THREE.IcosahedronGeometry(0.10, 0);
const buoyMat = mat(0xc97a4a);

function buildChunk(ci) {
  const r = rng(4242 + ci * 131);
  const g = new THREE.Group();
  const s0 = ci * CHUNK, s1 = s0 + CHUNK;
  const W = RIVER_HALF;

  for (const side of [-1, 1]) {
    // near grassy shelf and rising far band, continuous across chunks
    g.add(ribbon(side, s0, s1, W - 3, W + 42,
      (s, edge) => edge ? 1.5 + hash(s, side) * 1.4 : 0.22 + hash(s, side + 2) * 0.25,
      0x86ac63));
    g.add(ribbon(side, s0, s1, W + 42, W + 150,
      (s, edge) => edge ? 4.0 + hash(s, side + 4) * 3.0 : 1.5 + hash(s, side) * 1.4,
      0x6f9d57));

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
    // trees
    for (let i = 0; i < 4; i++) {
      const tree = makeTree(r, 1.8 + r() * 2.2);
      place(tree, s0 + r() * CHUNK, side * (W + 4 + r() * 20), r() * Math.PI * 2);
      tree.position.y = 0.5 + r() * 1.4;
      g.add(tree);
    }
    // rocks at the waterline
    for (let i = 0; i < 3; i++) {
      const rock = new THREE.Mesh(
        jitterGeo(new THREE.IcosahedronGeometry(1, 0), r, 0.3),
        mat(0x8d8f7e));
      rock.scale.setScalar(0.5 + r() * 1.3);
      place(rock, s0 + r() * CHUNK, side * (W - 1.5 + r() * 3));
      rock.position.y = 0;
      g.add(rock);
    }
    // reed clusters
    for (let i = 0; i < 4; i++) {
      const sR = s0 + r() * CHUNK, latR = W - 2 + r() * 2.5;
      for (let k = 0; k < 5; k++) {
        const reed = new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.6 + r() * 0.7, 4), mat(0x87a06b));
        place(reed, sR + (r() - 0.5) * 1.4, side * (latR + (r() - 0.5) * 1.4));
        reed.position.y = 0.28;
        reed.rotation.z = (r() - 0.5) * 0.2;
        g.add(reed);
      }
    }
    // small buoys marking the river edges
    for (let s = s0 + (side > 0 ? 0 : 9); s < s1; s += 18) {
      const b = new THREE.Mesh(buoyGeo, buoyMat);
      place(b, s, side * (W - 2));
      b.position.y = 0.05;
      g.add(b);
    }
  }
  return g;
}

function disposeGroup(g) {
  g.traverse((m) => {
    if (!m.isMesh) return;
    if (m.geometry !== buoyGeo) m.geometry.dispose();
    if (m.material !== buoyMat) m.material.dispose();
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

  reset() {
    this.markers.reset();
  }
}
