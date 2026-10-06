"""Evaluate official TripoSR on Apple Silicon without CUDA extensions.

Run with the isolated TripoSR environment; outputs remain review studies.
The scikit-image adapter returns torchmcubes' XYZ convention.
"""
import argparse
from pathlib import Path
import sys
import time
import types

import numpy as np
from PIL import Image
from skimage.measure import marching_cubes
import torch

parser = argparse.ArgumentParser()
parser.add_argument('image', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--resolution', type=int, default=256)
parser.add_argument('--crop', nargs=4, type=int, help='Input crop for a separate head reconstruction')
parser.add_argument('--black-background', action='store_true', help='TRELLIS demo preprocessing composites its mask onto black')
parser.add_argument('--remove-background', action='store_true')
args = parser.parse_args()
root = Path.home()/'.local/share/rower-tools/TripoSR'
sys.path.insert(0, str(root))

def cpu_marching_cubes(level, threshold):
    vertices, faces, _, _ = marching_cubes(level.cpu().numpy(), threshold)
    return torch.from_numpy(vertices[:, [2, 1, 0]].copy()), torch.from_numpy(faces[:, ::-1].copy())

mc = types.ModuleType('torchmcubes')
mc.marching_cubes = cpu_marching_cubes
sys.modules['torchmcubes'] = mc
from tsr.system import TSR
from tsr.utils import resize_foreground

args.output.mkdir(parents=True, exist_ok=True)
start = time.time()
print('Loading TripoSR weights', flush=True)
model = TSR.from_pretrained('stabilityai/TripoSR', config_name='config.yaml', weight_name='model.ckpt')
model.renderer.set_chunk_size(16384)
model.eval().to('mps')
image = Image.open(args.image).convert('RGBA')
if args.black_background:
    rgba = np.array(image)
    rgba[:, :, 3] = (rgba[:, :, :3].max(axis=2)>3)*255
    image = Image.fromarray(rgba)
if args.crop:
    image = image.crop(args.crop)
if args.remove_background:
    import rembg
    image = rembg.remove(image, session=rembg.new_session('u2net'))
image = resize_foreground(image, .85)
pixels = np.asarray(image).astype(np.float32)/255
image = Image.fromarray((255*(pixels[:, :, :3]*pixels[:, :, 3:4]+.5*(1-pixels[:, :, 3:4]))).astype(np.uint8))
image.save(args.output/'input.png')
print(f'Inferring on Apple GPU after {time.time()-start:.1f}s', flush=True)
with torch.inference_mode():
    codes = model([image], device='mps')
    torch.save(codes.cpu(), args.output/'scene-code.pt')
    print(f'Extracting mesh after {time.time()-start:.1f}s', flush=True)
    mesh = model.extract_mesh(codes, True, resolution=args.resolution)[0]
def nonmetal_material(tree):
    tree['materials'] = [{'name': 'Reconstruction colour', 'pbrMetallicRoughness': {
        'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0, 'roughnessFactor': .85}}]
    for item in tree['meshes']:
        for primitive in item['primitives']:
            primitive['material'] = 0

mesh.export(args.output/'mesh.glb', include_normals=True, tree_postprocessor=nonmetal_material)
print(f'Exported {len(mesh.vertices)} vertices, {len(mesh.faces)} faces in {time.time()-start:.1f}s', flush=True)
