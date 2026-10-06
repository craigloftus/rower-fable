"""Fit the seated garment to June's actual waist and thighs with a smooth cage warp."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Matrix,Vector

def tailor(shorts,bindings,matrices,C,seat_top):
    bm=bmesh.new();bm.from_mesh(shorts.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bm.to_mesh(shorts.data);bm.free()
    mesh=shorts.data
    bones=list(matrices);bone_id={b:i for i,b in enumerate(bones)}
    names={g.index:g.name for g in shorts.vertex_groups}
    weights=np.zeros((len(mesh.vertices),len(bones)))
    for vertex in mesh.vertices:
        for group in vertex.groups:
            if group.weight>1e-6:weights[vertex.index,bone_id[names[group.group]]]=group.weight
    def transform(ws):
        return sum((matrices[b]*float(w) for b,w in zip(bones,ws) if w>1e-8),Matrix(np.zeros((4,4))))
    world=np.array([transform(ws)@v.co for v,ws in zip(mesh.vertices,weights)])
    lookup={tuple(round(x,6) for x in v.co):v.index for v in mesh.vertices}
    # Keep all of the existing sitting surface and its surrounding support zone.
    fixed=np.array([(C.inverted()@Vector(p)).y<seat_top+.032 for p in world])
    delta=np.zeros((len(world),3+len(bones)))
    boundaries=[]
    for old_loop,new_loop,frame,offset in bindings:
        inverse=frame.inverted()
        old_ids=[lookup[tuple(round(x,6) for x in p)] for p,_ in old_loop]
        old_local=np.array([inverse@Vector(world[i]) for i in old_ids])
        new_weights=np.array([[ws.get(b,0) for b in bones] for _,ws in new_loop])
        new_local=np.array([inverse@(transform(ws)@p) for (p,_),ws in zip(new_loop,new_weights)])
        old_center=old_local.mean(axis=0);new_center=new_local.mean(axis=0)
        angles=np.arctan2(new_local[:,2]-new_center[2],new_local[:,0]-new_center[0])%math.tau
        order=np.argsort(angles);angles=angles[order]
        values=np.column_stack([new_local[order],new_weights[order]])
        angles=np.r_[angles[-1]-math.tau,angles,angles[0]+math.tau]
        values=np.vstack([values[-1],values,values[0]])
        for i,p in zip(old_ids,old_local):
            a=math.atan2(p[2]-old_center[2],p[0]-old_center[0])%math.tau
            target=np.array([np.interp(a,angles,values[:,j]) for j in range(values.shape[1])])
            target[1]-=offset
            delta[i,:3]=np.array(frame@Vector(target[:3]))-world[i]
            delta[i,3:]=target[3:]-weights[i]
            fixed[i]=True
        boundaries.extend(old_ids)
    # Diffuse boundary displacements, rather than smoothing away the garment's
    # shape. Positive graph weights keep the field stable near narrow hip faces.
    edges=np.array([e.vertices[:] for e in mesh.edges]);edges=np.vstack([edges,edges[:,::-1]])
    degree=np.bincount(edges[:,0],minlength=len(world))[:,None]
    for iteration in range(2500):
        total=np.zeros_like(delta);np.add.at(total,edges[:,0],delta[edges[:,1]])
        proposed=total/degree;proposed[fixed]=delta[fixed]
        error=np.max(np.abs(proposed-delta));delta=proposed
        if error<1e-9:break
    assert error<1e-7,f'Garment fitting did not converge: {error}'
    fitted=world+delta[:,:3]
    weights=np.maximum(0,weights+delta[:,3:])
    for ws in weights:
        ws[np.argsort(ws)[:-4]]=0;ws/=ws.sum()
    for group in list(shorts.vertex_groups):shorts.vertex_groups.remove(group)
    for bone in bones:shorts.vertex_groups.new(name=bone)
    normal_maps=[]
    for vertex,point,ws in zip(mesh.vertices,fitted,weights):
        matrix=transform(ws)
        vertex.co=matrix.inverted()@Vector(point)
        normal_maps.append(matrix.to_3x3().inverted())
        for bone,w in zip(bones,ws):
            if w>1e-8:shorts.vertex_groups[bone].add([vertex.index],float(w),'REPLACE')
    mesh.update()
    vertex_normals=[Vector() for _ in mesh.vertices];face_normals=[]
    for face in mesh.polygons:
        a,b,c=[Vector(fitted[i]) for i in face.vertices[:3]]
        normal=(b-a).cross(c-a);face_normals.append(normal.normalized())
        for i in face.vertices:vertex_normals[i]+=normal
    normals=[Vector() for _ in mesh.loops]
    for face,normal in zip(mesh.polygons,face_normals):
        for loop_id in face.loop_indices:
            i=mesh.loops[loop_id].vertex_index
            posed=(normal*.65+vertex_normals[i].normalized()*.35).normalized()
            normals[loop_id]=(normal_maps[i]@posed).normalized()
    mesh.normals_split_custom_set(normals)
    print('TAILORED_GARMENT',{'vertices':len(world),'boundaryVertices':len(boundaries),'iterations':iteration+1,'residual':float(error),'maximumDisplacement':float(np.linalg.norm(delta[:,:3],axis=1).max())},flush=True)
