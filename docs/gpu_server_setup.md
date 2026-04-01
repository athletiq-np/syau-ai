# GPU Server Setup

This guide assumes:

- your GPU server is `202.51.2.50`
- SSH port is `41447`
- models already exist under `/data/models`
- you are new to Linux/server setup

## What we are setting up

We are creating a **private inference API** on the GPU server.

Your main SYAUAI app will call this server over HTTP instead of trying to load models locally.

## Folder layout on the GPU server

We will use:

```text
/opt/syauai/gpu_server
```

## Step 1: SSH into the GPU server

From your local terminal:

```bash
ssh -p 41447 root@202.51.2.50
```

If `root` does not work, use your actual Linux username.

## Step 2: Install basic system packages

On the GPU server:

```bash
apt update
apt install -y python3 python3-pip python3-venv git
```

## Step 3: Create the app folder

```bash
mkdir -p /opt/syauai/gpu_server
```

## Step 4: Copy the repo files from your local machine

From your local machine, inside this repo:

```bash
bash ./infra/scripts/deploy-gpu-api.sh
```

If Git Bash is not available on Windows, run the same logic manually with `scp` or `rsync`.

## Step 5: Create the GPU API env file

On the GPU server:

```bash
cd /opt/syauai/gpu_server
cp .env.example .env
```

Then edit it:

```bash
nano /opt/syauai/gpu_server/.env
```

Recommended starting values:

```env
HOST=0.0.0.0
PORT=8100
API_KEY=replace-this-with-a-long-random-secret
MODELS_DIR=/data/models
INFERENCE_MODE=real
CHAT_MAX_NEW_TOKENS=512
CHAT_TEMPERATURE=0.7
```

## Step 6: Create a Python virtual environment

On the GPU server:

```bash
cd /opt/syauai/gpu_server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 7: Start the GPU API manually for the first test

```bash
cd /opt/syauai
source /opt/syauai/gpu_server/.venv/bin/activate
set -a
source /opt/syauai/gpu_server/.env
set +a
python3 -m uvicorn gpu_server.app:app --host 0.0.0.0 --port 8100
```

If `source .env` fails because of shell formatting, use manual exports instead:

```bash
cd /opt/syauai
source /opt/syauai/gpu_server/.venv/bin/activate
export HOST=0.0.0.0
export PORT=8100
export API_KEY=replace-this-with-a-long-random-secret
export MODELS_DIR=/data/models
export INFERENCE_MODE=real
python3 -m uvicorn gpu_server.app:app --host 0.0.0.0 --port 8100
```

If that succeeds, leave it running and open another terminal.

## Step 8: Test the health endpoint

From your local machine:

```bash
curl http://202.51.2.50:8100/health
```

Expected response:

```json
{"status":"ok","mode":"real"}
```

## Step 9: Test authenticated model listing

Replace `YOUR_API_KEY` with the value from `.env`:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://202.51.2.50:8100/models
```

## Step 10: Wire the main app to use the GPU API

In your main SYAUAI app `.env`, set:

```env
INFERENCE_MODE=remote
INFERENCE_API_BASE_URL=http://202.51.2.50:8100
INFERENCE_API_KEY=YOUR_API_KEY
INFERENCE_TIMEOUT_SECONDS=180
```

Then restart:

```bash
docker compose restart backend worker-image worker-video worker-chat
```

## Step 11: What is real vs mock right now

- Image remote path: ready for real server-backed inference
- Chat remote path: ready for real server-backed inference
- Video remote path: API contract is ready, but server still returns a mock GIF until the real video model loader is implemented

## Step 12: Production advice

Once manual startup works, the next step is:

- run the GPU API behind `systemd`
- optionally put nginx in front of it
- restrict access so only your VPS/app server can call it

## Step 13: Make the GPU API start automatically on Ubuntu

Copy the service file from this repo to the server:

```bash
sudo cp /opt/syauai/infra/gpu-server/syau-gpu-api.service /etc/systemd/system/syau-gpu-api.service
```

If the `User=` line in the file is wrong, edit it first:

```bash
sudo nano /etc/systemd/system/syau-gpu-api.service
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable syau-gpu-api
sudo systemctl start syau-gpu-api
sudo systemctl status syau-gpu-api
```

To see logs later:

```bash
journalctl -u syau-gpu-api -f
```

## Step 14: Make the SSH tunnel easier on Windows

From your local repo you can use:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\scripts\start-gpu-tunnel.ps1
```

Keep that PowerShell window open while testing locally.

What this does:

- local `127.0.0.1:8100`
- forwards to server `127.0.0.1:8100`

So your Docker containers can keep using:

```env
INFERENCE_API_BASE_URL=http://host.docker.internal:8100
```

## Common beginner problems

### `ModuleNotFoundError`

Make sure you are inside:

```bash
cd /opt/syauai
source /opt/syauai/gpu_server/.venv/bin/activate
```

### `CUDA out of memory`

This is expected if the wrong model/device settings are used. The image loader already expects:

- `DiffusionPipeline.from_pretrained(...)`
- `device_map="balanced"`

### `Connection refused`

Usually means:

- `uvicorn` is not running
- firewall is blocking port `8100`
- wrong IP/port in `INFERENCE_API_BASE_URL`

## Recommended next step

After you get `/health` and `/models` working, tell me exactly what happened and I’ll guide you through the first real `/infer/chat` or `/infer/image` test.
