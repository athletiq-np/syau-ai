"""Qwen chat/LLM handler.

Local development uses a deterministic mock response so the chat queue and
frontend contract can be exercised before a real GPU-backed model is wired in.
"""
import gc
from typing import Any

import structlog
from core.config import settings
from .base import BaseHandler

log = structlog.get_logger()


def _build_model_registry() -> dict[str, str]:
    registry = {
        "qwen3.5-7b-instruct": f"{settings.models_dir}/llm/qwen3.5-7b-instruct",
        "qwen2.5-7b-instruct-awq": f"{settings.models_dir}/llm/Qwen2.5-7B-Instruct-AWQ",
    }
    registry[settings.llm_default_model] = settings.llm_default_path
    registry[settings.llm_planner_model] = settings.llm_planner_path
    return registry


MODEL_REGISTRY = _build_model_registry()


class QwenChatHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        path = MODEL_REGISTRY.get(model_name)
        if path is None:
            raise ValueError(f"Unknown chat model: {model_name}")

        mode = settings.inference_mode.lower()
        if mode == "mock":
            log.info("chat_model_loaded", model=model_name, path=path, mode="mock")
            return {"model_name": model_name, "path": path, "mode": "mock"}

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                path,
                local_files_only=True,
                trust_remote_code=True,
            )
            load_kwargs: dict[str, Any] = {
                "local_files_only": True,
                "trust_remote_code": True,
            }
            if torch.cuda.is_available():
                load_kwargs["torch_dtype"] = torch.bfloat16
                load_kwargs["device_map"] = "auto"

            model = AutoModelForCausalLM.from_pretrained(path, **load_kwargs)
            log.info("chat_model_loaded", model=model_name, path=path, mode="real")
            return {
                "model_name": model_name,
                "path": path,
                "mode": "real",
                "tokenizer": tokenizer,
                "model": model,
            }
        except Exception as exc:
            if mode == "auto":
                log.warning("chat_model_fallback_to_mock", model=model_name, path=path, error=str(exc))
                return {"model_name": model_name, "path": path, "mode": "mock"}
            raise

    def unload(self, model: Any) -> None:
        del model
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        log.info("chat_model_unloaded")

    def infer(self, model: Any, inputs: dict, params: dict) -> dict:
        if model.get("mode") == "real":
            return self._infer_real(model, inputs, params)
        return self._infer_mock(model, inputs, params)

    def _infer_mock(self, model: dict, inputs: dict, params: dict) -> dict:
        prompt = inputs["prompt"].strip()
        negative_prompt = inputs.get("negative_prompt", "").strip()
        system_hint = "This is a local mock chat response for SYAUAI development."
        text = (
            f"{system_hint}\n\n"
            f"Model: {model['model_name']}\n"
            f"User prompt: {prompt}\n"
        )
        if negative_prompt:
            text += f"Avoid: {negative_prompt}\n"
        text += (
            "\nPlanned next step:\n"
            "A real Qwen chat backend will replace this mock once the GPU worker is wired in."
        )
        tokens_used = max(32, len(prompt.split()) * 6)
        log.info("chat_inference_completed", model=model["model_name"], tokens_used=tokens_used)
        return {"text": text, "tokens_used": tokens_used}

    def _infer_real(self, model_bundle: dict, inputs: dict, params: dict) -> dict:
        import torch

        tokenizer = model_bundle["tokenizer"]
        model = model_bundle["model"]
        prompt = inputs["prompt"].strip()
        negative_prompt = inputs.get("negative_prompt", "").strip()

        user_prompt = prompt
        if negative_prompt:
            user_prompt += f"\nAvoid: {negative_prompt}"

        system_prompt = (
            params.get("system_prompt")
            or "You are SYAUAI, a helpful creative studio assistant."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = tokenizer(rendered, return_tensors="pt")

        model_device = getattr(model, "device", None)
        if model_device is not None:
            model_inputs = {key: value.to(model_device) for key, value in model_inputs.items()}

        generate_kwargs: dict[str, Any] = {
            "max_new_tokens": settings.chat_max_new_tokens,
            "pad_token_id": tokenizer.eos_token_id,
        }
        if settings.chat_temperature > 0:
            generate_kwargs["do_sample"] = True
            generate_kwargs["temperature"] = settings.chat_temperature
        else:
            generate_kwargs["do_sample"] = False

        with torch.no_grad():
            output_ids = model.generate(**model_inputs, **generate_kwargs)

        prompt_tokens = model_inputs["input_ids"].shape[-1]
        new_tokens = output_ids[:, prompt_tokens:]
        text = tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0].strip()
        if not text:
            text = "Model returned an empty response."

        tokens_used = int(new_tokens.shape[-1])
        log.info("chat_inference_completed", model=model_bundle["model_name"], tokens_used=tokens_used, mode="real")
        return {"text": text, "tokens_used": tokens_used}
