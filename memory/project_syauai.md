---
name: SYAUAI Project Overview
description: SYAUAI self-hosted AI creative SaaS — architecture, phase, tech stack, GPU server details
type: project
---

Phase 1 in progress (no auth, no payments, just inference end-to-end).
**Why:** Get AI inference working before adding auth/payments (Phase 2).
**How to apply:** Do NOT add auth, Stripe, credits, workspaces, or user tables — these are Phase 2 only.

Project root: e:\Syau-ai
Structure: backend/ (FastAPI), frontend/ (Next.js 14), infra/ (nginx, scripts), tests/, gpu_server/

GPU server:
- Host: 202.51.2.50
- SSH port: 41447
- User used during setup: ekduiteen
- Private GPU API currently run manually with uvicorn on port 8100
- Local development reaches it through an SSH tunnel and `host.docker.internal:8100`

Current important model folders on GPU server:
- qwen-image-2512 → /data/models/t2i/qwen-image-2512
- qwen-image-layered → /data/models/layered/qwen-image-layered
- qwen-image-edit → /data/models/qwen-image-edit
- qwen3.5-7b-instruct → /data/models/llm/qwen3.5-7b-instruct
- qwen3.5-coder-7b → /data/models/llm/qwen3.5-coder-7b
- qwen3.5-vl-7b → /data/models/vlm/qwen3.5-vl-7b
- rmbg-1.4 → /data/models/utility/rmbg-1.4
- raw LTX-2.3 weights → /data/models/ltx-2.3/ltx-2.3-22b-distilled.safetensors and lora file
- downloaded Diffusers LTX bundle → /data/models/ltx-video

Local dev services (Docker): postgres, redis, minio, nginx, backend, frontend, worker-image, worker-video, worker-chat.
GPU server remains the target for real heavy inference workloads.

Current checkpoint:
- Step 1 complete: scaffold and Docker baseline are in place.
- Step 2 complete: config, SQLAlchemy, Alembic, jobs/models schema are working.
- Step 3 complete: FastAPI app, health route, WebSocket route, Redis pub/sub bridge are working.
- Step 4 complete: job API and model listing endpoints are working.
- Step 5 complete: Celery plumbing is working with dedicated queues.
- Step 6 complete with real remote image inference: qwen-image-2512 works end to end through the remote GPU API, uploads PNG outputs to MinIO, returns presigned URLs, and updates the UI live.
- Step 7 is partially complete and currently messy: there is working remote video plumbing and a working Diffusers LTX-Video experiment, but it is mislabeled as `ltx-2.3` and is not the true LTX-2.3 runtime path.
- Step 8 partially complete: chat plumbing works locally, remote-ready code exists, but full GPU-server chat deployment has not been revalidated after the video work.
- Step 9 mostly complete for Phase 1 local UX: `/generate`, `/video`, `/chat`, `/history`, landing page, job cards, filters, live updates, and asset actions are implemented.
- Step 10 substantially complete locally: model/type validation, Pydantic v2 cleanup, frontend dev cache mitigation, transient worker retries, stale job reconciliation, and API/worker tests are in place.

What works right now:
- Real remote qwen-image-2512 generation works from the UI through backend -> worker -> SSH tunnel -> GPU API -> MinIO.
- qwen-image-edit is wired through the same remote flow and can run successfully, but quality is not yet tuned and there is no masking support.
- Job status updates stream over WebSocket.
- Outputs are stored in MinIO and read back through presigned URLs.
- Frontend production build passes in Docker.
- History view supports filters and live refresh for active jobs.
- Backend startup reconciles stale `pending` and `running` jobs into failed jobs with an explanatory error.
- Workers retry transient storage/network-style failures instead of failing immediately.

What is unstable or unresolved:
- The frontend dev server still occasionally hits a Next.js stale chunk error (`Cannot find module './545.js'`) and sometimes needs a full frontend recreate.
- qwen-image-edit results are currently underwhelming because there is no prompt enhancement or masking yet.
- The currently working `ltx-2.3` path is actually using `/data/models/ltx-video`, which is a generic LTX-Video Diffusers bundle, not the raw `/data/models/ltx-2.3` checkpoint the user wanted.
- True LTX-2.3 integration likely requires the official LTX runtime or codebase under `/opt/ltx2`, not the temporary Diffusers fallback.
- An official LTX runtime repo was cloned to `/opt/ltx2`, `uv sync` succeeded there, but no true LTX-2.3 inference command has been wired into SYAUAI yet.
- Remote chat and coder models are partially wired in code but not fully end-to-end verified in the latest state.

Critical handoff warning:
- Do not assume the current `ltx-2.3` label in app code means true LTX-2.3 is working. The user explicitly wants true LTX-2.3, and the current Diffusers-based LTX experiment is not that.
- The user is frustrated by time spent on the wrong LTX path. Future work should clearly separate `working temporary LTX-Video Diffusers integration` from `true LTX-2.3 integration`.
