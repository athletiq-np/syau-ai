# SYAU AI Takeover Review

Last updated: 2026-04-02
Prepared for the next agent taking over after the current deployment/debugging session.

## Executive Summary

The original handover in `PROJECT_STATUS.md` is now partially stale.

The major changes completed in this session are:

- Remote GPU services on `202.51.2.50` are now working.
- Disk pressure on the remote server root filesystem has been resolved.
- `vLLM` has been migrated off the root-disk user install into `/data/venvs/vllm`.
- `ComfyUI` is running successfully from `/data/ComfyUI/venv`.
- The main app stack is running on the same remote server in a single-server deployment model.
- Public ingress to `http://202.51.2.50/` was restored after provider/network changes.
- Docker app services now work together with host-level `vLLM` and `ComfyUI`.

This means the project is no longer blocked on infrastructure bring-up. The next agent should focus on product verification, code sync, and remaining UX / pipeline issues.

## What Was Actually Done In This Session

### 1. Remote GPU service recovery

Remote server:
- Host: `202.51.2.50`
- SSH: `ssh -p 41447 ekduiteen@202.51.2.50`

Findings:
- The old handoff said disk was critically full and `vLLM` was broken.
- Actual live state differed from the stale handoff.
- Root disk was not 94 percent full after cleanup; it is now healthy.
- `syau-gpu-api.service` did not exist despite older notes referencing it.
- `vLLM` package itself was usable, but the old install path under `~/.local` was undesirable.
- The broken `comfyui` Docker container used a bad command (`python` instead of `python3`) and was abandoned in favor of the host venv.

### 2. ComfyUI fix

What was found:
- `/data/ComfyUI` already contained a healthy full install and its own `venv`.
- Running ComfyUI directly from `/data/ComfyUI/venv` worked correctly.

Current working host process:
- `./venv/bin/python main.py --listen 0.0.0.0 --port 8188`

Current state:
- `ComfyUI` is healthy on port `8188`.
- Health verified through `http://127.0.0.1:8188/system_stats`.

### 3. vLLM fix and migration

What was found:
- `vLLM` could run successfully with the local AWQ model at `/data/models/qwen2.5-awq`.
- The old heavy Python install was under `/home/ekduiteen/.local`, which was consuming root disk space.

What was done:
- Created a new dedicated venv at `/data/venvs/vllm`.
- Installed and validated `vLLM` there.
- Confirmed working launch with:

```bash
/data/venvs/vllm/bin/python -m vllm.entrypoints.openai.api_server \
  --model /data/models/qwen2.5-awq \
  --served-model-name qwen2.5-awq \
  --host 0.0.0.0 \
  --port 8100 \
  --quantization awq \
  --dtype float16 \
  --gpu-memory-utilization 0.2 \
  --max-model-len 1024
```

Important detail:
- A failed test with another model was due to high GPU memory demand, not a broken venv.
- The known-good settings above are the working baseline.

Current state:
- `vLLM` is healthy on port `8100`.
- Verified via `/v1/models` and backend connectivity checks.

### 4. Root disk cleanup and storage audit

A full storage audit was performed.

Actual filesystem layout:
- `/` on `ubuntu--vg-root`: 100G
- `/data` on `ubuntu--vg-data`: 1.9T

Key finding:
- `/home/ekduiteen` lives on the 100G root filesystem.
- Large user-local Python packages and caches were filling root, not `/data`.

Heavy root usage before cleanup included:
- `~/.local` around 12G
- `~/.cache/pip` around 4.4G
- `~/qwen_2.5_vl_7b_fp8_scaled.safetensors` around 9.3G

Safe cleanup performed:
- Removed `~/.cache/pip`
- Moved the large model file into `/data/models/manual`
- Removed old heavy user-space `vllm/torch/nvidia/triton` packages after confirming the new `/data/venvs/vllm` runtime worked

Result:
- root disk improved from about 83G used / 18G free to about 60G used / 41G free
- `~/.local` reduced to about 2.1G

Current storage status:
- Root disk is healthy
- `/data` is the correct location for models, venvs, caches, outputs, ComfyUI, and other large assets

### 5. Persistence across reboot

Because root `sudo` service management was not immediately available for all actions, a user-level persistence path was created using `tmux` plus `crontab`.

Remote files created:
- `/home/ekduiteen/bin/start-syau-vllm.sh`
- `/home/ekduiteen/bin/start-syau-comfyui.sh`

User crontab now includes:
- `@reboot /home/ekduiteen/bin/start-syau-vllm.sh`
- `@reboot /home/ekduiteen/bin/start-syau-comfyui.sh`

These startup scripts are syntactically valid.

