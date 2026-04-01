"""Base handler interface. All methods are synchronous."""
from typing import Any


class BaseHandler:
    def load(self, model_name: str) -> Any:
        """Load model from disk. Return model object."""
        raise NotImplementedError

    def unload(self, model: Any) -> None:
        """Free model from memory and release GPU VRAM."""
        raise NotImplementedError

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        """
        Run inference synchronously.

        Returns:
          Image handlers:  {"images": [PIL.Image, ...], "seed_used": int}
          Video handlers:  {"video_path": "/tmp/output.mp4", "frames": int}
          Chat handlers:   {"text": "...", "tokens_used": int}
        """
        raise NotImplementedError
