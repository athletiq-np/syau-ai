# Docker GPU Setup - vLLM + ComfyUI

**Updated:** April 2, 2026  
**Status:** ✅ Ready to Deploy

---

## Everything in Docker Now

One command starts EVERYTHING (12 services):

```bash
docker-compose up -d
```

All services automatically:
- Build/pull images
- Start in correct order
- Connect to each other
- Run on GPU (if available)
- Restart on failure

---

## Services Running

| Service | Port | GPU | Purpose |
|---------|------|-----|---------|
| Nginx | 80 | No | Frontend + API proxy |
| Frontend | 3000 | No | Next.js dev server |
| Backend | 8000 | No | FastAPI + Orchestration |
| **vLLM** | **8100** | **Yes** | LLM inference (Qwen) |
| **ComfyUI** | **8188** | **Yes** | Image/Video generation |
| PostgreSQL | 5433 | No | Database |
| Redis | 6380 | No | Cache/Queue |
| MinIO | 9000 | No | Object storage |
| Worker-Image | - | No | Image job processor |
| Worker-Video | - | No | Video job processor |
| Worker-Chat | - | No | Chat job processor |
| Worker-Studio | - | No | Cinema pipeline processor |

---

## Quick Start

### Local Machine (with GPU)

```bash
# Ensure NVIDIA Docker runtime installed
docker run --rm --gpus all nvidia/cuda:11.8.0-base nvidia-smi

# Start full stack
cd /path/to/Syau-ai
docker-compose up -d

# Check status
docker-compose ps

# Watch logs
docker-compose logs -f
```

### Remote Server (202.51.2.50)

```bash
# SSH into server
ssh -p 41447 ekduiteen@202.51.2.50

# Clone repo (if not already there)
cd ~
git clone https://github.com/your-repo/syau-ai.git
cd syau-ai

# Start everything
docker-compose up -d

# Check GPU usage
nvidia-smi
docker-compose logs -f vllm
docker-compose logs -f comfyui
```

---

## Configuration

### GPU Memory Management

Edit `.env`:

```env
# For 8GB VRAM
VLLM_GPU_MEMORY_UTILIZATION=0.6
VLLM_MAX_MODEL_LEN=2048

# For 16GB+ VRAM
VLLM_GPU_MEMORY_UTILIZATION=0.8
VLLM_MAX_MODEL_LEN=4096

# For 24GB+ VRAM
VLLM_GPU_MEMORY_UTILIZATION=0.9
VLLM_MAX_MODEL_LEN=8192
```

### Model Selection

vLLM in `docker-compose.yml`:

```yaml
vllm:
  command:
    - --model
    - Qwen/Qwen2.5-7B-Instruct    # Fast (15GB)
    # or
    - Qwen/Qwen2.5-72B-Instruct   # Better (140GB)
```

ComfyUI models stored in:
- `.docker-data/comfyui-models/`

---

## Health Checks

All services have automatic health checks:

```bash
# vLLM health
curl http://localhost:8100/health

# ComfyUI health
curl http://localhost:8188/api/status

# Backend
curl -H "Authorization: Bearer syauai_dev_key_12345" \
  http://localhost/health
```

---

## Common Commands

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# Restart specific service
docker-compose restart vllm
docker-compose restart comfyui

# View logs
docker-compose logs -f vllm
docker-compose logs -f comfyui
docker-compose logs -f backend

# Execute command in container
docker-compose exec vllm bash
docker-compose exec comfyui bash

# Rebuild images
docker-compose build vllm comfyui

# Full reset (removes volumes)
docker-compose down -v
```

---

## Troubleshooting

### GPU Not Detected

Check NVIDIA Docker runtime:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base nvidia-smi
```

If fails, install:
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-docker2
sudo systemctl restart docker
```

### vLLM Out of Memory

Lower in `docker-compose.yml`:
```yaml
- --gpu-memory-utilization
- "0.6"
- --max-model-len
- "2048"
```

### ComfyUI Not Starting

Check logs:
```bash
docker-compose logs comfyui
```

First run downloads dependencies (~30GB). Be patient.

### Port Already in Use

Change in `docker-compose.yml`:
```yaml
ports:
  - "8100:8000"  # vLLM
  - "8188:8188"  # ComfyUI
  - "8000:8000"  # Backend
  - "80:80"      # Nginx
