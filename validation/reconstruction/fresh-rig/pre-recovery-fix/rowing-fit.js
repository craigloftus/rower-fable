import { lerp, smooth, easeSin } from '../../../../src/util.js';
import { G } from '../../../../src/stroke.js';

// The boat and baked character must use the same handle path. June's sculpt
// has its own proportions, so its finish stops before the hands reach her chest.
export function fitRowingPose(pose, character) {
  if (character !== 'june') return pose;
  const catchAngle = 1.00, finishAngle = -.10, restAngle = .35;
  const p = pose.p;
  const oar = pose.mode === 'drive'
    ? lerp(catchAngle, finishAngle, easeSin(p))
    : lerp(lerp(finishAngle, restAngle, smooth(.02, .22, p)), catchAngle,
      easeSin(smooth(.28, .93, p)));
  const seat = pose.mode === 'drive'
    ? lerp(.025, G.seatFinish, smooth(0, .86, p))
    : lerp(G.seatFinish, .025, smooth(.32, .86, p));
  const lean = pose.mode === 'drive' ? pose.lean*.75 : lerp(-.27, .24, smooth(0, .30, p));
  const blade = pose.mode === 'drive' ? pose.blade
    : lerp(lerp(G.bladeDrive, .045, smooth(0, .18, p)), -.02, smooth(.94, 1, p));
  return { ...pose, seat, oar, lean, blade, pinY: .45, inboard: .80, gripRadius: .020 };
}
