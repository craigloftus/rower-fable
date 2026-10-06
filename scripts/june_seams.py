"""Make every material-cut edge conform before the mesh is skinned."""
import numpy as np
from scipy.spatial import cKDTree

def conform(parts):
    names=['Skin','Copper hair','Terracotta singlet','Singlet binding','Cream stripe',
           'Charcoal shorts','Ivory shoes','Shoe soles','Shoe straps']
    points=np.unique(np.round(np.concatenate([p for name in names for p in parts[name]]),8),axis=0)
    tree=cKDTree(points)
    cache={};split_count=0
    def between(a,b):
        key=(tuple(np.round(a,8)),tuple(np.round(b,8)))
        if key in cache:return cache[key]
        direction=b-a;length2=np.dot(direction,direction)
        if length2<1e-16:return []
        candidates=points[tree.query_ball_point((a+b)/2,np.sqrt(length2)/2+1e-7)]
        t=(candidates-a)@direction/length2
        distance=np.linalg.norm(candidates-(a+t[:,None]*direction),axis=1)
        inside=(t>1e-6)&(t<1-1e-6)&(distance<1e-7)
        result=candidates[inside][np.argsort(t[inside])]
        cache[key]=result;cache[(key[1],key[0])]=result[::-1]
        return result
    for name in names:
        result=[]
        for polygon in parts[name]:
            outline=[];changed=False
            for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
                outline.append(a);extra=between(a,b)
                if len(extra):outline.extend(extra);changed=True
            if changed:
                centre=np.mean(polygon,axis=0)
                for a,b in zip(outline,np.roll(outline,-1,axis=0)):
                    if np.linalg.norm(np.cross(a-centre,b-centre))>1e-13:
                        result.append(np.array([centre,a,b]))
                split_count+=1
            else:result.append(polygon)
        parts[name]=result
    print('Conformed material-edge polygons:',split_count,flush=True)
    return parts
