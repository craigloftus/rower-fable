import * as THREE from 'three';
import { mat } from './util.js';

// Only typed geometry buffers cross the worker boundary; no JSON vertices.
export function packChunk(group) {
  return group.children.map(mesh => ({
    color: mesh.material.color.getHex(), side: mesh.material.side,
    attributes: Object.fromEntries(Object.entries(mesh.geometry.attributes)
      .filter(([name]) => name !== 'uv')
      .map(([name, attr]) => [name, { array: attr.array.slice(), itemSize: attr.itemSize }])),
    index: mesh.geometry.index?.array.slice(),
    instances: mesh.isInstancedMesh ? mesh.instanceMatrix.array.slice() : null,
  }));
}
export function chunkTransfers(parts) {
  return parts.flatMap(part => [
    ...Object.values(part.attributes).map(attr => attr.array.buffer),
    ...(part.index ? [part.index.buffer] : []),
    ...(part.instances ? [part.instances.buffer] : []),
  ]);
}
const materials = new Map();
export function unpackChunk(parts) {
  const group = new THREE.Group();
  for (const part of parts) {
    const key = `${part.color}:${part.side}`;
    if (!materials.has(key)) materials.set(key, mat(part.color, { side: part.side }));
    const geometry = new THREE.BufferGeometry();
    for (const [name, attr] of Object.entries(part.attributes)) {
      geometry.setAttribute(name, new THREE.BufferAttribute(attr.array, attr.itemSize));
    }
    if (part.index) geometry.setIndex(new THREE.BufferAttribute(part.index, 1));
    const material = materials.get(key);
    const mesh = part.instances
      ? new THREE.InstancedMesh(geometry, material, part.instances.length / 16)
      : new THREE.Mesh(geometry, material);
    if (part.instances) mesh.instanceMatrix.array.set(part.instances);
    mesh.matrixAutoUpdate = false;
    group.add(mesh);
  }
  return group;
}
