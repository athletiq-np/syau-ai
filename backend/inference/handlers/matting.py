"""Background removal handler (RMBG-1.4) — placeholder."""
import gc
from typing import Any

import structlog
from core.config import settings
from .base import BaseHandler

log = structlog.get_logger()


class MattingHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        raise NotImplementedError("Matting handler not yet implemented")

    def unload(self, model: Any) -> None:
        del model
        gc.collect()

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        raise NotImplementedError("Matting inference not yet implemented")
