"""
Per-process model cache for Celery workers.

Each worker process keeps one model loaded in memory.
When a new model is requested, the old one is unloaded first.
Never share model objects between processes.
"""
from typing import Any, Optional
import structlog

log = structlog.get_logger()

_current_model: Optional[Any] = None
_current_model_name: Optional[str] = None
_current_handler: Optional[Any] = None


def get_model(model_name: str, handler: Any) -> Any:
    global _current_model, _current_model_name, _current_handler

    if _current_model_name != model_name:
        if _current_model is not None:
            log.info("model_unloading", model=_current_model_name)
            _current_handler.unload(_current_model)
            _current_model = None
            _current_model_name = None
            _current_handler = None

        log.info("model_loading", model=model_name)
        _current_model = handler.load(model_name)
        _current_model_name = model_name
        _current_handler = handler
        log.info("model_loaded", model=model_name)

    return _current_model