Important nuance:
- After reboot, `ComfyUI` came back successfully.
- `vLLM` also came back, but initial checks were misleading until the log was reviewed carefully.
- Current reboot behavior is workable, but a future systemd-based setup is still cleaner if root access is available later.

### 6. Tailscale

Tailscale was installed on the GPU server.

Current Tailscale IP:
- `100.112.62.29`

This provides a private access path if needed.

### 7. Deployment direction changed: single-server production

Initial planning explored a split app-server / GPU-server model.

Final practical direction for this phase:
- run the app stack on the same remote server
- keep `vLLM` and `ComfyUI` on the host
- run frontend/backend/nginx/postgres/redis/minio/workers in Docker on the same box

This is now the active deployment model for the project on `202.51.2.50`.

### 8. Repo changes made for deployment

Deployment-related repo changes created in this session:
- `docker-compose.yml` updated to include:
  - `extra_hosts: ["host.docker.internal:host-gateway"]` on backend and workers
- `.env.production.example`
- `.env.single-server.example`
- `docs/PRODUCTION_ROLLOUT_PLAN.md`
- `docs/TAILSCALE_SETUP.md`
- `docs/SINGLE_SERVER_PRODUCTION.md`
- `infra/systemd/syau-vllm.service`
- `infra/systemd/syau-comfyui.service`

Important note:
- `docs/SINGLE_SERVER_PRODUCTION.md` still says `INFERENCE_API_BASE_URL=http://host.docker.internal:8100/v1`
- this is now stale for the actual single-server runtime
- the correct working value is:
  - `INFERENCE_API_BASE_URL=http://host.docker.internal:8100`

That doc should be corrected by the next agent.

## Current Live Production-Like State On 202.51.2.50

### Host services

Healthy:
- `vLLM` on `8100`
- `ComfyUI` on `8188`

Validation done:
- `curl http://127.0.0.1:8100/v1/models`
- `curl http://127.0.0.1:8188/system_stats`

### Docker app stack

Healthy:
- `nginx` on `80`
- `frontend` on `3000`
- `backend` on `8000`
- `worker-image`
- `worker-video`
- `worker-chat`
- `worker-studio`
- `postgres`
- `redis`
- `minio`

Validation done:
- `curl http://127.0.0.1/health` returns OK JSON
- `curl http://127.0.0.1/api/projects -H 'Authorization: Bearer syauai_dev_key_12345'` returns project data
- backend container can reach host inference endpoints:
  - `curl http://host.docker.internal:8100/v1/models`
  - `curl http://host.docker.internal:8188/system_stats`

### Public ingress

Status at the end of the session:
- `http://202.51.2.50/` became reachable after provider-side networking was adjusted

There was a real external networking issue earlier:
- the VM itself only had `172.16.39.108` and `100.112.62.29`
- `202.51.2.50` was provider-mapped rather than assigned on the VM interface
- provider-side changes were needed before public access worked

## Important Operational Quirks Discovered

### 1. Old handoff documents are stale

`PROJECT_STATUS.md` is now materially outdated in these ways:
- it says GPU services are blocked; they are no longer blocked
- it says disk is critically full; this is no longer true
- it refers to old remote conditions that no longer match the server

Future agents should not rely on `PROJECT_STATUS.md` as the final source of truth.

### 2. `docker-compose` v1 is fragile on this server

Remote server uses:
- `docker-compose version 1.29.2`

It repeatedly failed with:
- `KeyError: 'ContainerConfig'`
- `http+docker` Python package conflict errors when polluted by user site-packages

Reliable workarounds discovered:
- run compose commands with `PYTHONNOUSERSITE=1`
- avoid `--force-recreate` on stale containers when possible
- if recreate crashes, remove the old exited containers by exact name, then run `up -d` again

Pattern that worked:
1. inspect `docker ps -a`
2. remove stale exited containers with exact generated names
3. run `PYTHONNOUSERSITE=1 docker-compose up -d ...`

### 3. nginx may need restart after backend/frontend changes

At one point nginx returned `502` after backend/frontend recreation even though backend was healthy directly on `:8000`.

Fix was simply:
- `docker restart syauai_nginx_1`

This likely came from stale upstream resolution.

### 4. Wrong inference base URL caused double `/v1`

A real bug during deploy:
- backend container originally had `INFERENCE_API_BASE_URL=http://host.docker.internal:8100/v1`
- backend code also appended `/v1/...`
- result: `GET /v1/v1/models`

Correct runtime value is:
- `INFERENCE_API_BASE_URL=http://host.docker.internal:8100`

This was fixed in deployment env.

### 5. DB password mismatch caused backend health failure

Another deploy issue:
- `.env.production` initially used placeholder DB password `replace_with_strong_password`
- actual running Postgres password was still `syau`
- backend DB auth failed until fixed

Correct current deployment value is:
- `DATABASE_URL=postgresql://syau:syau@postgres:5432/syau`

