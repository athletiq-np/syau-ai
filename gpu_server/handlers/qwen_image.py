import gc
import random
import time
from typing import Any

import structlog

from gpu_server.config import settings
from gpu_server.handlers.base import BaseHandler

MODEL_REGISTRY = {
    "qwen-image-2512": f"{settings.models_dir}/t2i/qwen-image-2512",
    "qwen-image-layered": f"{settings.models_dir}/layered/qwen-image-layered",
}

log = structlog.get_logger()


class QwenImageHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        import torch
        from diffusers import DiffusionPipeline

        path = MODEL_REGISTRY.get(model_name)
        if path is None:
            raise ValueError(f"Unknown image model: {model_name}")

        started_at = time.perf_counter()
        pipeline = DiffusionPipeline.from_pretrained(
            path,
            torch_dtype=torch.bfloat16,
            local_files_only=True,
        )
        pipeline.enable_model_cpu_offload()
        pipeline.vae.enable_slicing()
        pipeline.vae.enable_tiling()
        log.info(
            "image_model_loaded",
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

        prompt = inputs["prompt"]
        negative_prompt = inputs.get("negative_prompt", "")
        width = int(params.get("width", 1024) or 1024)
        height = int(params.get("height", 1024) or 1024)
        steps = int(params.get("steps", 20) or 20)
        true_cfg_scale = float(params.get("cfg_scale", 7.0) or 7.0)
        seed = params.get("seed") or random.randint(0, 2**31 - 1)
        generator = torch.Generator(device="cpu").manual_seed(seed)

        if not negative_prompt and true_cfg_scale != 1.0:
            negative_prompt = " "

        started_at = time.perf_counter()
        log.info(
            "image_inference_started",
            width=width,
            height=height,
            steps=steps,
            cfg_scale=true_cfg_scale,
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

        log.info(
            "image_inference_completed",
            seed=seed,
            image_count=len(result.images),
            inference_seconds=round(time.perf_counter() - started_at, 2),
        )
        return {"images": result.images, "seed_used": seed}
