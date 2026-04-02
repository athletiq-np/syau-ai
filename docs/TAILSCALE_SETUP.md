# Tailscale Setup For SYAU AI Production

Last updated: 2026-04-02

## Goal

Create a private network between the app server and GPU server so the backend and workers can reach `vLLM` and `ComfyUI` without using a developer laptop or public inference ports.

## Target Layout

- App server
  - public: `80`, `443`
  - private: Docker services for app, workers, db, cache, object storage
- GPU server
  - private only: `8100`, `8188`
- Connectivity
  - Tailscale on both servers

## 1. Install Tailscale On App Server

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

## 2. Install Tailscale On GPU Server

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

## 3. Capture Private Addresses

On each server:

```bash
tailscale ip -4
tailscale status
```

Record the GPU server Tailscale IP or MagicDNS hostname.

Example:

- app server: `100.90.10.5`
- GPU server: `100.90.10.9`
- MagicDNS: `gpu-server.tailnet-name.ts.net`

## 4. Lock Down GPU Server Access

Do not expose `8100` or `8188` publicly.

Allow only:

- Tailscale/private network traffic from app server
- SSH from trusted admin IPs

If you use UFW:

```bash
sudo ufw allow 22/tcp
sudo ufw allow in on tailscale0
sudo ufw deny 8100/tcp
sudo ufw deny 8188/tcp
sudo ufw enable
```

Adjust SSH port/rules to match your real server policy.

## 5. Update App Server Environment

Set these in the production env file used by backend and workers:

```env
INFERENCE_MODE=remote
INFERENCE_API_BASE_URL=http://gpu-server.tailnet.ts.net:8100/v1
COMFYUI_URL=http://gpu-server.tailnet.ts.net:8188
```

If you use raw Tailscale IPs instead of MagicDNS:

```env
INFERENCE_API_BASE_URL=http://100.90.10.9:8100/v1
COMFYUI_URL=http://100.90.10.9:8188
```

Frontend public values should be:

```env
NEXT_PUBLIC_API_URL=https://app.syau.ai/api
NEXT_PUBLIC_WS_URL=wss://app.syau.ai/ws
```

## 6. Restart App Services

From the app server repo root:

```bash
docker compose --env-file .env.production up -d --build
docker compose restart backend worker-image worker-video worker-chat worker-studio frontend nginx
```

## 7. Verify Private Reachability

From the app server:

```bash
curl http://gpu-server.tailnet.ts.net:8100/health
curl http://gpu-server.tailnet.ts.net:8188/system_stats
```

From inside the backend container:

```bash
docker compose exec backend curl http://gpu-server.tailnet.ts.net:8100/health
docker compose exec backend curl http://gpu-server.tailnet.ts.net:8188/system_stats
```

## 8. Verify Product End-To-End

1. Load `https://app.syau.ai`
2. Create a project
3. Analyze a script
4. Run workflow
5. Watch progress through WebSocket updates
6. Confirm final output lands in MinIO and appears in the UI

## Notes

- Tailscale is preferred over public GPU ports.
- If you later move to VPC peering or WireGuard, only the private endpoint values need to change.
- Keep `vLLM` and `ComfyUI` private even in production.
