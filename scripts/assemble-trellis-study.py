"""Assemble the detailed head and reconstructed body in a neutral pose.

The original image controls their relative scale. Output is an unrigged study.
"""
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]/'validation/reconstruction'
body=trimesh.load(ROOT/'trellis-clean/mesh.glb')
head=trimesh.load(ROOT/'trellis-local-head/mesh.glb')
from neck_join import clip,section_loops,bridge
assembled=trimesh.Scene()
body_edges=[];head_edges=[]
for name,mesh in body.geometry.items():
    mesh,edges=clip(mesh,.307,above=False)
    if len(mesh.faces):assembled.add_geometry(mesh,geom_name=name)
    body_edges.extend(edges)
for name,mesh in head.geometry.items():
    mesh=mesh.copy();mesh.apply_scale(.242);mesh.apply_translation([0,.367,-.019])
    mesh,edges=clip(mesh,.318,above=True)
    assembled.add_geometry(mesh,geom_name='Head');head_edges.extend(edges)
body_loops=section_loops(body_edges);head_loops=section_loops(head_edges)
neck=bridge(body_loops[0],head_loops[0])
assembled.add_geometry(neck,geom_name='Neck transition')
print('Neck sections:',[len(loop) for loop in body_loops],[len(loop) for loop in head_loops])
out=ROOT/'trellis-assembled'
out.mkdir(exist_ok=True)
assembled.export(out/'mesh.glb',include_normals=True)
print('Assembled neutral June:',sum(len(m.faces) for m in assembled.geometry.values()),'triangles')
