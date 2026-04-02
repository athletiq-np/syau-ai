# Remote GPU Server Setup (vLLM + ComfyUI)

**Server:** 202.51.2.50 (ekduiteen user, port 41447)  
**GPU Requirements:** NVIDIA GPU with CUDA support  
**Ports:** 8100 (vLLM), 8188 (ComfyUI)

---

## Architecture

```
Local Docker Stack          Remote GPU Server
┌──────────────┐           ┌──────────────────────┐
│ Backend API  │──────────→│ vLLM (port 8100)     │ (LLM inference)
│ (localhost)  │           │ ComfyUI (port 8188)  │ (Image/video gen)
└──────────────┘           └──────────────────────┘
                                    ▲
                        GPU (CUDA required)
```

---

## Prerequisites

SSH into remote server:
```bash
ssh -p 41447 ekduiteen@202.51.2.50
```

Check GPU:
```bash
nvidia-smi
```

Should show NVIDIA GPU with CUDA Compute Capability 7.0+

---

## 1. Install vLLM (LLM Inference Server)

vLLM serves language models for text generation (Qwen, etc.)

### Option A: Using Python Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv ~/venv-vllm
source ~/venv-vllm/bin/activate

# Install vLLM with CUDA
pip install vllm torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Download model (Qwen 2.5 7B - 15GB)
export HF_HOME=~/models
python -c "from vllm import LLM; llm = LLM(model='Qwen/Qwen2.5-7B-Instruct', gpu_memory_utilization=0.8)"
```

### Option B: Using Docker

```bash
docker run --gpus all --rm \
  -p 8100:8000 \
  -v ~/models:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-7B-Instruct \
  --gpu-memory-utilization 0.8
```

### Start vLLM Service

After installation, start with:

```bash
# Create start script
cat > ~/start-vllm.sh << 'EOF'
#!/bin/bash
source ~/venv-vllm/bin/activate
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8100 \
  --gpu-memory-utilization 0.8 \
  --tensor-parallel-size 1
EOF

chmod +x ~/start-vllm.sh
nohup ~/start-vllm.sh > ~/vllm.log 2>&1 &
```

### Test vLLM

```bash
curl -X POST http://localhost:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }' \
  -H "Authorization: Bearer syauai_9fK2mQ7xL1pR8vN4zT6bW3cD5hJ0sA"
```

---

## 2. Install ComfyUI (Image/Video Generation)

ComfyUI runs the visual generation models (Wan 2.2 for video, FLUX for images).

### Setup ComfyUI

```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git ~/ComfyUI
cd ~/ComfyUI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Download models (for first run)
# Models go into: ~/ComfyUI/models/
mkdir -p models/{checkpoints,loras,embeddings}
```

### Install Custom Nodes (Optional but Recommended)

```bash
cd ~/ComfyUI/custom_nodes

# Wan Video Model
git clone https://github.com/example/wan-2.2-nodes.git

# FLUX Image Model
git clone https://github.com/example/flux-nodes.git

# Manager (simplifies node installation)
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
```

### Start ComfyUI Service

```bash
cat > ~/start-comfyui.sh << 'EOF'
#!/bin/bash
cd ~/ComfyUI
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188 --gpu-device 0
EOF

chmod +x ~/start-comfyui.sh
nohup ~/start-comfyui.sh > ~/comfyui.log 2>&1 &
```

### Test ComfyUI

```bash
curl http://localhost:8188/api/status
```

Should return JSON with system status.

---

## 3. Configure Backend to Use Remote Services

On remote server, update the deployed backend .env:

```bash
ssh -p 41447 ekduiteen@202.51.2.50 << 'EOF'
cat > /home/ekduiteen/SYAUAI/.env.remote << 'ENVEOF'
# Database
DATABASE_URL=postgresql://syau:syau@localhost:5432/syau
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_PUBLIC_ENDPOINT=http://202.51.2.50:9000
MINIO_ACCESS_KEY=changeme
MINIO_SECRET_KEY=changeme_also

# ComfyUI (Video generation)
COMFYUI_URL=http://localhost:8188

# vLLM (LLM inference)
INFERENCE_MODE=remote
INFERENCE_API_BASE_URL=http://localhost:8100/v1
INFERENCE_API_KEY=syauai_9fK2mQ7xL1pR8vN4zT6bW3cD5hJ0sA

# Other settings
LOG_LEVEL=INFO
ENVIRONMENT=production
MODELS_DIR=/data/models
ENVEOF
EOF
```

Restart backend with new config:
```bash
ssh -p 41447 ekduiteen@202.51.2.50 "docker restart syauai_backend_1"
```

---

## 4. Systemd Services (Auto-restart on Boot)

### vLLM Service

```bash
sudo tee /etc/systemd/system/vllm.service << 'EOF'
[Unit]
Description=vLLM OpenAI API Server
After=network.target

