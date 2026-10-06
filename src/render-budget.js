// Target up to 120 renders/s; preserve steady display timing even
// when RAF arrives a fraction early. Never replay frames after a long pause.
export function createFramePacer() {
  let next = 0, previousFps = 0;
  return (now, fps) => {
    if (fps !== previousFps) { next = now; previousFps = fps; }
    if (now < next - 1) return false;
    const interval = 1000 / fps;
    next += interval;
    if (next < now || next > now + interval + 1) next = now + interval;
    return true;
  };
}
