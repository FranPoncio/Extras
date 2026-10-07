"""Etapa 1: imágenes por escena con SDXL local (diffusers). Requiere GPU NVIDIA + PyTorch CUDA.

Si ya existe images/scene_XX.(png|jpg|webp) (por ejemplo, la bajaste de Kling), esa escena se saltea.
"""
from __future__ import annotations

from vp_common import dirs, find_asset

_PIPE = None


def _load(cfg):
    global _PIPE
    if _PIPE is None:
        import torch
        from diffusers import StableDiffusionXLPipeline

        pipe = StableDiffusionXLPipeline.from_pretrained(
            cfg["image_model"], torch_dtype=torch.float16, variant="fp16", use_safetensors=True
        )
        pipe.enable_model_cpu_offload()  # clave para entrar en 6 GB de VRAM
        pipe.enable_vae_tiling()
        pipe.enable_vae_slicing()
        _PIPE = pipe
    return _PIPE


def _gen(cfg, prompt, negative, w, h, seed):
    import torch

    pipe = _load(cfg)
    g = torch.Generator(device="cpu").manual_seed(seed)
    return pipe(
        prompt=prompt, negative_prompt=negative, width=w, height=h,
        num_inference_steps=cfg["image_steps"], guidance_scale=cfg["image_guidance"], generator=g,
    ).images[0]


def generate(cfg: dict, spec: dict) -> list[str]:
    d = dirs(cfg, spec)
    suffix = spec.get("style_suffix", cfg["style_suffix"])
    negative = spec.get("negative_prompt", cfg["negative_prompt"])
    made = []
    for sc in spec["scenes"]:
        stem = f"scene_{sc['n']:02d}"
        if find_asset(d["images"], stem, (".png", ".jpg", ".jpeg", ".webp")):
            continue
        if sc.get("image"):  # ruta explícita a una imagen propia
            continue
        prompt = f"{sc['image_prompt']}, {suffix}"
        seed = cfg["image_seed"] + sc["n"]
        try:
            img = _gen(cfg, prompt, negative, cfg["image_width"], cfg["image_height"], seed)
        except Exception as e:  # sin memoria: reintento más chico (576x1024 sigue siendo 9:16)
            if "out of memory" not in str(e).lower():
                raise
            import torch
            torch.cuda.empty_cache()
            img = _gen(cfg, prompt, negative, 576, 1024, seed)
        out = d["images"] / f"{stem}.png"
        img.save(out)
        made.append(str(out))
    return made
