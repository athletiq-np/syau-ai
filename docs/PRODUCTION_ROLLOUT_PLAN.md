# SYAU AI Production Rollout Plan

Last updated: 2026-04-02

## Goal

Deploy SYAU AI so multiple external testers can access the product reliably without depending on a developer laptop or local SSH tunnels.

## Chosen Architecture

Use a two-server production topology:

- App server
  - `frontend`
  - `backend`
  - `nginx`
  - `worker-image`
  - `worker-video`
  - `worker-chat`
  - `worker-studio`
  - `postgres`
  - `redis`
  - `minio`
- GPU server
  - `vLLM`
  - `ComfyUI`
- Private connectivity between them
  - Preferred: `Tailscale`
  - Fallback: `WireGuard`
  - Temporary fallback: persistent server-side `autossh`

This keeps only the product surface public while the GPU services stay private.

## Why This Is The Best Option

- Multiple people can use the product at the same time.
- The system no longer depends on a local PC staying on.
- `vLLM` and `ComfyUI` stay off the public internet.
- It matches the current SYAU architecture: async API + Celery + private inference services.
- It is the fastest path to a real production test environment without redesigning the application.

## Network Topology

### Public

- `https://app.syau.ai`
- `https://app.syau.ai/api`
- `wss://app.syau.ai/ws`

### Private Only

- `postgres:5432`
- `redis:6379`
- `minio:9000`
- `vLLM:8100`
- `ComfyUI:8188`

### Data Flow

1. Tester opens `app.syau.ai`
2. `nginx` routes UI traffic to `frontend`
3. `nginx` routes `/api` and `/ws` to `backend`
4. `backend` and workers talk to:
   - `postgres`
   - `redis`
   - `minio`
   - remote GPU services over private network
5. GPU server responds only to the app server over Tailscale/private IP

## Recommended Connectivity: Tailscale

Install Tailscale on:

- app server
- GPU server

After joining the same tailnet, the app server should talk to the GPU server using its Tailscale IP or MagicDNS hostname.

Example:

```env
INFERENCE_API_BASE_URL=http://100.64.10.20:8100/v1
COMFYUI_URL=http://100.64.10.20:8188
```

If MagicDNS is enabled:

```env
INFERENCE_API_BASE_URL=http://gpu-server.tailnet-name.ts.net:8100/v1
COMFYUI_URL=http://gpu-server.tailnet-name.ts.net:8188
```

## Current Repo Alignment

The repo already supports the app-server side of this topology well:

- `docker-compose.yml` runs the full app stack locally
- `infra/nginx/nginx.conf` already separates `/`, `/api/`, and `/ws/`
- `.env` already supports remote inference through:
  - `INFERENCE_MODE=remote`
  - `INFERENCE_API_BASE_URL=...`
  - `COMFYUI_URL=...`

What should change for production:

- do not use laptop-based SSH tunnels
- do not expose `8100` or `8188` publicly
- point app containers to the GPU server over private networking
- use production domain/TLS for frontend and API

## Production Environment Variables

Create a production env file for the app server with values like:

```env
DATABASE_URL=postgresql://syau:strong_password@postgres:5432/syau
REDIS_URL=redis://redis:6379/0

MINIO_ENDPOINT=minio:9000
MINIO_PUBLIC_ENDPOINT=https://files.syau.ai
MINIO_ACCESS_KEY=replace_me
MINIO_SECRET_KEY=replace_me_too
MINIO_BUCKET=syau-outputs
MINIO_SECURE=false

COMFYUI_URL=http://100.64.10.20:8188
MODELS_DIR=/data/models
LOG_LEVEL=INFO
ENVIRONMENT=production

INFERENCE_MODE=remote
INFERENCE_API_BASE_URL=http://100.64.10.20:8100/v1
INFERENCE_API_KEY=replace_me
INFERENCE_TIMEOUT_SECONDS=180

CHAT_MAX_NEW_TOKENS=512
CHAT_TEMPERATURE=0.7

API_KEY_ENABLED=true
API_KEY_DEV=disable_or_rotate
API_KEY_TEST=disable_or_rotate
```

Frontend environment should become:

```env
NEXT_PUBLIC_API_URL=https://app.syau.ai/api
NEXT_PUBLIC_WS_URL=wss://app.syau.ai/ws
```

