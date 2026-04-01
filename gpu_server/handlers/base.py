from typing import Any


class BaseHandler:
    def load(self, model_name: str) -> Any:
        raise NotImplementedError

    def unload(self, model: Any) -> None:
        raise NotImplementedError

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        raise NotImplementedError
