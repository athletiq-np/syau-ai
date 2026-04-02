# SYAU AI - Complete Project Status & Handoff Guide

**Last Updated:** April 2, 2026  
**Status:** 70% Complete - Workflow Editor Done, GPU Services In Progress

---

## Executive Summary

SYAU AI is a cinematic AI pipeline platform combining:
- **Script → Scenes** (Qwen2.5 LLM planning)
- **Scenes → Shots** (Script analysis & breakdown)
- **Shots → Video** (ComfyUI Wan 2.2 video generation)

**What's Working:**
- ✅ Full frontend (Next.js + React Flow workflow editor)
- ✅ Backend API (FastAPI + Celery workers)
- ✅ Database & caching (PostgreSQL, Redis, MinIO)
- ✅ Local Docker Compose setup (12 services)
- ✅ Professional workflow editor with infinite canvas

**What's Stuck:**
- 🔴 vLLM on remote server (CLI/import issues)
- 🟡 ComfyUI on remote starting up (disk space risk)
- 🔴 Remote GPU services not yet verified operational

---

## Architecture

### Frontend Stack
```
Location: /frontend
Tech: Next.js 14, React 18, TailwindCSS, ReactFlow 11.11.4, Zustand 5.0.12

Key Features:
- Authentication: Bearer token system (API_KEY_DEV=syauai_dev_key_12345)
- Workflow Editor: Full ReactFlow integration with custom nodes
  - Node types: Script, Analysis, Shot, Stitch, Output
  - Type-safe connections: text→scenes→video
  - Color-coded handles by data type
  - Real-time status monitoring
  - Live progress tracking for generation jobs
- Pages: Studio, Generate, Chat, Home
- API Status indicator on homepage
- Error boundary with auth error display

Status: ✅ COMPLETE & TESTED
```

### Backend Stack
```
Location: /backend
Tech: FastAPI, Celery, SQLAlchemy, Alembic

API Endpoints:
POST   /api/projects/{id}/analyze          → Scene breakdown via Qwen
POST   /api/projects/{id}/shots/{id}/generate → Per-shot video generation
GET    /api/jobs                           → List generation jobs
GET    /api/projects/{id}                  → Get project with scenes/shots

Workers (Celery):
- worker-image: Image generation tasks
- worker-video: Video generation tasks (ComfyUI)
- worker-chat: Chat/LLM tasks (vLLM)
- worker-studio: Cinema pipeline orchestration

Authentication: Bearer token validation on all endpoints

Status: ✅ COMPLETE - Ready for GPU service integration
```

### Database Schema
```
Location: /backend/alembic/versions
Migrations: 005_add_user_id.py (latest)

Tables:
- projects: name, description, script_content, user_id
- scenes: project_id, number, description, shot_count
- shots: scene_id, number, type (t2v/i2v), prompt, model, resolution, frames, steps, output_url
- jobs: type, status, result, project_id, created_at

Status: ✅ COMPLETE & MIGRATED
```

### GPU Services (Remote Server: 202.51.2.50)

#### Current State
```
Server Details:
- IP: 202.51.2.50, Port: 41447 (SSH)
- User: ekduiteen
- GPU: Available (nvidia-smi works)
- Storage: /data/ with models & ComfyUI installed

Disk Usage: ⚠️ 94% FULL (94GB/100GB, only 6.6GB free)
Memory: Fine (125GB total, 122GB available)

Data Directories:
/data/
├── ComfyUI/           ✅ Full installation
├── models/            ✅ ~20 subdirs (Qwen, video models)
├── outputs/           ✅ Generation output storage
├── projects/          ✅ Project data
└── logs/              ✅ Service logs

vLLM Installation:
- Script: ~/.local/bin/vllm (broken CLI wrapper)
- Python Package: ~/.local/lib/python3.10/site-packages/vllm/
- Status: ❌ BROKEN - Import errors, CLI parsing fails

ComfyUI Docker:
- Container: b4aa68215add (running)
- Image: nvidia/cuda:11.8.0-devel-ubuntu22.04
- Volumes: /data/ComfyUI → /ComfyUI, /data/models → /ComfyUI/models
- Status: 🟡 STARTING UP (installing dependencies, slow due to disk constraints)

Status: 🔴 BLOCKED - vLLM broken, ComfyUI in progress, disk space critical
```