## Deployment Phases

### Phase 1: Stabilize GPU Server

Success criteria:

- `vLLM` responds on remote `8100`
- `ComfyUI` responds on remote `8188`
- both services start automatically after reboot

Tasks:

1. Replace ad hoc launches with persistent service definitions
2. Make `vLLM` and `ComfyUI` restart automatically
3. Document logs and health checks
4. Keep them listening on `0.0.0.0`
5. Restrict access at the network layer to private traffic only

### Phase 2: Stand Up App Server

Success criteria:

- app stack runs on a dedicated server
- public users can load the site
- backend can reach GPU services privately

Tasks:

1. Provision Linux app server
2. Install Docker and Docker Compose plugin
3. Clone repo
4. Create production `.env`
5. Bring up:
   - `postgres`
   - `redis`
   - `minio`
   - `backend`
   - `frontend`
   - `nginx`
   - all workers

### Phase 3: Connect Servers Privately

Success criteria:

- app server reaches GPU server without local tunnels
- no public dependency on developer workstation

Tasks:

1. Install Tailscale on app server
2. Install Tailscale on GPU server
3. Confirm private ping between them
4. Confirm app server can call:
   - `http://gpu-private-ip:8100/health`
   - `http://gpu-private-ip:8188/system_stats`
5. Update app server `.env`
6. Restart backend and workers

### Phase 4: Public Domain + TLS

Success criteria:

- testers can access product using domain
- secure `https` and `wss` traffic

Tasks:

1. Point DNS `app.syau.ai` to app server
2. Install TLS certificate
3. Update nginx to serve HTTPS
4. Redirect HTTP to HTTPS
5. Verify:
   - frontend page load
   - API auth
   - WebSocket connection

### Phase 5: External Testing

Success criteria:

- multiple testers can create projects, analyze scripts, and generate outputs

Tasks:

1. Create tester accounts or distribute auth keys safely
2. Run 2-3 simultaneous test sessions
3. Monitor:
   - backend logs
   - worker logs
   - GPU memory
   - Redis queue depth
   - MinIO storage growth
4. Collect failures and tune limits

## Security Boundaries

Never expose these publicly:

- `8100`
- `8188`
- `5432`
- `6379`
- `9000`

Only expose:

- `80`
- `443`

Recommended controls:

- firewall allowlist for SSH
- Tailscale ACLs or equivalent
- rotated API keys
- TLS at nginx
- service restart policies
- regular database and MinIO backups

## Preferred Service Ownership

### App Server

- public ingress
- API
- job orchestration
- data persistence
- WebSocket fanout

### GPU Server

- model hosting
- heavy inference execution
- no public tester traffic

## Production Risks To Address

1. `ComfyUI` custom node import failures should be reviewed before heavy production use.
2. Remote service startup should move from ad hoc sessions to managed services.
3. Public auth should not rely on development API keys.
4. Current docs contain stale notes about disk and service names; deployment should follow live server state.
5. Backup and restore procedures for `postgres` and `minio` must be defined before external testing expands.

## Verification Checklist

### Private Infrastructure

- [ ] app server can resolve and reach GPU server private address
- [ ] `curl http://gpu-private-ip:8100/health` returns `200`
- [ ] `curl http://gpu-private-ip:8188/system_stats` returns `200`
- [ ] backend and workers use private endpoints, not localhost tunnel endpoints

### Public App

- [ ] `https://app.syau.ai` loads
- [ ] login/auth works
- [ ] `wss://app.syau.ai/ws` connects
- [ ] project list loads

### End-to-End Workflow

- [ ] create project
- [ ] analyze script
- [ ] inspect generated scenes/shots
- [ ] run workflow
- [ ] see real-time progress
- [ ] final output stored and downloadable

### Multi-User Test

- [ ] 2 users can use the app at the same time
- [ ] 3+ jobs queue without deadlock
- [ ] GPU server remains stable under concurrent load

## Immediate Next Step

Implement Phase 1 and Phase 3 first:

1. turn remote `vLLM` and `ComfyUI` into persistent managed services
2. join app server and GPU server with Tailscale
3. repoint backend/worker env to the GPU server private address

That removes the laptop dependency and creates the cleanest base for production rollout.
