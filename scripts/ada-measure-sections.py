"""Report separated source cross-sections for Ada's anatomical measurements."""
from pathlib import Path
import sys,json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'validation/characters/ada/reconstructed.glb')
m=trimesh.load(path,force='mesh');p=m.vertices
rows=[]
for y in np.arange(-.48,.501,.02):
 q=p[abs(p[:,1]-y)<.004];q=q[np.argsort(q[:,0])]
 if len(q)==0:continue
 groups=np.split(q,np.flatnonzero(np.diff(q[:,0])>.012)+1)
 row={'y':round(float(y),3),'sections':[]}
 for g in groups:
  if len(g)<8:continue
  row['sections'].append({'bounds':np.round([g.min(0),g.max(0)],4).tolist(),'centre':np.round((g.min(0)+g.max(0))/2,4).tolist(),'vertices':len(g)})
 rows.append(row)
print(json.dumps({'source':str(path),'bounds':m.bounds.tolist(),'sections':rows},indent=2))