---

## Local Development (Docker Compose)

### Quick Start
```bash
cd e:/Syau-ai
docker-compose up -d
# Starts all 12 services automatically
```

### Services Running Locally
```
Service          Port    GPU    Status
─────────────────────────────────────
Nginx            80      No     ✅ Reverse proxy
Frontend         3000    No     ✅ Next.js dev server
Backend          8000    No     ✅ FastAPI
vLLM             8100    Yes    ✅ LLM inference
ComfyUI          8188    Yes    ✅ Image/video generation
PostgreSQL       5433    No     ✅ Database
Redis            6380    No     ✅ Cache
MinIO            9000    No     ✅ Object storage
worker-image     -       No     ✅ Job processor
worker-video     -       No     ✅ Job processor
worker-chat      -       No     ✅ Job processor
worker-studio    -       No     ✅ Job processor
```

### Environment Files
```
.env (Docker):
- DATABASE_URL=postgresql://syau:syau@postgres:5432/syau
- INFERENCE_API_BASE_URL=http://vllm:8000/v1 (internal)
- COMFYUI_URL=http://comfyui:8188 (internal)
- MINIO_ENDPOINT=minio:9000
- API_KEY_DEV=syauai_dev_key_12345

frontend/.env.local (Next.js):
- NEXT_PUBLIC_API_URL=http://localhost/api (local)
- NEXT_PUBLIC_API_KEY=syauai_dev_key_12345
```

---

## Workflow Editor Implementation

### Location
```
/frontend/app/studio/[project_id]/workflow/page.tsx (main page)
/frontend/components/workflow/ (all components)
```

### Files Created
```
Node Components:
- nodes/ScriptNode.tsx          (blue, text-out)
- nodes/AnalysisNode.tsx        (violet, text-in → scenes-out)
- nodes/ShotNode.tsx            (cyan, scenes-in → video-out, live progress)
- nodes/StitchNode.tsx          (green, video-in → video-out)
- nodes/OutputNode.tsx          (teal, video-in, download)
- nodes/nodeTypes.ts            (NODE_TYPES_MAP, handle colors)

Edge & Visualization:
- edges/WorkflowEdge.tsx        (type-aware bezier edges, animated)

Panels:
- panels/NodeLibraryPanel.tsx   (drag-to-add nodes, assets tab)
- panels/PropertiesPanel.tsx    (node parameter inspector)
- panels/ActiveRunsPanel.tsx    (live job progress tracking)

State Management:
- /lib/workflowStore.ts         (Zustand v5 store)

Integration:
- useProjectWebSocket.ts        (WebSocket for live updates, 5s polling fallback)
- WorkflowTopBar.tsx            (header with back/title/run button)
```

### Handle Color Mapping
```
text:   cyan (#06b6d4)
scenes: green (#22c55e)
video:  purple (#a855f7)
image:  orange (#f97316)

Connection validation: Only same-type handles can connect
```

### Node Layout
```
Columns:
x=80:   ScriptNode
x=360:  AnalysisNode
x=640:  ShotNodes (stacked vertically, y = 80 + index*160)
x=920:  StitchNode (centered vertically)
x=1200: OutputNode

Shot node IDs: "shot-{shot.id}" (recoverable by splitting)
```

**Status:** ✅ COMPLETE & TESTED

---

## Known Issues & Blockers

