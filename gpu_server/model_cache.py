from typing import Any, Optional

_current_model = None
_current_model_name: Optional[str] = None
_current_handler: Optional[Any] = None


def get_model(model_name: str, handler: Any) -> Any:
    global _current_model, _current_model_name, _current_handler

    if _current_model_name != model_name:
        if _current_model is not None and _current_handler is not None:
            _current_handler.unload(_current_model)
            _current_model = None
            _current_model_name = None
            _current_handler = None

        _current_model = handler.load(model_name)
        _current_model_name = model_name
        _current_handler = handler

    return _current_model
