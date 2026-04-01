import gc
from typing import Any

from gpu_server.config import settings
from gpu_server.handlers.base import BaseHandler

MODEL_REGISTRY = {
    "qwen3.5-7b-instruct": f"{settings.models_dir}/qwen3.5-7b-instruct",
}


class QwenChatHandler(BaseHandler):
    def load(self, model_name: str) -> Any:
        if settings.inference_mode == "mock":
            return {"model_name": model_name, "mode": "mock"}

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        path = MODEL_REGISTRY.get(model_name)
        if path is None:
            raise ValueError(f"Unknown chat model: {model_name}")

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
        return {"model_name": model_name, "mode": "real", "model": model, "tokenizer": tokenizer}

    def unload(self, model: Any) -> None:
        del model
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def infer(self, model_bundle: dict, inputs: dict, params: dict) -> dict:
        if model_bundle.get("mode") == "mock":
            text = f"Mock GPU server response for prompt: {inputs['prompt']}"
            return {"text": text, "tokens_used": max(16, len(inputs["prompt"].split()) * 4)}

        import torch

        tokenizer = model_bundle["tokenizer"]
        model = model_bundle["model"]
        prompt = inputs["prompt"].strip()
        negative_prompt = inputs.get("negative_prompt", "").strip()
        user_prompt = prompt if not negative_prompt else f"{prompt}\nAvoid: {negative_prompt}"
        messages = [
            {"role": "system", "content": "You are SYAUAI, a helpful creative studio assistant."},
            {"role": "user", "content": user_prompt},
        ]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = tokenizer(rendered, return_tensors="pt")

        model_device = getattr(model, "device", None)
        if model_device is not None:
            model_inputs = {key: value.to(model_device) for key, value in model_inputs.items()}

        generate_kwargs = {
            "max_new_tokens": settings.chat_max_new_tokens,
            "pad_token_id": tokenizer.eos_token_id,
            "do_sample": settings.chat_temperature > 0,
        }
        if settings.chat_temperature > 0:
            generate_kwargs["temperature"] = settings.chat_temperature

        with torch.no_grad():
            output_ids = model.generate(**model_inputs, **generate_kwargs)

        prompt_tokens = model_inputs["input_ids"].shape[-1]
        new_tokens = output_ids[:, prompt_tokens:]
        text = tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0].strip() or "Model returned an empty response."
        return {"text": text, "tokens_used": int(new_tokens.shape[-1])}
