# Claude Handoff — 2026-03-31

You are taking over SYAUAI development in VS Code.

## High-level product
SYAUAI is a self-hosted AI creative studio SaaS with:
- FastAPI backend
- Next.js frontend
- Celery workers
- Redis, Postgres, MinIO
- separate GPU server reached through a private API

Phase 1 scope is still:
- no auth
- no payments
- inference first
- simple usable UI

## Repo location
- Windows/local repo: `e:\Syau-ai`
- GPU server: `202.51.2.50`
- SSH port: `41447`
- user used so far: `ekduiteen`

## Current local runtime setup
Local Docker app is running backend, frontend, worker-image, worker-video, worker-chat, Redis, Postgres, MinIO, nginx.

Remote inference currently works through:
- SSH tunnel from Windows host to GPU server port 8100
- local `.env` uses `INFERENCE_MODE=remote`
- local backend/worker containers point to `http://host.docker.internal:8100`

The GPU API on the server is currently started manually with uvicorn from `/opt/syauai/gpu_server`.

## What definitely works
1. Real remote qwen-image-2512 generation works end to end.
- frontend -> backend -> worker-image -> remote GPU API -> MinIO -> UI
- this was verified successfully

2. qwen-image-edit is wired and can execute remotely.
- it needs uploaded source image data in params
- it produces results, but quality is not tuned yet
- there is no masking support yet

3. Frontend pages exist and are mostly usable.
- `/generate`
- `/video`
- `/chat`
- `/history`
- landing page `/`

4. Core backend plumbing is in good shape.
- job creation
- model validation
- websocket updates
- stale job reconciliation
- transient retries
- MinIO presigned URLs

## What is messy / unresolved
1. Frontend dev server still intermittently breaks.
- recurring Next.js error: `Cannot find module './545.js'`
- usually fixed by full frontend recreate
- this is a dev-server/cache issue, not usually an app-code issue

2. Video work is the most confusing area.
There are now two different realities:
- temporary working Diffusers LTX-Video experiment
- desired true LTX-2.3 integration

The user explicitly wants true `LTX-2.3`.

3. Current `ltx-2.3` label in app code is misleading.
- temporary working path used `/data/models/ltx-video`
- that folder is a generic `LTX-Video` Diffusers package with `model_index.json`
- it is not the same as the raw `/data/models/ltx-2.3/*.safetensors` checkpoint the user actually wanted

4. Official LTX runtime investigation has started but is not integrated.
- repo cloned on GPU server: `/opt/ltx2`
- `uv sync` succeeded there
- it created `/opt/ltx2/.venv`
- Python 3.12 had to be installed first
- no actual official-runtime inference command has been tested yet
- do not assume true LTX-2.3 works in SYAUAI yet

## Important server-side paths currently present
### Real image/chat/edit assets
- `/data/models/t2i/qwen-image-2512`
- `/data/models/layered/qwen-image-layered`
- `/data/models/qwen-image-edit`
- `/data/models/llm/qwen3.5-7b-instruct`
- `/data/models/llm/qwen3.5-coder-7b`
- `/data/models/vlm/qwen3.5-vl-7b`
- `/data/models/utility/rmbg-1.4`

### Video-related paths
- raw desired weights: `/data/models/ltx-2.3/ltx-2.3-22b-distilled.safetensors`
- temporary Diffusers bundle: `/data/models/ltx-video`
- official runtime repo: `/opt/ltx2`

## Files changed significantly during this phase
### Backend / local app
- `backend/inference/remote_client.py`
- `backend/workers/image_worker.py`
- `backend/workers/video_worker.py`
- `backend/workers/chat_worker.py`
- `backend/schemas/job.py`
- `frontend/lib/api.ts`
- `frontend/components/generate-form.tsx`
- `frontend/components/video-form.tsx`
- `frontend/components/job-card.tsx`
- `frontend/app/generate/page.tsx`
- `docker-compose.yml`

### GPU API package
- `gpu_server/app.py`
- `gpu_server/schemas.py`
- `gpu_server/handlers/qwen_image.py`
- `gpu_server/handlers/qwen_image_edit.py`
- `gpu_server/handlers/ltx_video.py`
- `gpu_server/handlers/qwen_chat.py`
- `gpu_server/requirements.txt`

## Why the user is frustrated
- They wanted true LTX-2.3.
- A lot of time was spent making a Diffusers-based LTX path run.
- That path turned out to be a different LTX package, not true LTX-2.3.
- Be explicit about this. Do not blur the distinction.

## Recommended next step for you
Choose and state one path clearly before writing more code:

### Path A: honest temporary video path
- rename current temporary model from `ltx-2.3` to something truthful like `ltx-video`
- keep it working as a temporary Diffusers-based option
- defer true LTX-2.3

### Path B: true LTX-2.3
- stop using the Diffusers fallback for that model name
- inspect `/opt/ltx2` official runtime docs/scripts
- run a standalone true LTX-2.3 inference directly against `/data/models/ltx-2.3/ltx-2.3-22b-distilled.safetensors`
- only after standalone success, wire it back into `gpu_server/app.py`

Path B is what the user wants.

## Constraints and preferences
- User is not advanced with server/runtime setup and needs explicit step-by-step guidance.
- User is in the middle of running commands on the remote Ubuntu box.
- Avoid vague suggestions. Give exact commands.
- Be honest when a model/runtime path is not really what was requested.
- Do not add auth/payments/credits/workspaces.

## Suggested opening to continue
"I’m taking over from the current state where remote qwen image works, qwen-image-edit runs but is untuned, and video is split between a temporary Diffusers LTX path and the true LTX-2.3 runtime you actually want. I’m going to inspect `/opt/ltx2` first, find the official standalone inference entrypoint, and verify a direct LTX-2.3 run against `/data/models/ltx-2.3/ltx-2.3-22b-distilled.safetensors` before touching SYAUAI’s handler again."
