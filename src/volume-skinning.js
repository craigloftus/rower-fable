// Dual-quaternion skinning for the native-proportion Blender rig.
// Its deform bones are rigid: no animated scale or per-bone mesh resizing.
import { Matrix4, Quaternion, Vector3, Vector4 } from 'three';

export function makePalette(skeleton) {
  const real = skeleton.bones.map(() => new Vector4());
  const dual = skeleton.bones.map(() => new Vector4());
  const matrix = new Matrix4(), rotation = new Quaternion(), translation = new Quaternion();
  function update() {
    skeleton.bones.forEach((bone, i) => {
      matrix.multiplyMatrices(bone.matrixWorld, skeleton.boneInverses[i]);
      rotation.setFromRotationMatrix(matrix).normalize();
      const e = matrix.elements;
      translation.set(e[12], e[13], e[14], 0).multiply(rotation);
      real[i].set(rotation.x, rotation.y, rotation.z, rotation.w);
      dual[i].set(translation.x, translation.y, translation.z, translation.w).multiplyScalar(.5);
    });
  }
  return { real, dual, update };
}

const rotation = new Quaternion(), translation = new Quaternion();
const real = new Vector4(), dual = new Vector4(), local = new Vector3();
export function deformPoint(mesh, palette, index, point, normal) {
  const { skinIndex, skinWeight } = mesh.geometry.attributes;
  const offset = index * 4, reference = palette.real[skinIndex.array[offset]];
  real.set(0, 0, 0, 0); dual.set(0, 0, 0, 0);
  for (let j = 0; j < 4; j++) {
    const bone = skinIndex.array[offset + j];
    const w = skinWeight.array[offset + j] * (reference.dot(palette.real[bone]) < 0 ? -1 : 1);
    real.addScaledVector(palette.real[bone], w);
    dual.addScaledVector(palette.dual[bone], w);
  }
  const length = real.length(); real.divideScalar(length); dual.divideScalar(length);
  rotation.set(real.x, real.y, real.z, real.w);
  translation.set(dual.x, dual.y, dual.z, dual.w).multiply(rotation.clone().conjugate());
  local.copy(point).applyMatrix4(mesh.bindMatrix).applyQuaternion(rotation);
  local.add(new Vector3(translation.x, translation.y, translation.z).multiplyScalar(2));
  if(normal)normal.transformDirection(mesh.bindMatrix).applyQuaternion(rotation).transformDirection(mesh.bindMatrixInverse);
  return point.copy(local).applyMatrix4(mesh.bindMatrixInverse);
}

export function useDualQuaternion(mesh) {
  const palette = makePalette(mesh.skeleton);
  mesh.userData.volumePalette=palette;
  palette.update();
  mesh.applyBoneTransform=(index,point)=>deformPoint(mesh,palette,index,point);
  mesh.material = mesh.material.clone();
  mesh.material.onBeforeCompile = shader => {
    shader.uniforms.dqReal = { value: palette.real };
    shader.uniforms.dqDual = { value: palette.dual };
    shader.vertexShader = `
      uniform vec4 dqReal[${palette.real.length}];
      uniform vec4 dqDual[${palette.dual.length}];
      vec3 dqRotate(vec4 q, vec3 p) {
        return p + 2.0 * cross(q.xyz, cross(q.xyz, p) + q.w * p);
      }
    ` + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <skinbase_vertex>', `
      vec4 qr = vec4(0.0), qd = vec4(0.0);
      vec4 reference = dqReal[int(skinIndex.x)];
      for (int i = 0; i < 4; i++) {
        int bone = int(skinIndex[i]);
        float w = skinWeight[i] * (dot(reference, dqReal[bone]) < 0.0 ? -1.0 : 1.0);
        qr += w * dqReal[bone]; qd += w * dqDual[bone];
      }
      float magnitude = length(qr); qr /= magnitude; qd /= magnitude;
      vec3 dqTranslation = 2.0 * (qr.w * qd.xyz - qd.w * qr.xyz + cross(qr.xyz, qd.xyz));
    `).replace('#include <skinnormal_vertex>', `
      objectNormal = (bindMatrixInverse * vec4(dqRotate(qr, (bindMatrix * vec4(objectNormal, 0.0)).xyz), 0.0)).xyz;
      #ifdef USE_TANGENT
        objectTangent = (bindMatrixInverse * vec4(dqRotate(qr, (bindMatrix * vec4(objectTangent, 0.0)).xyz), 0.0)).xyz;
      #endif
    `).replace('#include <skinning_vertex>', `
      transformed = (bindMatrixInverse * vec4(dqRotate(qr, (bindMatrix * vec4(transformed, 1.0)).xyz) + dqTranslation, 1.0)).xyz;
    `);
  };
  mesh.material.customProgramCacheKey = () => `volume-skinning-${palette.real.length}`;
  mesh.onBeforeRender = () => palette.update();
}

export function prepareCharacterSkinning(model) {
  model.traverse(root=>{
    if(root.userData.skinning==='dualQuaternion')root.traverse(mesh=>{if(mesh.isSkinnedMesh)useDualQuaternion(mesh);});
  });
}

// CPU surface measurements use the same deformation as the rendering shader.
export function updateCharacterSkinning(model) {
  model.updateMatrixWorld(true);
  model.traverse(mesh=>mesh.userData.volumePalette?.update());
}
