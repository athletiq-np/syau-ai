---
name: SYAUAI Technical Decisions
description: Key technical rules for SYAUAI — inference loading, handler interface, model cache pattern
type: project
---

Key technical rules (violation = bugs):
- DiffusionPipeline.from_pretrained, NOT AutoModelForCausalLM for Qwen image models.
- For qwen-image-2512 on the remote GPU API, CPU offload is currently safer than forcing the whole model onto CUDA on the 44GB GPU.
- Inference parameter is `true_cfg_scale` not `cfg_scale` for QwenImagePipeline and QwenImageEditPipeline.
- All handler methods MUST be synchronous (no async def) — Celery runs sync threads.
- Output keys are stored in DB, presigned URLs are generated at read time with 1-hour expiry.
- Model cache pattern is one model per worker or GPU API process, unload old before loading new.
- Workers publish Redis pub/sub events on channel `job_events:{job_id}`.
- FastAPI subscribes to Redis pub/sub and forwards to WebSocket clients.
- Worker tasks use shared retry handling for transient errors and should only hard-fail non-retryable exceptions.
- Backend startup reconciles stale `pending` and `running` jobs using timeout thresholds from config.
- Docker `restart` is not enough to reload changed `.env` values; worker containers needed full recreate to pick up remote inference settings.
- Next.js dev in Docker is still fragile in this repo and can re-enter a stale chunk state that requires full frontend recreate.

Remote inference rules:
- Local Docker development currently uses `INFERENCE_MODE=remote` with `INFERENCE_API_BASE_URL=http://host.docker.internal:8100`.
- That only works when an SSH tunnel from the Windows host to the GPU server is open.
- The GPU API is currently started manually on the server with uvicorn and reads `/opt/syauai/gpu_server/.env`.

Video-specific warning:
- The current Diffusers-based `ltx-2.3` experiment is not true LTX-2.3. It is using `/data/models/ltx-video`, a generic LTX-Video Diffusers package.
- The user wants real LTX-2.3 from `/data/models/ltx-2.3/*.safetensors`.
- Future work must clearly choose between the temporary Diffusers path and a true LTX-2.3 runtime path before changing more code.

ComfyUI note:
- Original project direction avoided ComfyUI for API cleanliness.
- That decision may need to be revisited specifically for difficult video runtimes like true LTX-2.3 if official runtime integration becomes too costly.

**Why:** Architecture choices were made to avoid async/sync conflicts, URL expiry bugs, and model-loading ambiguity while keeping the SaaS flow simple.
**How to apply:** Always verify model format, runtime expectations, and server path layout before adding new GPU-backed handlers.
