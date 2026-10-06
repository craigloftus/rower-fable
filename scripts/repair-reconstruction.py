"""Repair surface winding across UV seams while retaining textures.

Run with the reconstruction environment's trimesh installation. Source and
output paths are explicit so the raw model remains available for comparison.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh

parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args()
mesh=trimesh.load(args.source,force='mesh')
# The connectivity solver must see physical edges, including texture seams.
_,ids,inverse=np.unique(np.round(mesh.vertices,7),axis=0,return_index=True,return_inverse=True)
faces=inverse[mesh.faces]
welded=trimesh.Trimesh(mesh.vertices[ids],faces,process=False)
before=welded.face_normals.copy()
trimesh.repair.fix_normals(welded,multibody=True)
flipped=np.einsum('ij,ij->i',before,welded.face_normals)<0
repaired_faces=mesh.faces.copy()
repaired_faces[flipped]=repaired_faces[flipped,::-1]
fixed=trimesh.Trimesh(mesh.vertices,repaired_faces,vertex_normals=welded.vertex_normals[inverse],visual=mesh.visual,process=False)
fixed.export(args.output,include_normals=True)
report={'source':str(args.source),'output':str(args.output),'flippedTriangles':int(flipped.sum()),'triangles':len(mesh.faces),'consistentWinding':bool(welded.is_winding_consistent),'watertight':bool(welded.is_watertight)}
args.output.with_suffix('.repair.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