[Service]
Type=simple
User=ekduiteen
WorkingDirectory=/home/ekduiteen
ExecStart=/home/ekduiteen/start-vllm.sh
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vllm
sudo systemctl start vllm
```

### ComfyUI Service

```bash
sudo tee /etc/systemd/system/comfyui.service << 'EOF'
[Unit]
Description=ComfyUI Image/Video Generation Server
After=network.target

[Service]
Type=simple
User=ekduiteen
WorkingDirectory=/home/ekduiteen
ExecStart=/home/ekduiteen/start-comfyui.sh
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable comfyui
sudo systemctl start comfyui
```

Check status:
```bash
sudo systemctl status vllm
sudo systemctl status comfyui
```

---

## 5. Monitor Services

### View Logs

```bash
# vLLM logs
tail -f ~/vllm.log

# ComfyUI logs
tail -f ~/comfyui.log

# Or systemd logs
sudo journalctl -u vllm -f
sudo journalctl -u comfyui -f
```

### Check Health

```bash
# vLLM
curl http://localhost:8100/health

# ComfyUI
curl http://localhost:8188/api/status

# Backend connection test
curl -H "Authorization: Bearer syauai_dev_key_12345" \
  http://202.51.2.50:8000/health
```

---

## 6. GPU Memory Management

### Monitor GPU Usage
```bash
# Watch GPU in real-time
watch -n 1 nvidia-smi

# One-time check
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader
```

### Tune Memory Usage

**vLLM:**
```bash
# In start-vllm.sh, adjust:
--gpu-memory-utilization 0.7    # Lower = more stable, higher = faster
```

**ComfyUI:**
```bash
# In start-comfyui.sh, add:
--normalvram                     # Conservative memory usage
# or
--highvram                       # Aggressive (needs lots of VRAM)
```

---

## 7. Download Models

Models are large (10-50GB each). Download on remote server:

### vLLM Models

```bash
cd ~/models
# Qwen 2.5 7B (15GB) - recommended for balance
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-7B-Instruct')"

# Or Qwen 2.5 72B (140GB) - for better quality
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-72B-Instruct')"
```

### ComfyUI Models

```bash
cd ~/ComfyUI/models/checkpoints

# Wan 2.2 (Video generation) - 20GB
# Download manually or use ComfyUI manager

# FLUX Schnell (Fast image gen) - 15GB
# Download manually or use ComfyUI manager
```

---

## 8. Network Configuration

### Allow Remote Access

If accessing from different machine:

```bash
# vLLM: Update start script
python -m vllm.entrypoints.openai.api_server \
  --host 0.0.0.0 \          # Listen on all interfaces
  --port 8100

# ComfyUI: Already does this
python main.py --listen 0.0.0.0 --port 8188
```

### Firewall (if enabled)

```bash
sudo ufw allow 8100/tcp
sudo ufw allow 8188/tcp
sudo systemctl reload ufw
```

---

## 9. Troubleshooting

### vLLM Won't Start
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Check VRAM
nvidia-smi

# View detailed logs
tail -100 ~/vllm.log
```

### ComfyUI Port in Use
```bash
# Find process using port 8188
lsof -i :8188

# Kill it
kill -9 <PID>
```

### Backend Can't Connect to Services
```bash
# From backend container, test connectivity
docker exec syauai_backend_1 curl http://localhost:8100/health
docker exec syauai_backend_1 curl http://localhost:8188/api/status

# If fails, check network
docker network ls
docker network inspect syauai-network
```

### Out of Memory
```bash
# Reduce batch size
# Lower gpu-memory-utilization
# Use smaller models
# Kill other GPU processes
```

---

## Quick Start Commands

All-in-one for a fresh remote server:

```bash
# SSH into remote server
ssh -p 41447 ekduiteen@202.51.2.50

# 1. Install vLLM
python3 -m venv ~/venv-vllm
source ~/venv-vllm/bin/activate
pip install vllm torch --index-url https://download.pytorch.org/whl/cu118
cat > ~/start-vllm.sh << 'EOF'
#!/bin/bash
source ~/venv-vllm/bin/activate
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8100 \
  --gpu-memory-utilization 0.8
EOF
chmod +x ~/start-vllm.sh
nohup ~/start-vllm.sh > ~/vllm.log 2>&1 &

# 2. Install ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git ~/ComfyUI
cd ~/ComfyUI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cu118
cat > ~/start-comfyui.sh << 'EOF'
#!/bin/bash
cd ~/ComfyUI
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188
EOF
chmod +x ~/start-comfyui.sh
nohup ~/start-comfyui.sh > ~/comfyui.log 2>&1 &

# 3. Verify both are running
sleep 30
curl http://localhost:8100/health
curl http://localhost:8188/api/status

# ✓ Done!
```

---

## Next Steps

Once vLLM and ComfyUI are running:

1. Test end-to-end: Create a job via frontend
2. Watch progress: `docker logs -f syauai_backend_1`
3. Monitor GPU: `nvidia-smi`
4. View outputs: MinIO at http://202.51.2.50:9001

---

**GPU acceleration ready!** 🚀
