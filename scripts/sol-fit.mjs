import {fitNativeRowingPose} from '../src/rowing-fit.js';

// Measured Sol anatomy; the boat must use these same five parameters.
export const SOL_ROWING_FIT = {
  catchAngle: .90, seatFinish: .30, pinY: .48, inboard: .75, gripRadius: .020,
};
export const solPose = pose => fitNativeRowingPose(pose, SOL_ROWING_FIT);
