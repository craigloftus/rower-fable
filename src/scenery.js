import * as THREE from 'three';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { mat } from './util.js';

export const GREENS = [0x7ca35f, 0x93b56e, 0x6f9d57, 0x84ad62];
export const DARKGREENS = [0x5d8a4c, 0x648f55];

// scenery is rebuilt as the course streams past, so share one material per
// colour instead of allocating per mesh (never dispose these)
const matCache = new Map();
export function cmat(color) {
  let m = matCache.get(color);
  if (!m) { m = mat(color); matCache.set(color, m); }
  return m;
}

// polyhedron/cone geometries duplicate vertices per face; weld them first
// so the jitter moves shared corners together instead of tearing the mesh
export function jitterGeo(geo, r, amt) {
  geo.deleteAttribute('normal');
  geo.deleteAttribute('uv');
  geo = mergeVertices(geo);
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

export function makeTree(r, scale) {
  const t = new THREE.Group();
  const trunkH = (0.8 + r() * 0.6) * scale;
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.07 * scale, 0.11 * scale, trunkH, 5), cmat(0x7a5f48));
  trunk.position.y = trunkH / 2;
  t.add(trunk);
  const n = 2 + ((r() * 2) | 0);
  for (let i = 0; i < n; i++) {
    const fr = (0.55 - i * 0.13 + r() * 0.12) * scale;
    const blob = new THREE.Mesh(
      new THREE.IcosahedronGeometry(fr, 0),
      cmat(GREENS[(r() * GREENS.length) | 0]));
    blob.position.set((r() - 0.5) * 0.3 * scale, trunkH + i * fr * 0.95, (r() - 0.5) * 0.3 * scale);
    blob.rotation.y = r() * Math.PI;
    t.add(blob);
  }
  return t;
}