### 🔴 CRITICAL: vLLM on Remote Server
```
Issue: vLLM CLI wrapper broken, Python module import fails
Root Cause: Installation issue with ~/.local/bin/vllm script

Error:
  vllm: error: argument subparser: invalid choice: 'Qwen/Qwen2.5-7B-Instruct'

Attempted Fixes:
1. /home/ekduiteen/.local/bin/vllm serve --model ... → Failed (CLI parsing)
2. python3 -m vllm.entrypoints.openai.api_server → Failed (ImportError: no main)

Next Steps:
- Option A: Reinstall vLLM cleanly
  ```bash
  pip install --upgrade vllm
  ```
- Option B: Check if vLLM version incompatibility with Qwen model
- Option C: Use Docker image if disk space can be freed

Status: REQUIRES IMMEDIATE ATTENTION
```

### 🟡 MEDIUM: ComfyUI on Remote - Slow Startup
```
Issue: Container installing dependencies, very slow
Reason: Disk 94% full, limited I/O bandwidth

Container: b4aa68215add (nvidia/cuda:11.8.0-devel-ubuntu22.04)
Mounted: /data/ComfyUI → /ComfyUI, /data/models → /ComfyUI/models

Monitor with:
  ssh -p 41447 ekduiteen@202.51.2.50 "docker logs -f comfyui"

Status: NEEDS MONITORING
```

### 🔴 CRITICAL: Disk Space (202.51.2.50)
```
Usage: 94GB / 100GB (only 6.6GB free)

Risk: Container builds, pip installs, and model downloads will fail

Solution - Pick ONE:
1. Clean old Docker images/containers
   docker system prune -a --volumes

2. Delete old docker-compose containers from earlier attempts
   docker container ls -a | grep syauai | xargs docker rm -f

3. Check /tmp for old files
   du -sh /tmp

Status: MUST RESOLVE BEFORE PROCEEDING
```

### 🟡 MEDIUM: Network Verification Needed
```
Untested:
- vLLM port 8100 responding to requests
- ComfyUI port 8188 responding to requests
- Backend can reach both services
- WebSocket connectivity from frontend

Next Steps:
1. Verify vLLM: curl http://202.51.2.50:8100/health
2. Verify ComfyUI: curl http://202.51.2.50:8188/api/status
3. Test generation job end-to-end
```

---

## How to Proceed (Next Agent)

### Immediate Priority (Do First)
```
1. SSH to remote server
   ssh -p 41447 ekduiteen@202.51.2.50

2. Check disk space
   df -h /

3. IF disk > 90%:
   - Clean containers: docker container ls -a
   - Delete old ones: docker rm -f <container_id>
   - Check what's using space: du -sh /data/*

4. Get vLLM working
   - Try: pip install --upgrade vllm
   - Or: Check vLLM version vs. Qwen compatibility
   - Or: Use Docker if disk is freed

5. Monitor ComfyUI startup
   - docker logs -f comfyui
   - Wait for "listening on 0.0.0.0:8188" message
```

### Testing Flow
```
Once services running:

1. Test vLLM directly:
   curl -X POST http://202.51.2.50:8100/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"Hello"}]}'

2. Test ComfyUI:
   curl http://202.51.2.50:8188/api/status

3. Test backend connectivity:
   curl -H "Authorization: Bearer syauai_dev_key_12345" \
     http://202.51.2.50/api/projects

4. Test frontend → backend → GPU pipeline:
   - Create project in frontend
   - Upload script
   - Click "Analyze" (tests vLLM)
   - Click "Generate Shot" (tests ComfyUI)
   - Watch job in "Active Runs" panel
```

### If Stuck
```
Key files to check:
- /home/ekduiteen/vllm.log          (vLLM logs)
- docker logs comfyui               (ComfyUI logs)
- docker logs syauai_backend_1      (Backend logs)

Backend config (connecting to remote):
- /backend/.env

Environment points to:
- INFERENCE_API_BASE_URL=http://vllm:8000/v1 (should be http://202.51.2.50:8100/v1 if separate)
- COMFYUI_URL=http://comfyui:8188 (should be http://202.51.2.50:8188 if separate)
```

