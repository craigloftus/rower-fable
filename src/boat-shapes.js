import * as THREE from 'three';

// Each patch is [material index, ...corners]. Keep broad planes; colour changes
// share the same edges instead of covering one surface with another.
export function facets(patches, materials) {
  const geometry = new THREE.BufferGeometry(), positions = [];
  for (let material = 0; material < materials.length; material++) {
    const start = positions.length / 3;
    for (const [index, ...corners] of patches) {
      if (index !== material) continue;
      for (let i = 1; i < corners.length - 1; i++) {
        positions.push(...corners[0], ...corners[i], ...corners[i + 1]);
      }
    }
    geometry.addGroup(start, positions.length / 3 - start, material);
  }
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, materials);
}

// Bevels stay inside the given dimensions, including the two support planes.
export function panel(width, height, depth, corner = .02, bevel = .003) {
  const x = width / 2 - bevel, y = height / 2 - bevel;
  const points = [[-x + corner,-y],[x - corner,-y],[x,-y + corner],
    [x,y - corner],[x - corner,y],[-x + corner,y],[-x,y - corner],[-x,-y + corner]];
  const shape = new THREE.Shape(points.map(p => new THREE.Vector2(...p)));
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: depth - 2 * bevel, steps: 1, bevelEnabled: true,
    bevelThickness: bevel, bevelSize: bevel, bevelSegments: 1,
  });
  geometry.translate(0, 0, -depth / 2 + bevel);
  return geometry;
}

export function shell(materials) {
  // x, half beam, sheer height, cockpit half-width (zero outside cockpit).
  const stations = [
    [-4.15,.006,.19,0],[-3.60,.052,.215,0],[-2.65,.118,.228,0],[-1.80,.184,.23,0],
    [-1.15,.225,.225,.14],[-1.0,.233,.225,.185],[-.60,.244,.225,.193],
    [0,.248,.225,.195],[.60,.243,.225,.193],[1.05,.229,.225,.18],[1.20,.219,.225,.13],
    [1.85,.177,.233,0],[2.70,.11,.228,0],[3.60,.045,.21,0],[4.15,.006,.18,0],
  ];
  const patches = [], rings = stations.map(([x,w,y]) => {
    const keel = -.055 + .16 * (Math.abs(x) / 4.15) ** 2;
    const depth = y - keel;
    return [[x,y,-w],[x,y-depth*.25,-w*.94],[x,keel+depth*.24,-w*.60],
      [x,keel,0],[x,keel+depth*.24,w*.60],[x,y-depth*.25,w*.94],[x,y,w]];
  });
  for (let i = 0; i < stations.length - 1; i++) {
    const a = rings[i], b = rings[i+1];
    for (let k = 0; k < a.length - 1; k++) patches.push([0,a[k],b[k],b[k+1],a[k+1]]);
    const [x,w,y,iw] = stations[i], [nx,nw,ny,niw] = stations[i+1];
    const cockpit = iw > 0 && niw > 0;
    if (!cockpit) {
      // A shallow ridge catches real light along the long cream deck.
      for (const s of [-1,1]) {
        const points = [[x,y,s*w],[x,y+.018,0],[nx,ny+.018,0],[nx,ny,s*nw]];
        patches.push([1,...(s < 0 ? points : points.reverse())]);
      }
      continue;
    }
    for (const s of [-1,1]) {
      const strip = (a,b,c,d,material) => patches.push([material,...(s < 0 ? [a,b,c,d] : [d,c,b,a])]);
      strip([x,y,s*w],[x,y,s*(iw+.016)],[nx,ny,s*(niw+.016)],[nx,ny,s*nw],1);
      strip([x,y,s*(iw+.016)],[x,.246,s*(iw+.014)],[nx,.246,s*(niw+.014)],[nx,ny,s*(niw+.016)],2);
      strip([x,.246,s*(iw+.014)],[x,.246,s*iw],[nx,.246,s*niw],[nx,.246,s*(niw+.014)],2);
      strip([x,.246,s*iw],[x,.105,s*iw*.9],[nx,.105,s*niw*.9],[nx,.246,s*niw],3);
    }
    patches.push([3,[x,.105,-iw*.9],[x,.105,iw*.9],[nx,.105,niw*.9],[nx,.105,-niw*.9]]);
  }
  // Cockpit bulkheads and a narrow wooden lip close the ends of the opening.
  for (const index of [4,10]) {
    const [x,,y,w] = stations[index], direction = index === 4 ? 1 : -1;
    const wall = [[x,.105,-w*.9],[x,.105,w*.9],[x,.246,w],[x,.246,-w]];
    patches.push([3,...(direction > 0 ? wall.reverse() : wall)]);
    const outerX=x-direction*.02, edge=w+.014;
    const lip = [[x,.246,-edge],[x,.246,edge],[outerX,.246,edge],[outerX,.246,-edge]];
    patches.push([2,...(direction > 0 ? lip.reverse() : lip)]);
    // The outside face beds into the deck, rather than floating above its camber.
    const apron=[[outerX,y-.004,-edge],[outerX,y-.004,edge],[outerX,.246,edge],[outerX,.246,-edge]];
    patches.push([2,...(direction > 0 ? apron : apron.reverse())]);
    for(const side of [-1,1]){
      const end=[[x,y,side*edge],[outerX,y-.004,side*edge],[outerX,.246,side*edge],[x,.246,side*edge]];
      patches.push([2,...(side*direction < 0 ? end : end.reverse())]);
    }
  }
  for(const i of [0,stations.length-1]){
    const [x,,y]=stations[i], cap=[...rings[i],[x,y+.018,0]];
    patches.push([0,...(i===0?cap:cap.reverse())]);
  }
  return facets(patches, materials);
}

export function spoonBlade(side, materials) {
  // A thin, closed spoon with a continuous cream tip. The middle ridge gives
  // the face its cup; the silhouette uses a few purposeful changes in width.
  const sections = [[0,-.024,.024],[.065,-.057,.072],[.16,-.13,.106],
    [.36,-.15,.11],[.39,-.146,.108],[.44,-.12,.088]];
  const sheets = [-1,1].map(face => sections.map(([z,bottom,top]) => {
    const cup = Math.sin(z/.50*Math.PI)*.023*side;
    return [bottom,(bottom+top)/2,top].map((y,i) =>
      [cup*(i===1?1:.18)+face*.0035,y,z]);
  }));
  const patches = [];
  for (let j=0;j<sections.length-1;j++) {
    const material = j>=3 ? 1 : 0;
    for (let face=0;face<2;face++) for(let k=0;k<2;k++) {
      const a=sheets[face][j],b=sheets[face][j+1];
      const points=[a[k],a[k+1],b[k+1],b[k]];
      patches.push([material,...(face===1?points:points.reverse())]);
    }
    for(const k of [0,2]) {
      const points=[sheets[0][j][k],sheets[1][j][k],sheets[1][j+1][k],sheets[0][j+1][k]];
      patches.push([material,...(k===0?points:points.reverse())]);
    }
  }
  for(const j of [0,sections.length-1]) for(let k=0;k<2;k++) {
    const points=[sheets[0][j][k],sheets[0][j][k+1],sheets[1][j][k+1],sheets[1][j][k]];
    patches.push([j===0?0:1,...(j===0?points:points.reverse())]);
  }
  return facets(patches,materials);
}
