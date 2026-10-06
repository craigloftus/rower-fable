import { Euler, Quaternion, Vector3 } from 'three';
import { G } from './stroke.js';
import { clamp } from './util.js';

// The rig bake and boat use exactly the same grip frame. The small height
// difference belongs to the oars themselves, so hands stay on the shafts.
export function oarPose(pose, side) {
  const pinY = pose.pinY ?? G.pinY;
  const inboard = pose.inboard ?? G.inboard;
  const crossover = pose.crossover ?? Math.max(0, 1 - Math.abs(pose.oar) / 0.5) ** 2;
  const lift = side > 0 ? 0.045 * crossover : -0.018 * crossover;
  const pitch = Math.asin(clamp((pinY - pose.blade) / 1.9, -0.6, 0.6)) + lift / (inboard - 0.10);
  const rotation = new Euler(pitch, side > 0 ? pose.oar : Math.PI - pose.oar, 0, 'YXZ');
  const quaternion = new Quaternion().setFromEuler(rotation);
  const pin = new Vector3(G.pinX, pinY, side * G.pinZ);
  const grip = new Vector3(0, 0, -(inboard - 0.10)).applyQuaternion(quaternion).add(pin);
  return { rotation, quaternion, pin, grip };
}