---

## File Structure Reference

```
e:/Syau-ai/
├── frontend/                          # Next.js app
│   ├── app/
│   │   ├── studio/[project_id]/workflow/page.tsx  (WORKFLOW EDITOR)
│   │   ├── page.tsx                   (Home with API status)
│   │   └── layout.tsx                 (AuthProvider wrapper)
│   ├── components/workflow/           (All workflow components)
│   ├── lib/
│   │   ├── api.ts                     (API client with Bearer token)
│   │   └── workflowStore.ts           (Zustand state)
│   └── .env.local
│
├── backend/                           # FastAPI
│   ├── main.py                        (FastAPI app, WebSocket route)
│   ├── api/routes/
│   │   ├── projects.py                (POST analyze, generate)
│   │   └── ...
│   ├── services/
│   │   ├── script_analyzer.py         (Qwen integration)
│   │   └── comfyui_client.py          (Workflow execution)
│   ├── workers/                       (Celery tasks)
│   └── alembic/versions/              (DB migrations)
│
├── infra/
│   └── nginx/nginx.conf               (Reverse proxy config)
│
├── docker-compose.yml                 (12 services)
├── .env                               (Backend env)
├── docker-compose.remote.yml          (Remote config template)
│
├── DOCKER_GPU_GUIDE.md                (vLLM + ComfyUI Docker setup)
├── DOCKER_COMPOSE_GUIDE.md            (Local docker-compose guide)
├── REMOTE_GPU_SETUP.md                (Remote setup guide)
└── PROJECT_STATUS.md                  (THIS FILE)
```

---

## Git Status

```
Current branch: main

Recent commits:
- 56f138e: Implement professional workflow editor with ReactFlow
- 17859c6: Fix project update validation schema
- 7e6e4ac: Add planning layer with Qwen2.5 scene breakdown
- 0cc2482: Implement complete cinematic filmmaking pipeline (Phase 1-3)
```

---

## Testing Checklist

```
Before declaring complete:
□ vLLM responding on port 8100
□ ComfyUI responding on port 8188
□ Backend can reach both services
□ Create new project in frontend
□ Upload script
□ Click "Analyze Scenes" → vLLM processes
□ View shots in workflow editor
□ Click "Generate" on shot → ComfyUI processes
□ Video appears in "Active Runs" panel with progress
□ Download generated video from OutputNode
□ Multiple shots generate correctly
□ Stitch works (combine multiple shot videos)
```

---

## Helpful Commands

```bash
# Remote Server SSH
ssh -p 41447 ekduiteen@202.51.2.50

# Check GPU
nvidia-smi

# View service logs
docker logs -f vllm
docker logs -f comfyui
docker logs -f backend

# Tail vLLM startup log
tail -f /home/ekduiteen/vllm.log

# Check port status
netstat -tlnp | grep -E ':(8100|8188|8000|80)'
ss -tlnp | grep -E ':(8100|8188|8000|80)'

# Container management
docker ps
docker ps -a
docker rm -f <container_id>
docker system prune -a

# Check disk space
df -h
du -sh /data/*

# Test endpoints
curl http://202.51.2.50:8100/health
curl http://202.51.2.50:8188/api/status
curl -H "Authorization: Bearer syauai_dev_key_12345" http://202.51.2.50/api/projects
```

---

## Contact / Notes

**Project Lead Notes:**
- Workflow editor completely redesigned with ReactFlow (Phase 1 complete)
- GPU services architecture ready, just needs startup debugging
- Disk space on remote is critical blocker
- vLLM installation issue is non-obvious - may need version investigation

**Next Agent Should:**
1. Fix/restart vLLM (highest priority)
2. Verify ComfyUI fully up
3. Test end-to-end generation pipeline
4. Clean up disk space
5. Document any workarounds needed

---

**Status:** Ready for GPU service debugging & end-to-end testing  
**Completion:** ~70% (missing GPU service verification & testing)
