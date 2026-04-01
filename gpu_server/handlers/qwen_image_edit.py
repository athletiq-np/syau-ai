from __future__ import annotations

import base64
import gc
import io
import random
import time
from typing import Any

import structlog
from PIL import Image

from gpu_server.config import settings
from gpu_server.handlers.base import BaseHandler

MODEL_REGISTRY = {
    "qwen-image-edit": f"{settings.models_dir}/qwen-image-edit",
}

log = structlog.get_logger()


class QwenImageEditHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        import torch
        from diffusers import QwenImageEditPipeline

        path = MODEL_REGISTRY.get(model_name)
        if path is None:
            raise ValueError(f"Unknown image edit model: {model_name}")

        started_at = time.perf_counter()
        pipeline = QwenImageEditPipeline.from_pretrained(
            path,
            torch_dtype=torch.bfloat16,
            local_files_only=True,
        )
        pipeline.enable_model_cpu_offload()
        pipeline.vae.enable_slicing()
        pipeline.vae.enable_tiling()
        log.info(
            "image_edit_model_loaded",
            model_name=model_name,
            path=path,
            load_seconds=round(time.perf_counter() - started_at, 2),
        )
        return pipeline

    def unload(self, model: Any) -> None:
        import torch

        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        import torch

        source_image = _decode_input_image(params.get("input_image_base64"))
        prompt = inputs["prompt"]
        negative_prompt = inputs.get("negative_prompt", "")
        width = int(params.get("width", source_image.width) or source_image.width)
        height = int(params.get("height", source_image.height) or source_image.height)
        steps = int(params.get("steps", 30) or 30)
        true_cfg_scale = float(params.get("cfg_scale", 4.0) or 4.0)
        seed = params.get("seed") or random.randint(0, 2**31 - 1)
        generator = torch.Generator(device="cpu").manual_seed(seed)

        if not negative_prompt and true_cfg_scale != 1.0:
            negative_prompt = " "

        started_at = time.perf_counter()
        log.info(
            "image_edit_inference_started",
            width=width,
            height=height,
            steps=steps,
            cfg_scale=true_cfg_scale,
            seed=seed,
        )
        with torch.no_grad():
            result = model(
                image=source_image,
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                width=width,
                height=height,
                num_inference_steps=steps,
                true_cfg_scale=true_cfg_scale,
                generator=generator,
            )

        log.info(
            "image_edit_inference_completed",
            seed=seed,
            image_count=len(result.images),
            inference_seconds=round(time.perf_counter() - started_at, 2),
        )
        return {"images": result.images, "seed_used": seed}


def _decode_input_image(value: str | None) -> Image.Image:
    if not value:
        raise ValueError("qwen-image-edit requires params.input_image_base64")

    encoded = value
    if "," in value and value.startswith("data:"):
        encoded = value.split(",", 1)[1]

    data = base64.b64decode(encoded)
    return Image.open(io.BytesIO(data)).convert("RGB")
