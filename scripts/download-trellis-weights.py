"""Fetch only the pinned weights used by the installed TRELLIS.2 MLX pipeline.

Uses the local Hugging Face credential store. Weights stay in the standard
user cache, outside the game repository (approximately 13.6 GB).
"""
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import snapshot_download

models = [
    ('facebook/dinov3-vitl16-pretrain-lvd1689m', 'ea8dc2863c51be0a264bab82070e3e8836b02d51',
     ['model.safetensors', '*.json', '*LICENSE*', 'README.md']),
    ('microsoft/TRELLIS-image-large', '25e0d31ffbebe4b5a97464dd851910efc3002d96',
     ['ckpts/ss_dec_conv3d_16l8_fp16.*', 'LICENSE', 'README.md']),
    ('microsoft/TRELLIS.2-4B', 'af44b45f2e35a493886929c6d786e563ec68364d', [
        'ckpts/ss_flow_img_dit_1_3B_64_bf16.*',
        'ckpts/slat_flow_img2shape_dit_1_3B_512_bf16.*',
        'ckpts/slat_flow_img2shape_dit_1_3B_1024_bf16.*',
        'ckpts/shape_dec_next_dc_f16c32_fp16.*',
        'ckpts/slat_flow_imgshape2tex_dit_1_3B_512_bf16.*',
        'ckpts/tex_dec_next_dc_f16c32_fp16.*', 'pipeline.json', 'LICENSE', 'README.md']),
]

def download(spec):
    repo, revision, files = spec
    print(f'Downloading {repo}', flush=True)
    path = snapshot_download(repo, revision=revision, allow_patterns=files, max_workers=2)
    print(f'Ready: {repo} at {path}', flush=True)

with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(download, models))
