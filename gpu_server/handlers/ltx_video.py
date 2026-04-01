from __future__ import annotations

import gc
import io
import random
import time
from typing import Any

import structlog
from PIL import Image
import torch
import numpy as np

from gpu_server.config import settings
from gpu_server.handlers.base import BaseHandler

# True LTX-2.3 official runtime
MODEL_REGISTRY = {
    "ltx-2.3": {
        "checkpoint": "/data/models/ltx-2.3/ltx-2.3-22b-distilled.safetensors",
        "gemma_root": "/data/models/ltx-2.3/gemma",
        "spatial_upsampler": "/data/models/ltx-2.3/ltx-2.3-spatial-upscaler-x2-1.0.safetensors",
    },
}

log = structlog.get_logger()


class LTXVideoHandler(BaseHandler):
    """True LTX-2.3 handler using the official DistilledPipeline runtime."""

    def load(self, model_name: str) -> Any:
        from ltx_pipelines.distilled import DistilledPipeline

        config = MODEL_REGISTRY.get(model_name)
        if config is None:
            raise ValueError(f"Unknown LTX video model: {model_name}")

        started_at = time.perf_counter()
        log.info("ltx23_loading", model_name=model_name)

        try:
            pipeline = DistilledPipeline(
                distilled_checkpoint_path=config["checkpoint"],
                gemma_root=config["gemma_root"],
                spatial_upsampler_path=config["spatial_upsampler"],
                loras=[],
                device=torch.device("cuda"),
                quantization=None,
                registry=None,
                torch_compile=False,
            )

            # Enable CPU offloading to reduce GPU memory pressure
            if hasattr(pipeline, "stage") and hasattr(pipeline.stage, "enable_model_cpu_offload"):
                pipeline.stage.enable_model_cpu_offload()
            if hasattr(pipeline, "upsampler") and hasattr(pipeline.upsampler, "enable_model_cpu_offload"):
                pipeline.upsampler.enable_model_cpu_offload()
            if hasattr(pipeline, "video_decoder") and hasattr(pipeline.video_decoder, "enable_model_cpu_offload"):
                pipeline.video_decoder.enable_model_cpu_offload()

            log.info(
                "ltx23_loaded",
                model_name=model_name,
                load_seconds=round(time.perf_counter() - started_at, 2),
            )
            return pipeline
        except Exception as e:
            log.error("ltx23_load_failed", model_name=model_name, error=str(e))
            raise

    def unload(self, model: Any) -> None:
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        prompt = inputs["prompt"]
        width = int(params.get("width", 768) or 768)
        height = int(params.get("height", 512) or 512)
        num_frames = int(params.get("num_frames", 97) or 97)
        frame_rate = float(params.get("frame_rate", 25.0) or 25.0)
        seed = params.get("seed") or random.randint(0, 2**31 - 1)
        enhance_prompt = params.get("enhance_prompt", False)

        started_at = time.perf_counter()
        log.info(
            "ltx23_inference_started",
            width=width,
            height=height,
            num_frames=num_frames,
            seed=seed,
        )

        try:
            # Call the official DistilledPipeline with layer streaming for memory efficiency
            frame_iterator, audio = model(
                prompt=prompt,
                seed=seed,
                height=height,
                width=width,
                num_frames=num_frames,
                frame_rate=frame_rate,
                images=[],  # No image conditioning for now
                tiling_config=None,
                enhance_prompt=enhance_prompt,
                streaming_prefetch_count=2,  # Stream 2 layers at a time to reduce peak memory
            )

            # Collect frames from the iterator
            frames = []
            for frame_tensor in frame_iterator:
                # frame_tensor is [C, H, W] in torch tensor format
                frame_np = frame_tensor.cpu().numpy()
                # Convert from [C, H, W] to [H, W, C]
                if frame_np.ndim == 3:
                    frame_np = np.transpose(frame_np, (1, 2, 0))
                # Convert from float [0, 1] to uint8 [0, 255]
                if frame_np.dtype != np.uint8:
                    frame_np = (np.clip(frame_np, 0, 1) * 255).astype(np.uint8)
                # Convert to PIL Image
                pil_frame = Image.fromarray(frame_np, mode="RGB")
                frames.append(pil_frame)

            if not frames:
                raise ValueError("LTX-2.3 generated no frames")

            gif_bytes = _frames_to_gif(frames)
            log.info(
                "ltx23_inference_completed",
                seed=seed,
                frame_count=len(frames),
                inference_seconds=round(time.perf_counter() - started_at, 2),
            )
            return {"video_bytes": gif_bytes, "frames": len(frames)}

        except Exception as e:
            log.error("ltx23_inference_failed", error=str(e), seed=seed)
            raise


def _coerce_frames(frames: Any) -> list[Image.Image]:
    if not frames:
        raise ValueError("LTX pipeline returned no frames")

    first = frames[0]
    if isinstance(first, list):
        frames = first

    coerced: list[Image.Image] = []
    for frame in frames:
        if isinstance(frame, Image.Image):
            coerced.append(frame.convert("RGB"))
        else:
            coerced.append(Image.fromarray(frame).convert("RGB"))
    return coerced


def _frames_to_gif(frames: list[Image.Image]) -> bytes:
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        format="GIF",
    )
    return buffer.getvalue()
