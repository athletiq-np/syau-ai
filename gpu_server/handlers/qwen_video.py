import base64
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from gpu_server.handlers.base import BaseHandler


class QwenVideoHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        return {"model_name": model_name, "mode": "mock"}

    def unload(self, model: Any) -> None:
        del model

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        width = int(params.get("width", 576) or 576)
        height = int(params.get("height", 576) or 576)
        frame_count = max(8, min(int(params.get("steps", 16) or 16), 24))
        prompt = inputs["prompt"][:80]

        frames = []
        for index in range(frame_count):
            frame = Image.new("RGB", (width, height), ((40 + index * 9) % 255, (90 + index * 7) % 255, (150 + index * 5) % 255))
            draw = ImageDraw.Draw(frame)
            draw.text((30, 30), "SYAUAI REMOTE VIDEO MOCK", fill=(255, 255, 255))
            draw.text((30, 70), f"Frame {index + 1}/{frame_count}", fill=(240, 240, 240))
            draw.text((30, 120), prompt, fill=(255, 255, 255))
            frames.append(frame)

        tmp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        frames[0].save(tmp_path, save_all=True, append_images=frames[1:], duration=160, loop=0, format="GIF")
        data = tmp_path.read_bytes()
        tmp_path.unlink(missing_ok=True)
        return {"video_bytes": data, "frames": frame_count}
