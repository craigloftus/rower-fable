"""Group neighbouring cells into readable sculpt planes without moving the shape."""
from collections import deque
import numpy as np
from scipy.spatial import cKDTree
from trimesh.triangles import closest_point

class SculptPlanes:
    def __init__(self,mesh):
        self.mesh=mesh.copy()
        p=mesh.triangles_center;area=mesh.area_faces
        n=mesh.vertex_normals[mesh.faces].mean(axis=1)
        n/=np.linalg.norm(n,axis=1)[:,None]
        adjacent=[[] for _ in area]
        for a,b in mesh.face_adjacency:
            adjacent[a].append(b);adjacent[b].append(a)
        assigned=np.zeros(len(area),dtype=bool)
        self.normals=np.zeros_like(n)
        groups=0
        for seed in np.argsort(-area):
            if assigned[seed]:continue
            head=p[seed,1]>.33
            hair=head and (p[seed,1]>.415 or p[seed,2]<.005)
            radius=.014 if hair else .009 if head else .032
            limit=.00035 if hair else .00016 if head else .0013
            cosine=np.cos(np.deg2rad(14 if hair else 12))
            members=[];queue=deque([seed]);visited=set();total=0
            while queue:
                i=queue.popleft()
                if i in visited:continue
                visited.add(i)
                if assigned[i] or (i!=seed and total+area[i]>limit):continue
                if np.dot(n[i],n[seed])<cosine or np.linalg.norm(p[i]-p[seed])>radius:continue
                assigned[i]=True;members.append(i);total+=area[i]
                queue.extend(adjacent[i])
            normal=np.sum(n[members]*area[members,None],axis=0)
            normal/=np.linalg.norm(normal)
            self.normals[members]=normal;groups+=1
        self.tree=cKDTree(p)
        self.groups=groups

    def at(self,points):
        _,ids=self.tree.query(points,k=12)
        triangles=self.mesh.triangles[ids].reshape(-1,3,3)
        repeated=np.repeat(points,12,axis=0)
        closest=closest_point(triangles,repeated)
        distance=np.sum((closest-repeated)**2,axis=1).reshape(-1,12)
        best=ids[np.arange(len(points)),distance.argmin(axis=1)]
        return self.normals[best]
