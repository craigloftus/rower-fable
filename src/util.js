import * as THREE from 'three';

export const lerp = (a, b, t) => a + (b - a) * t;
export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const smooth = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
export const easeSin = (x) => (1 - Math.cos(Math.PI * clamp(x, 0, 1))) / 2;

// deterministic rng (mulberry32) so scenery tiles are reproducible
export function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s |= 0; s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function mat(color, opts = {}) {
  return new THREE.MeshStandardMaterial({
    color, roughness: 0.92, metalness: 0, flatShading: true, ...opts,
  });
}

const _up = new THREE.Vector3(0, 1, 0);
const _d = new THREE.Vector3();
const _dir = new THREE.Vector3();
const _u = new THREE.Vector3();

// a "limb" is a unit cylinder whose base sits at its origin; setLimb stretches
// it between two joint positions each frame
export function makeLimb(parent, rA, rB, material, seg = 6) {
  const geo = new THREE.CylinderGeometry(rB, rA, 1, seg, 1);
  geo.translate(0, 0.5, 0);
  const m = new THREE.Mesh(geo, material);
  parent.add(m);
  return m;
}

export function setLimb(mesh, a, b) {
  _d.subVectors(b, a);
  const l = Math.max(_d.length(), 1e-4);
  mesh.position.copy(a);
  mesh.scale.set(1, l, 1);
  mesh.quaternion.setFromUnitVectors(_up, _d.normalize());
}

// analytic two-bone IK. A: root joint, T: target, pole: bend hint direction.
// Writes the middle joint to outMid and the (possibly clamped) end to outEnd.
// Allows up to 12% stretch before clamping so hands never visibly detach.
export function ik2(A, T, l1, l2, pole, outMid, outEnd) {
  _d.subVectors(T, A);
  let dist = _d.length();
  const reach = (l1 + l2) * 0.999;
  let s = 1;
  if (dist > reach) {
    s = Math.min(dist / reach, 1.12);
    dist = Math.min(dist, reach * s);
  }
  const L1 = l1 * s, L2 = l2 * s;
  dist = Math.max(dist, Math.abs(L1 - L2) + 1e-3);
  _dir.copy(_d).normalize();
  const a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist);
  const h = Math.sqrt(Math.max(L1 * L1 - a * a, 0));
  _u.copy(pole).addScaledVector(_dir, -pole.dot(_dir));
  if (_u.lengthSq() < 1e-6) _u.set(0, 1, 0);
  _u.normalize();
  outMid.copy(A).addScaledVector(_dir, a).addScaledVector(_u, h);
  outEnd.copy(A).addScaledVector(_dir, dist);
}