```

---

## Volume Management

Models and outputs stored locally:

```
.docker-data/
├── vllm-models/           # vLLM Hugging Face cache
├── comfyui-models/        # ComfyUI models (Wan, FLUX)
├── comfyui-outputs/       # ComfyUI generated images
├── postgres/              # Database
├── redis/                 # Cache
├── minio/                 # Object storage
├── models/                # Shared model directory
├── outputs/               # Job outputs
└── cache/                 # Cache directory
```

Pre-download models:
```bash
# vLLM (Qwen 7B = 15GB)
docker-compose exec vllm python -c \
  "from huggingface_hub import snapshot_download; \
   snapshot_download('Qwen/Qwen2.5-7B-Instruct')"

# ComfyUI models: Add manually to .docker-data/comfyui-models/
# Wan 2.2 for video
# FLUX Schnell for images
```

---

## End-to-End Test

1. **Start everything:**
   ```bash
   docker-compose up -d
   sleep 60  # Wait for startup
   ```

2. **Test vLLM:**
   ```bash
   curl -X POST http://localhost:8100/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"Hello"}]}'
   ```

3. **Test ComfyUI:**
   ```bash
   curl http://localhost:8188/api/status
   ```

4. **Test Backend:**
   ```bash
   curl -H "Authorization: Bearer syauai_dev_key_12345" \
     http://localhost/api/jobs
   ```

5. **Open Frontend:**
   - Browser: http://localhost
   - Try Image generation page
   - Watch job in History

6. **Monitor GPU:**
   ```bash
   docker stats
   # or on host
   nvidia-smi
   ```

---

## Performance Tuning

### vLLM

```yaml
vllm:
  command:
    - --model Qwen/Qwen2.5-7B-Instruct
    - --tensor-parallel-size 2          # Multi-GPU
    - --gpu-memory-utilization 0.8
    - --max-model-len 4096
    - --disable-log-stats               # Reduce logging
```

### ComfyUI

```yaml
comfyui:
  environment:
    CUDA_VISIBLE_DEVICES: "0"           # Single GPU
    # or "0,1" for multi-GPU
```

---

## Deployment on Remote Server

1. **Update backend .env for remote:**
   ```bash
   # Already uses service names (vllm, comfyui)
   # They work via internal Docker network
   ```

2. **Expose ports on remote:**
   ```bash
   # Update docker-compose.yml ports if needed
   ports:
     - "0.0.0.0:80:80"    # Nginx (public)
     - "0.0.0.0:8100:8100" # vLLM (optional public access)
     - "0.0.0.0:8188:8188" # ComfyUI (optional public access)
   ```

3. **Start on remote:**
   ```bash
   ssh -p 41447 ekduiteen@202.51.2.50
   cd ~/syau-ai
   docker-compose up -d
   ```

4. **Access from local:**
   ```bash
   # Frontend
   http://202.51.2.50

   # API
   http://202.51.2.50/api/jobs

   # vLLM (direct)
   http://202.51.2.50:8100/health

   # ComfyUI (direct)
   http://202.51.2.50:8188/api/status
   ```

---

## Monitoring

```bash
# Real-time stats
docker stats

# GPU usage
nvidia-smi

# Service health
docker-compose ps

# Logs per service
docker-compose logs backend
docker-compose logs vllm
docker-compose logs comfyui

# Follow all logs
docker-compose logs -f
```

---

## Cost of Delay (First Run)

First start takes time:
- vLLM pulls base image: ~5min
- vLLM downloads Qwen model: ~20min (15GB)
- ComfyUI sets up environment: ~10min
- ComfyUI downloads models: depends on what you add

**Total first run: ~30-40 minutes with good internet**

Subsequent starts: ~30 seconds

---

## What's New

✅ vLLM service (LLM inference)  
✅ ComfyUI service (Image/video generation)  
✅ Auto GPU detection  
✅ Health checks  
✅ Automatic startup order  
✅ Shared Docker network  
✅ Volume management  
✅ Single docker-compose up command  

---

**Everything runs in containers. One command. All automatic.** 🐳🚀
