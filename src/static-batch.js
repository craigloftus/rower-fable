import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// For opaque, untextured scenery only. Keep spatial cells separately culled;
// bake transforms once, retaining every original triangle and facet normal.
export function batchScenery(group, cellSize = Infinity) {
  group.updateWorldMatrix(true, true);
  const inverse = group.matrixWorld.clone().invert();
  const batches = new Map(), originals = new Set();
  group.traverse(mesh => {
    if (!mesh.isMesh) return;
    const transform = new THREE.Matrix4().multiplyMatrices(inverse, mesh.matrixWorld);
    const geo = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry.clone();
    geo.deleteAttribute('uv');
    geo.applyMatrix4(transform);
    geo.computeBoundingBox();
    const center = geo.boundingBox.getCenter(new THREE.Vector3());
    const key = `${mesh.material.uuid}:${Math.floor(center.x / cellSize)}:${Math.floor(center.z / cellSize)}`;
    if (!batches.has(key)) batches.set(key, { material: mesh.material, geometries: [] });
    batches.get(key).geometries.push(geo);
    originals.add(mesh.geometry);
  });
  group.clear();
  for (const { material, geometries } of batches.values()) {
    const merged = mergeGeometries(geometries);
    merged.computeBoundingSphere();
    const mesh = new THREE.Mesh(merged, material);
    mesh.matrixAutoUpdate = false;
    group.add(mesh);
    for (const geometry of geometries) geometry.dispose();
  }
  for (const geometry of originals) geometry.dispose();
  return group;
}
