import { Vector3 } from 'three';

// Measure the rendered, skinned shorts against the actual seat dimensions.
export function seatSurface(scene) {
  const surfaces=[];
  scene.traverse(mesh=>{
    if(mesh.isSkinnedMesh && mesh.material.name.includes('_shorts')) {
      surfaces.push({mesh,indices:mesh.geometry.index.array,
        points:Array.from({length:mesh.geometry.attributes.position.count},()=>new Vector3())});
    }
  });
  return (seatX,seat)=>{
    const lowest=[Infinity,Infinity],area=[0,0];
    let minimumClearance=Infinity,centre=Infinity;
    const inside=p=>Math.abs(p.x-seatX)<seat.length/2-.002 && Math.abs(p.z)<seat.width/2-.002;
    for(const {mesh,indices,points} of surfaces) {
      for(let i=0;i<points.length;i++) {
        const p=mesh.getVertexPosition(i,points[i]).applyMatrix4(mesh.matrixWorld);
        if(!inside(p))continue;
        minimumClearance=Math.min(minimumClearance,p.y-seat.top);
        if(Math.abs(p.z)<.02)centre=Math.min(centre,p.y);
        else lowest[p.z<0?0:1]=Math.min(lowest[p.z<0?0:1],p.y);
      }
      for(let i=0;i<indices.length;i+=3) {
        const a=points[indices[i]],b=points[indices[i+1]],c=points[indices[i+2]];
        if(![a,b,c].every(p=>inside(p)&&Math.abs(p.y-seat.top)<.001))continue;
        const side=a.z<0?0:1;
        if([b,c].some(p=>(p.z<0?0:1)!==side))continue;
        area[side]+=Math.abs((b.x-a.x)*(c.z-a.z)-(b.z-a.z)*(c.x-a.x))/2;
      }
    }
    return {gap:Math.max(...lowest)-seat.top,minimumClearance,
      contactArea:Math.min(...area),centreDrop:Math.max(0,Math.min(...lowest)-centre)};
  };
}
