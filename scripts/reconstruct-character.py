"""Generate a reconstruction through Microsoft's public TRELLIS.2 demo.
Usage: uv run --with gradio_client python scripts/reconstruct-character.py
The original illustration is the input; this does not edit the runtime assets.
"""
from pathlib import Path
import argparse
import json
from gradio_client import Client, handle_file
from huggingface_hub import get_token
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--image',type=Path,default=ROOT/'art/characters/june-concept.png')
parser.add_argument('--output',type=Path,default=ROOT/'validation/reconstruction/trellis')
parser.add_argument('--seed',type=int,default=42)
args=parser.parse_args()
OUT=args.output.resolve()
OUT.mkdir(parents=True,exist_ok=True)
token=get_token()
if not token:
    raise SystemExit('Sign in locally with hf auth login, then rerun. Do not put a token in this file or in chat.')
client=Client('microsoft/TRELLIS.2',download_files=str(OUT),token=token)
client.predict(api_name='/start_session')
print(f'Preparing {args.image.name}',flush=True)
prepared=client.predict(handle_file(str(args.image.resolve())),api_name='/preprocess_image')
print('Starting image-to-3D reconstruction',flush=True)
preview=client.predict(image=handle_file(prepared),seed=args.seed,resolution='1024',api_name='/image_to_3d')
(OUT/'preview.html').write_text(preview)
print('Extracting textured GLB',flush=True)
result=client.predict(decimation_target=100000,texture_size=2048,api_name='/extract_glb')
(OUT/'result.json').write_text(json.dumps({'input':str(args.image),'space':'microsoft/TRELLIS.2','seed':args.seed,'resolution':1024,'output':result},indent=2))
import shutil
shutil.copy2(result[0],OUT/'mesh.glb')
print(result,flush=True)
