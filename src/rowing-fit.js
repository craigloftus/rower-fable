import { lerp, smooth, easeSin, clamp } from './util.js';
import { G } from './stroke.js';

// Zero velocity and acceleration at the ends of a movement.
const soft = (a, b, p) => {
  const t = clamp((p-a)/(b-a), 0, 1);
  return t*t*t*(10+t*(-15+6*t));
};
// Quintic interpolation with endpoint speeds and zero endpoint acceleration.
function travel(t, from, to, startSpeed, endSpeed) {
  const d=to-from;
  return from+startSpeed*t+t*t*t*((10*d-6*startSpeed-4*endSpeed)
    +t*((-15*d+8*startSpeed+7*endSpeed)+t*(6*d-3*startSpeed-3*endSpeed)));
}
function recoverySweep(p) {
  // Hands away flows into the slide at the same speed and acceleration.
  return p<.30 ? travel(p/.30,0,.35,0,1.8*.30)
    : travel((p-.30)/.70,.35,1,1.8*.70,0);
}

export const JUNE_ROWING_FIT = {
  catchAngle: 1.00, seatFinish: G.seatFinish, pinY: .45, inboard: .80, gripRadius: .020,
};

// Every character shares June's approved body and baked stroke.
export function fitRowingPose(pose, character) {
  if (character === null) return pose; // The initial asset is still loading.
  return fitNativeRowingPose(pose, JUNE_ROWING_FIT);
}

export function fitNativeRowingPose(pose, fit) {
  const { catchAngle, seatFinish, pinY, inboard, gripRadius } = fit;
  const finishAngle = -.10;
  const p = pose.p;
  const oar = pose.mode === 'drive'
    ? lerp(catchAngle, finishAngle, easeSin(p))
    : lerp(finishAngle, catchAngle, recoverySweep(p));
  const seat = pose.mode === 'drive'
    ? lerp(.025, seatFinish, smooth(0, .86, p))
    : lerp(seatFinish, .025, soft(.10, 1, p));
  const lean = pose.mode === 'drive' ? pose.lean*.75 : lerp(-.27, .24, soft(0, .52, p));
  const blade = pose.mode === 'drive' ? pose.blade
    : lerp(lerp(G.bladeDrive, .045, soft(0, .42, p)), -.02, soft(.90, 1, p));
  const feather = pose.mode === 'drive' ? pose.feather
    : soft(.02,.30,p)*(1-soft(.78,.99,p));
  // Round the change of direction in hand-over-hand height at the crossover.
  // abs(oar) has a cusp here, which otherwise snaps the wrists vertically.
  const angle=Math.abs(oar),t=clamp(angle/.10,0,1);
  const roundedAngle=pose.mode==='rec' && angle<.10
    ? .10*t*t*t*(6+t*(-8+3*t)) : angle;
  const crossover=Math.max(0,1-roundedAngle/.5)**2;
  return { ...pose, seat, oar, lean, blade, feather, crossover, pinY, inboard, gripRadius };
}
