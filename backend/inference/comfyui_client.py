"""ComfyUI client — Wan 2.2 T2V/I2V inference via LightX2V dual-UNet 4-step approach."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional
import httpx

logger = logging.getLogger(__name__)

_WAN_DEFAULT_NEGATIVE = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
    "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，"
    "手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走，裸露，NSFW"
)


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    """Submit workflows to ComfyUI, poll for completion, download output."""

    def __init__(self, base_url: str = "http://localhost:8188"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 3600

    # ------------------------------------------------------------------
    # Text-to-Video  (Wan 2.2 14B, LightX2V 4-step dual-UNet)
    # ------------------------------------------------------------------

    def infer_wan_t2v(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 81,
        height: int = 640,
        width: int = 640,
        seed: int = 0,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> dict[str, Any]:
        """Generate video via Wan 2.2 T2V LightX2V 4-step dual-UNet."""
        workflow = {
            # CLIP / text encoder
            "1": {
                "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"},
                "class_type": "CLIPLoader",
            },
            "2": {
                "inputs": {"text": prompt, "clip": ["1", 0]},
                "class_type": "CLIPTextEncode",
            },
            "3": {
                "inputs": {"text": negative_prompt or _WAN_DEFAULT_NEGATIVE, "clip": ["1", 0]},
                "class_type": "CLIPTextEncode",
            },
            # VAE
            "4": {"inputs": {"vae_name": "wan_2.1_vae.safetensors"}, "class_type": "VAELoader"},
            # Dual UNets + LoRAs (LightX2V 4-step)
            "5": {
                "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"},
                "class_type": "UNETLoader",
            },
            "6": {
                "inputs": {"unet_name": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"},
                "class_type": "UNETLoader",
            },
            "7": {
                "inputs": {"lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors", "strength_model": 1.0, "model": ["5", 0]},
                "class_type": "LoraLoaderModelOnly",
            },
            "8": {
                "inputs": {"lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors", "strength_model": 1.0, "model": ["6", 0]},
                "class_type": "LoraLoaderModelOnly",
            },
            # ModelSamplingSD3 shift
            "9":  {"inputs": {"shift": 5.0, "model": ["7", 0]}, "class_type": "ModelSamplingSD3"},
            "10": {"inputs": {"shift": 5.0, "model": ["8", 0]}, "class_type": "ModelSamplingSD3"},
            # Empty latent (T2V)
            "11": {
                "inputs": {"width": width, "height": height, "length": num_frames, "batch_size": 1},
                "class_type": "EmptyHunyuanLatentVideo",
            },
            # Stage 1: high-noise model, steps 0→2
            "12": {
                "inputs": {
                    "add_noise": "enable", "noise_seed": seed, "steps": 4, "cfg": 1,
                    "sampler_name": "euler", "scheduler": "simple",
                    "start_at_step": 0, "end_at_step": 2, "return_with_leftover_noise": "enable",
                    "model": ["9", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["11", 0],
                },
                "class_type": "KSamplerAdvanced",
            },
            # Stage 2: low-noise model, steps 2→4
            "13": {
                "inputs": {
                    "add_noise": "disable", "noise_seed": 0, "steps": 4, "cfg": 1,
                    "sampler_name": "euler", "scheduler": "simple",
                    "start_at_step": 2, "end_at_step": 4, "return_with_leftover_noise": "disable",
                    "model": ["10", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["12", 0],
                },
                "class_type": "KSamplerAdvanced",
            },
            # Decode + save
            "14": {"inputs": {"samples": ["13", 0], "vae": ["4", 0]}, "class_type": "VAEDecode"},
            "15": {"inputs": {"fps": 16, "images": ["14", 0]}, "class_type": "CreateVideo"},
            "16": {
                "inputs": {"filename_prefix": "video/wan_t2v", "format": "auto", "codec": "auto", "video": ["15", 0]},
                "class_type": "SaveVideo",
            },
        }
        return self._run_workflow(workflow, on_progress=on_progress)

    # ------------------------------------------------------------------
    # Image-to-Video  (Wan 2.2 14B I2V, LightX2V 4-step dual-UNet)
    # ------------------------------------------------------------------

    def infer_wan_i2v(
        self,
        image_filename: str,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 81,
        height: int = 640,
        width: int = 640,
        seed: int = 0,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> dict[str, Any]:
        """
        Generate video from a start image via Wan 2.2 I2V LightX2V 4-step.
        `image_filename` must already be uploaded to ComfyUI's input folder.
        """
        workflow = {
            # Load start image
            "1": {"inputs": {"image": image_filename}, "class_type": "LoadImage"},
            # CLIP / text encoder
            "2": {
                "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"},
                "class_type": "CLIPLoader",
            },
            "3": {"inputs": {"text": prompt, "clip": ["2", 0]}, "class_type": "CLIPTextEncode"},
            "4": {
                "inputs": {"text": negative_prompt or _WAN_DEFAULT_NEGATIVE, "clip": ["2", 0]},
                "class_type": "CLIPTextEncode",
            },
            # VAE
            "5": {"inputs": {"vae_name": "wan_2.1_vae.safetensors"}, "class_type": "VAELoader"},
            # I2V latent conditioner (encodes start_image into latent space + conditioning)
            "6": {
                "inputs": {
                    "width": width, "height": height, "length": num_frames, "batch_size": 1,
                    "positive": ["3", 0], "negative": ["4", 0],
                    "vae": ["5", 0], "start_image": ["1", 0],
                },
                "class_type": "WanImageToVideo",
            },
            # Dual UNets + LoRAs (LightX2V 4-step I2V)
            "7": {
                "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"},
                "class_type": "UNETLoader",
            },
            "8": {
                "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"},
                "class_type": "UNETLoader",
            },
            "9": {
                "inputs": {"lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", "strength_model": 1.0, "model": ["7", 0]},
                "class_type": "LoraLoaderModelOnly",
            },
            "10": {
                "inputs": {"lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", "strength_model": 1.0, "model": ["8", 0]},
                "class_type": "LoraLoaderModelOnly",
            },
            "11": {"inputs": {"shift": 5.0, "model": ["9", 0]}, "class_type": "ModelSamplingSD3"},
            "12": {"inputs": {"shift": 5.0, "model": ["10", 0]}, "class_type": "ModelSamplingSD3"},
            # Stage 1: high-noise, steps 0→2
            "13": {
                "inputs": {
                    "add_noise": "enable", "noise_seed": seed, "steps": 4, "cfg": 1,
                    "sampler_name": "euler", "scheduler": "simple",
                    "start_at_step": 0, "end_at_step": 2, "return_with_leftover_noise": "enable",
                    "model": ["11", 0], "positive": ["6", 0], "negative": ["6", 1], "latent_image": ["6", 2],
                },
                "class_type": "KSamplerAdvanced",
            },
            # Stage 2: low-noise, steps 2→4
            "14": {
                "inputs": {
                    "add_noise": "disable", "noise_seed": 0, "steps": 4, "cfg": 1,
                    "sampler_name": "euler", "scheduler": "simple",
                    "start_at_step": 2, "end_at_step": 4, "return_with_leftover_noise": "disable",
                    "model": ["12", 0], "positive": ["6", 0], "negative": ["6", 1], "latent_image": ["13", 0],
                },
                "class_type": "KSamplerAdvanced",
            },
            # Decode + save
            "15": {"inputs": {"samples": ["14", 0], "vae": ["5", 0]}, "class_type": "VAEDecode"},
            "16": {"inputs": {"fps": 16, "images": ["15", 0]}, "class_type": "CreateVideo"},
            "17": {
                "inputs": {"filename_prefix": "video/wan_i2v", "format": "auto", "codec": "auto", "video": ["16", 0]},
                "class_type": "SaveVideo",
            },
        }
        return self._run_workflow(workflow, on_progress=on_progress)

    def upload_image(self, image_bytes: bytes, filename: str = "input.jpg") -> str:
        """Upload an image to ComfyUI's input folder. Returns the filename."""
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/upload/image",
                files={"image": (filename, image_bytes, "image/jpeg")},
                data={"overwrite": "true"},
            )
            response.raise_for_status()
            return response.json()["name"]

    def download_output(self, filename: str, subfolder: str = "", file_type: str = "output") -> bytes:
        """Download a completed output file from ComfyUI via /view endpoint."""
        with httpx.Client(timeout=300) as client:
            response = client.get(
                f"{self.base_url}/view",
                params={"filename": filename, "subfolder": subfolder, "type": file_type},
            )
            response.raise_for_status()
            return response.content

    def _run_workflow(
        self,
        workflow: dict,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> dict[str, Any]:
        """Submit workflow, wait for completion, download and return video bytes."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/prompt", json={"prompt": workflow})
                response.raise_for_status()
                result = response.json()
                prompt_id = result.get("prompt_id")
                if not prompt_id:
                    raise ComfyUIError("No prompt_id returned from ComfyUI")
                logger.info("comfyui_job_submitted | prompt_id=%s", prompt_id)

            completion = self._wait_for_completion(prompt_id, on_progress=on_progress)

            if not completion["videos"]:
                raise ComfyUIError("ComfyUI returned no video output")

            video_info = completion["videos"][0]
            logger.info("comfyui_downloading_video | filename=%s", video_info["filename"])
            video_bytes = self.download_output(
                filename=video_info["filename"],
                subfolder=video_info["subfolder"],
                file_type=video_info["type"],
            )

            filename = video_info["filename"]
            content_type = (
                "video/mp4" if filename.endswith(".mp4")
                else "video/webm" if filename.endswith(".webm")
                else "image/gif"
            )
            logger.info("comfyui_video_ready | filename=%s size_bytes=%s", filename, len(video_bytes))
            return {"video_bytes": video_bytes, "filename": filename, "content_type": content_type}

        except httpx.HTTPError as e:
            logger.error("comfyui_http_error | error=%s", str(e))
            raise ComfyUIError(f"ComfyUI HTTP error: {e}") from e

    def _wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: int = 2,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> dict[str, Any]:
        """Poll ComfyUI history until job completes. Returns structured video info."""
        max_wait = 3600
        elapsed = 0
        last_progress_report = 0

        with httpx.Client(timeout=self.timeout) as client:
            while elapsed < max_wait:
                try:
                    response = client.get(f"{self.base_url}/history/{prompt_id}")
                    response.raise_for_status()
                    history = response.json()

                    if prompt_id in history:
                        job = history[prompt_id]
                        if "outputs" in job:
                            logger.info("comfyui_job_complete | prompt_id=%s elapsed=%ss", prompt_id, elapsed)
                            logger.info("comfyui_outputs_raw | outputs=%s", job["outputs"])
                            videos = []
                            for node_id, node_out in job["outputs"].items():
                                logger.info("comfyui_node_output | node_id=%s output=%s", node_id, node_out)
                                # Check all possible video output keys
                                for key in ("videos", "gifs", "images"):
                                    for v in node_out.get(key, []):
                                        if isinstance(v, dict) and "filename" in v:
                                            fname = v.get("filename", "")
                                            # Only collect video files (not plain images)
                                            if key in ("videos", "gifs") or any(
                                                fname.endswith(ext) for ext in (".mp4", ".webm", ".gif", ".mkv", ".mov")
                                            ):
                                                videos.append({
                                                    "filename": fname,
                                                    "subfolder": v.get("subfolder", ""),
                                                    "type": v.get("type", "output"),
                                                })
                            logger.info("comfyui_videos_found | count=%s videos=%s", len(videos), videos)
                            return {"videos": videos}

                    if on_progress and elapsed - last_progress_report >= 30:
                        minutes = elapsed // 60
                        pct = min(80, 10 + int(elapsed / max_wait * 70))
                        on_progress(pct, f"Generating... {minutes}m elapsed")
                        last_progress_report = elapsed

                    time.sleep(poll_interval)
                    elapsed += poll_interval

                except httpx.HTTPError as e:
                    logger.error("comfyui_poll_error | error=%s", str(e))
                    raise ComfyUIError(f"ComfyUI poll error: {e}") from e

        raise ComfyUIError(f"ComfyUI job {prompt_id} did not complete within {max_wait}s")
