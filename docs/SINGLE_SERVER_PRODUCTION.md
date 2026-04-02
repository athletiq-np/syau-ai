# SYAU AI Single-Server Production

Last updated: 2026-04-02

## Goal

Run the full SYAU AI product on `202.51.2.50` using one server:

- Host services:
  - `vLLM` on `8100`
  - `ComfyUI` on `8188`
- Docker services:
  - `frontend`
  - `backend`
  - `nginx`
  - `postgres`
  - `redis`
  - `minio`
  - `worker-image`
  - `worker-video`
  - `worker-chat`
  - `worker-studio`

## How It Works

The app stack runs in Docker, while the GPU inference services stay on the host.

The backend and workers reach host inference services through:

```env
INFERENCE_API_BASE_URL=http://host.docker.internal:8100
COMFYUI_URL=http://host.docker.internal:8188
```

`docker-compose.yml` now includes:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

for the services that need host inference access.

## Deployment Files

- env template: `.env.single-server.example`
- main compose file: `docker-compose.yml`

## Deployment Steps

### 1. Prepare Production Env

On the server:

```bash
cp .env.single-server.example .env.production
cp .env.production .env
```

Edit values:

- database password
- MinIO keys
- production API keys or auth strategy
- public URL/domain values

### 2. Keep Host GPU Services Running

Verify:

```bash
curl http://127.0.0.1:8100/health
curl http://127.0.0.1:8188/system_stats
```

### 3. Start Docker App Stack

```bash
PYTHONNOUSERSITE=1 docker-compose up -d --build postgres redis minio backend frontend nginx worker-image worker-video worker-chat worker-studio
PYTHONNOUSERSITE=1 docker-compose ps
```

### 4. Verify Docker Can Reach Host Inference

```bash
PYTHONNOUSERSITE=1 docker-compose exec backend curl http://host.docker.internal:8100/health
PYTHONNOUSERSITE=1 docker-compose exec backend curl http://host.docker.internal:8188/system_stats
```

Also verify from a worker if needed:

```bash
PYTHONNOUSERSITE=1 docker-compose exec worker-studio curl http://host.docker.internal:8100/health
PYTHONNOUSERSITE=1 docker-compose exec worker-studio curl http://host.docker.internal:8188/system_stats
```

### 5. Verify Public App

Check:

- frontend loads
- API works
- WebSocket works
- project create/analyze/generate flow works

## Current Working Env Notes

These values were confirmed working on `202.51.2.50`:

```env
DATABASE_URL=postgresql://syau:syau@postgres:5432/syau
INFERENCE_API_BASE_URL=http://host.docker.internal:8100
COMFYUI_URL=http://host.docker.internal:8188
```

## Docker Compose Caveat

The remote server currently uses old Python `docker-compose` v1, which is fragile.

Known working pattern:

```bash
PYTHONNOUSERSITE=1 docker-compose ps
PYTHONNOUSERSITE=1 docker-compose up -d backend frontend nginx worker-image worker-video worker-chat worker-studio
```

If `docker-compose` crashes with `KeyError: 'ContainerConfig'`, remove the stale exited containers shown by `docker ps -a` and run `up -d` again.

## Security

Expose publicly only:

- `80`
- `443`

Avoid public exposure for:

- `8100`
- `8188`
- `5432`
- `6379`
- `9000`

## Best Fit

This mode is best for:

- MVP
- beta access
- early multi-user testing
- fastest route to production on existing hardware

Move to split app-server / GPU-server architecture later if load or operational complexity grows.
