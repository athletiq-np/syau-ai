"""Qwen video generation handler.

Local development uses a mock animated GIF to stand in for video output.
GPU deployment can replace the mock generator with a real video pipeline once
the concrete model path and loader strategy are finalized.
"""
import gc
import tempfile
from pathlib import Path
from typing import Any

import structlog
from PIL import Image, ImageDraw
from .base import BaseHandler

log = structlog.get_logger()


class QwenVideoHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        log.info("video_model_loaded", model=model_name, mode="mock")
        return {"model_name": model_name, "mode": "mock"}

    def unload(self, model: Any) -> None:
        del model
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        log.info("video_model_unloaded")

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        prompt = inputs["prompt"]
        width = int(params.get("width", 576))
        height = int(params.get("height", 576))
        frame_count = max(8, min(int(params.get("steps", 16)), 24))

        frames: list[Image.Image] = []
        text = prompt[:80] or "SYAUAI mock video"
        for index in range(frame_count):
            background = (
                (40 + index * 9) % 255,
                (90 + index * 7) % 255,
                (150 + index * 5) % 255,
            )
            frame = Image.new("RGB", (width, height), background)
            draw = ImageDraw.Draw(frame)
            draw.rounded_rectangle(
                (24, 24, width - 24, height - 24),
                radius=28,
                outline=(255, 255, 255),
                width=4,
            )
            draw.text((40, 48), "SYAUAI VIDEO MOCK", fill=(255, 255, 255))
            draw.text((40, 88), f"Frame {index + 1}/{frame_count}", fill=(240, 240, 240))
            draw.text((40, 140), text, fill=(255, 255, 255))
            orb_x = 40 + int((width - 120) * index / max(frame_count - 1, 1))
            draw.ellipse((orb_x, height - 140, orb_x + 80, height - 60), fill=(255, 220, 120))
            frames.append(frame)

        tmp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        frames[0].save(
            tmp_path,
            save_all=True,
            append_images=frames[1:],
            duration=160,
            loop=0,
            format="GIF",
        )
        log.info("video_inference_completed", model=model["model_name"], frames=frame_count, output_path=str(tmp_path))
        return {"video_path": str(tmp_path), "frames": frame_count}