### 6. Caddy was occupying port 80

Host-level `caddy` was listening on port 80 and blocking Docker nginx.

Resolution:
- stop Caddy to let Docker nginx bind to `80`

### 7. Frontend on server is still running in dev-oriented mode

The browser showed `_next/webpack-hmr` websocket errors.

That is a Next.js dev/HMR signal, not the product workflow websocket.

This means the server-side frontend setup is still not fully production-hardened. For now this is acceptable for staging/beta validation, but a future cleanup should run frontend in proper production build mode.

## Likely Current Product-Level Gaps

Infrastructure is now mostly solved, but these product-level items still need validation:

- Confirm the newest local workflow-editor code is actually on the remote server.
  - The remote homepage content looked older/dev-oriented during some checks.
  - Deployment files were copied, but not every full source sync was guaranteed at every step.
- Confirm workflow page on remote matches latest local changes.
- Confirm script analysis and generation flows really work end to end against live GPU services.
- Confirm WebSocket behavior in the live environment.
- Confirm output URLs, downloads, and final stitch behavior under real user flow.

## Recommended Next Tasks For The Next Agent

### Highest priority

1. Verify the remote workflow UI is the latest code.
   - Compare local workflow files vs remote deployment.
   - If needed, sync full `frontend` and relevant `backend` source again.

2. Run the end-to-end cinematic pipeline in browser on the remote server.
   - project list
   - project detail
   - workflow page
   - script analysis
   - shot generation
   - stitch/output

3. Watch these logs during live testing:
   - `docker logs -f syauai_backend_1`
   - `docker logs -f syauai_worker-studio_1`
   - `tail -f /tmp/vllm-live.log`
   - `tail -f /tmp/comfyui-live.log`

### Medium priority

4. Correct stale deployment docs:
   - fix `docs/SINGLE_SERVER_PRODUCTION.md` to remove the trailing `/v1` in `INFERENCE_API_BASE_URL`
   - add a note about `PYTHONNOUSERSITE=1 docker-compose ...`
   - update `PROJECT_STATUS.md` or replace it with a fresher server status doc

5. Lock down public ports.
   Current UFW output showed public allow rules for:
   - `8100`
   - `8188`

   If public access is no longer needed for those ports, tighten them.

6. Consider moving from user-crontab persistence to systemd services if root access is available and desired.

### Lower priority

7. Replace the old Python `docker-compose` v1 with the Docker Compose plugin (`docker compose`) if feasible.

8. Productionize the frontend container startup so the public server is not running Next.js dev/HMR behavior.

## Key Working Commands

### GPU host checks

```bash
curl http://127.0.0.1:8100/v1/models
curl http://127.0.0.1:8188/system_stats
```

### App health checks

```bash
curl http://127.0.0.1/health
curl http://127.0.0.1/api/projects -H "Authorization: Bearer syauai_dev_key_12345"
```

### Backend-to-host inference checks

```bash
PYTHONNOUSERSITE=1 docker-compose exec backend curl http://host.docker.internal:8100/v1/models
PYTHONNOUSERSITE=1 docker-compose exec backend curl http://host.docker.internal:8188/system_stats
```

### Compose safety on this server

```bash
PYTHONNOUSERSITE=1 docker-compose ps
PYTHONNOUSERSITE=1 docker-compose up -d backend frontend nginx worker-image worker-video worker-chat worker-studio
```

If compose crashes with `ContainerConfig`, remove the stale exited containers first using exact names from `docker ps -a`.

## Files The Next Agent Should Read First

1. `docs/TAKEOVER_REVIEW_2026-04-02.md` (this file)
2. `docs/SINGLE_SERVER_PRODUCTION.md`
3. `docker-compose.yml`
4. `.env.single-server.example`
5. local workflow/frontend/backend files if product behavior is being verified

## Repo State To Be Aware Of

At the time of writing, local `git status --short` showed deployment-related file changes including:
- modified `docker-compose.yml`
- new `.env.production.example`
- new `.env.single-server.example`
- new deployment docs under `docs/`
- new service templates under `infra/systemd/`

There are also unrelated user changes such as `.claude/settings.json`; do not revert user changes unless explicitly asked.

## Final Status Summary

What is now true:
- GPU infra is no longer the blocker.
- The single-server deployment on `202.51.2.50` is up.
- Backend, workers, Redis, Postgres, MinIO, nginx, and frontend are running.
- Host `vLLM` and host `ComfyUI` are running and reachable by backend.
- Public ingress works after provider/network changes.

What is still not fully closed:
- Full product end-to-end validation in browser
- Confirmation that the latest local code is what the remote server is serving
- Cleanup of stale docs and deployment polish
- Optional hardening of compose/frontend/proxy setup
