"""Fit the reconstructed hip surface to the real rowing seat over the stroke.

Solve small rest-surface displacements against the skinned seat constraints.
The same displacement is applied to material-seam duplicates. The supported
ischial patches remain pelvis-bound, so contact is stable throughout the cycle.
"""
import json
import numpy as np
from mathutils import Quaternion,Vector

def fit_seat(mesh,target,samples,C,seat,report_path):
    short_materials={i for i,m in enumerate(mesh.data.materials) if '_shorts' in m.name}
    shorts={i for p in mesh.data.polygons if p.material_index in short_materials for i in p.vertices}
    positions=np.array([v.co[:] for v in mesh.data.vertices],dtype=float)
    keys=[tuple(np.round(p,6)) for p in positions]
    chosen={keys[i] for i in shorts}
    grouped={key:[] for key in chosen}
    for i,key in enumerate(keys):
        if key in grouped:grouped[key].append(i)
    ids=np.array([items[0] for items in grouped.values()])
    points=positions[ids].copy();delta=np.zeros_like(points)
    names=list(target);bone_index={name:i for i,name in enumerate(names)}
    groups={g.index:g.name for g in mesh.vertex_groups}
    weights=np.zeros((len(ids),len(names)))
    for row,i in enumerate(ids):
        for g in mesh.data.vertices[i].groups:
            if groups[g.group] in bone_index:weights[row,bone_index[groups[g.group]]]=g.weight
    transforms_by_pose=[]
    for sample in samples[::5]:
        transforms=[]
        for name in names:
            b=sample['bones'][name];x,y,z,w=b['q']
            pose=Quaternion((w,x,y,z)).to_matrix().to_4x4();pose.translation=Vector(b['a'])
            transforms.append(np.array(C@pose@target[name].inverted()))
        transforms_by_pose.append((sample['pose']['seat'],np.array(transforms).reshape(len(names),16)))
    def blend_matrices():
        result=[]
        for seat_x,transforms in transforms_by_pose:
            blended=(weights@transforms).reshape(-1,4,4)
            result.append((seat_x,blended[:,:3,:3],blended[:,:3,3]))
        return result
    matrices=blend_matrices()
    # Sculpt the seated cloth surface as a connected patch before fitting it.
    # Independent point clamps can satisfy clearance while leaving spikes.
    index={i:row for row,items in enumerate(grouped.values()) for i in items}
    adjacent=[set() for _ in ids]
    boundary=np.zeros(len(ids),dtype=bool)
    for polygon in mesh.data.polygons:
        for i,j in zip(polygon.vertices,list(polygon.vertices[1:])+[polygon.vertices[0]]):
            if i in index and j in index:
                a,b=index[i],index[j]
                if a!=b:adjacent[a].add(b);adjacent[b].add(a)
            elif i in index:boundary[index[i]]=True
            elif j in index:boundary[index[j]]=True
    seat_x,A,b=matrices[0]
    posed=np.einsum('nij,nj->ni',A,points)+b
    support=np.clip((.46-posed[:,2])/.10,0,1)
    support*=np.clip((posed[:,0]-seat_x+.10)/.07,0,1)
    support[boundary]=0
    for _ in range(18):
        mean=np.array([posed[list(neighbors)].mean(axis=0) if neighbors else posed[i] for i,neighbors in enumerate(adjacent)])
        posed+=(mean-posed)*(.40*support)[:,None]
    # Paint a broad underside in the seated pose, where the actual support
    # surface is visible. This avoids pinning two isolated standing-pose points
    # and stretching their neighbours into spikes.
    def smooth(a,b,x):
        t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
    rear=smooth(seat_x-.12,seat_x-.065,posed[:,0])
    hold=rear*(1-smooth(.405,.50,posed[:,2]))
    posed[:,2]-=.081*hold
    posed[:,2]=np.maximum(posed[:,2],seat['top']+.0004)
    weights*=1-hold[:,None]
    weights[:,bone_index['pelvis']]+=hold
    for row,items in enumerate(grouped.values()):
        for i in items:
            for group in mesh.vertex_groups:group.remove([i])
            for bone,w in zip(names,weights[row]):
                if w>1e-6:mesh.vertex_groups[bone].add([i],float(w),'REPLACE')
    matrices=blend_matrices()
    _,A,b=matrices[0]
    delta=np.linalg.solve(A,(posed-b)[:,:,None])[:,:,0]-points
    for _ in range(6):
        maximum=0
        for seat_x,A,b in matrices:
            posed=np.einsum('nij,nj->ni',A,points+delta)+b
            inside=(np.abs(posed[:,0]-seat_x)<seat['length']/2+.001)&(np.abs(posed[:,1])<seat['width']/2+.001)
            needed=seat['top']+.00035-posed[:,2]
            hit=inside&(needed>0)
            if hit.any():
                normal=A[hit,2,:]
                delta[hit]+=normal*(needed[hit]/np.sum(normal*normal,axis=1))[:,None]
                maximum=max(maximum,float(needed[hit].max()))
        if maximum<1e-6:break
    affected=set()
    for row,items in enumerate(grouped.values()):
        if np.linalg.norm(delta[row])<1e-7:continue
        for i in items:
            mesh.data.vertices[i].co=positions[i]+delta[row];affected.add(i)
    mesh.data.update()
    normals=[n.vector.copy() for n in mesh.data.corner_normals]
    # Rebuild a shared normal field over the sculpted cloth. The render mesh
    # deliberately duplicates material/cut vertices; auto normals on those
    # individual triangles would make a smooth hip look crumpled.
    _,A,b=matrices[0]
    posed=np.einsum('nij,nj->ni',A,points+delta)+b
    field=np.zeros_like(posed)
    for polygon in mesh.data.polygons:
        rows=[index.get(i) for i in polygon.vertices]
        if any(i is None for i in rows):continue
        polygon_points=posed[rows]
        normal=np.cross(polygon_points,np.roll(polygon_points,-1,axis=0)).sum(axis=0)
        for row in rows:field[row]+=normal
    field/=np.maximum(np.linalg.norm(field,axis=1)[:,None],1e-12)
    rest_normals=np.linalg.solve(A,field[:,:,None])[:,:,0]
    rest_normals/=np.maximum(np.linalg.norm(rest_normals,axis=1)[:,None],1e-12)
    mesh.data.normals_split_custom_set([Vector(rest_normals[index[loop.vertex_index]]) if loop.vertex_index in affected and np.linalg.norm(field[index[loop.vertex_index]])>.5 else normals[loop.index] for loop in mesh.data.loops])
    report={'adjustedVertices':len(affected),'maximumRestCorrection':float(np.linalg.norm(delta,axis=1).max()),'constraintPoses':len(matrices)}
    report_path.write_text(json.dumps(report,indent=2));print('Seat fit:',report,flush=True)
