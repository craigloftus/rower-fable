// Segment distance used for capsule clearance, including both opposite legs.
export function distance(a, b, c, d) {
  const u=b.clone().sub(a), w=a.clone().sub(c), vv=d.clone().sub(c);
  const A=u.dot(u), B=u.dot(vv), C=vv.dot(vv), D=u.dot(w), E=vv.dot(w);
  const clamp=x=>Math.max(0,Math.min(1,x));
  let s=clamp((B*E-C*D)/(A*C-B*B));
  let t=clamp((B*s+E)/C);
  s=clamp((B*t-D)/A); t=clamp((B*s+E)/C);
  return a.clone().addScaledVector(u,s).distanceTo(c.clone().addScaledVector(vv,t));
}
