"""Qwen vision/VL handler — placeholder."""
import gc
from typing import Any

import structlog
from core.config import settings
from .base import BaseHandler

log = structlog.get_logger()

MODEL_REGISTRY = {
    "qwen3.5-vl-7b": f"{settings.models_dir}/qwen3.5-vl-7b",
}


class QwenVisionHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        raise NotImplementedError("Vision handler not yet implemented")

    def unload(self, model: Any) -> None:
        import torch
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        raise NotImplementedError("Vision inference not yet implemented")
