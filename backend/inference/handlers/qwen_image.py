"""
QwenImageHandler — wraps the 54GB DiffusionPipeline model.

Key facts:
- Model: /data/models/t2i/qwen-image-2512
- Load with DiffusionPipeline.from_pretrained, NOT AutoModelForCausalLM
- device_map="balanced" REQUIRED: model is 54GB, GPU is 44GB VRAM
- torch_dtype=torch.bfloat16
- local_files_only=True
- Inference parameter is "true_cfg_scale" not "cfg_scale"
- Returns result.images (list of PIL.Image)
- Wrap inference in torch.no_grad()
"""
import random
import gc
from typing import Any

import structlog

from core.config import settings
from .base import BaseHandler

log = structlog.get_logger()

MODEL_REGISTRY = {
    "qwen-image-2512": f"{settings.models_dir}/t2i/qwen-image-2512",
    "qwen-image-layered": f"{settings.models_dir}/layered/qwen-image-layered",
}


class QwenImageHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        import torch
        from diffusers import DiffusionPipeline

        path = MODEL_REGISTRY.get(model_name)
        if path is None:
            raise ValueError(f"Unknown image model: {model_name}")

        log.info("model_loading", model=model_name, path=path)
        pipeline = DiffusionPipeline.from_pretrained(
            path,
            torch_dtype=torch.bfloat16,
            local_files_only=True,
            device_map="balanced",
        )
        log.info("model_loaded", model=model_name)
        return pipeline

    def unload(self, model: Any) -> None:
        import torch
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        log.info("model_unloaded")

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        import torch

        prompt = inputs["prompt"]
        negative_prompt = inputs.get("negative_prompt", "")
        width = int(params.get("width", 1024))
        height = int(params.get("height", 1024))
        steps = int(params.get("steps", 20))
        true_cfg_scale = float(params.get("cfg_scale", 7.0))
        seed = params.get("seed") or random.randint(0, 2**31 - 1)

        generator = None
        try:
            import torch
            generator = torch.Generator().manual_seed(seed)
        except Exception:
            pass

        log.info(
            "inference_started",
            model="qwen-image",
            width=width,
            height=height,
            steps=steps,
            seed=seed,
        )

        with torch.no_grad():
            result = model(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                width=width,
                height=height,
                num_inference_steps=steps,
                true_cfg_scale=true_cfg_scale,
                generator=generator,
            )

        images = result.images
        log.info("inference_completed", num_images=len(images), seed_used=seed)
        return {"images": images, "seed_used": seed}
