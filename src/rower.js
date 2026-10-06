import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DEFAULT_CHARACTER } from './characters.js';
import { prepareCharacterSkinning } from './volume-skinning.js';

// The Blender cycle is two seconds: drive p, recovery 1+p. No second clock.
export class Rower {
  constructor(parent) {
    this.group = new THREE.Group();
    parent.add(this.group);
    this.loader = new GLTFLoader();
    this.request = 0;
    this.ready = false;
    this.character = null;
  }

  async select(id = DEFAULT_CHARACTER) {
    const request = ++this.request;
    const gltf = await this.loader.loadAsync(`${import.meta.env.BASE_URL}characters/${id}.glb`);
    if (request !== this.request) {
      this.disposeModel(gltf.scene);
      return false;
    }
    if (this.model) {
      this.mixer.stopAllAction();
      this.mixer.uncacheRoot(this.model);
      this.group.remove(this.model);
      this.disposeModel(this.model);
    }
    this.model = gltf.scene;
    prepareCharacterSkinning(this.model);
    this.model.traverse((o) => { if (o.isMesh) o.frustumCulled = false; });
    this.group.add(this.model);
    this.mixer = new THREE.AnimationMixer(this.model);
    this.action = this.mixer.clipAction(gltf.animations.find((clip) => clip.name === 'RowingCycle'));
    this.action.setLoop(THREE.LoopOnce, 1);
    this.action.clampWhenFinished = true;
    this.action.play();
    this.character = id;
    this.ready = true;
    if (this.pose) this.update(this.pose);
    return true;
  }

  disposeModel(model) {
    model.traverse((o) => {
      if (!o.isMesh) return;
      o.geometry.dispose();
      for (const material of Array.isArray(o.material) ? o.material : [o.material]) material.dispose();
      if (o.isSkinnedMesh) o.skeleton.dispose();
    });
  }

  update(pose) {
    this.pose = pose;
    if (!this.ready) return;
    this.action.paused = false;
    this.mixer.setTime((pose.mode === 'drive' ? 0 : 1) + pose.p);
  }
}
