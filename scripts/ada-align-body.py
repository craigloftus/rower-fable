"""Put Ada's observed shoulder axis across X with one rigid source transform."""
from pathlib import Path
import json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/ada'
# The two isolated forearm sections at y=.12 and .05 give a 6.3 degree yaw.
angle=np.deg2rad(6.3)
transform=trimesh.transformations.rotation_matrix(angle,[0,1,0])
transform[:3,3]=-transform[:3,:3]@np.array([0,0,-.028])
for source,target in [('solid.ply','aligned-solid.ply'),('reconstructed.glb','aligned-source.glb')]:
 mesh=trimesh.load(OUT/source,force='mesh');mesh.apply_transform(transform);mesh.export(OUT/target)
(OUT/'source-alignment.json').write_text(json.dumps({'rotationDegreesY':6.3,'sourceCentre':[0,0,-.028],'matrix':transform.tolist(),'method':'Rigid transform from measured paired forearm cross-sections; no nonuniform scale'},indent=2)+'\n')
