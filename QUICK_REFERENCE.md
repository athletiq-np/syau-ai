# SYAU AI Architecture - Quick Reference

## The Complete Flow (Simplified)

```
USER
  ↓
FRONTEND (Next.js, :3000)
  ↓ [submit job]
NGINX GATEWAY (:80)
  ↓ [route to backend]
BACKEND API (FastAPI, :8000)
  ├─ [write to PostgreSQL]
  ├─ [dispatch to Redis/Celery]
  └─ [return immediately: 202 Accepted]
  ↓
REDIS TASK QUEUE (:6379)
  ├─ [job sits in queue]
  └─ [workers pull tasks]
  ↓
WORKER (Async Celery Task)
  ├─ [pick up task from queue]
  ├─ [submit workflow to GPU server]
  ├─ [wait for result (~50s)]
  ├─ [download output video]
  ├─ [upload to MinIO storage]
  ├─ [update PostgreSQL]
  └─ [publish progress to Redis pub/sub]
  ↓
REDIS PUB/SUB
  ↓ [real-time updates]
WEBSOCKET HANDLER (Backend)
  ↓ [forward to frontend]
FRONTEND (React WebSocket)
  ↓ [update UI in real-time]
USER SEES PROGRESS BAR
  ↓
MINISO STORAGE (:9000)
  ├─ [stores generated video MP4]
  ├─ [generates presigned URL]
  └─ [user can download]
USER SEES RESULT
  ↓
DOWNLOAD VIDEO ✅
```

---

## Why This Architecture?

### ✅ **Asynchronous is Better Because:**

1. **User doesn't wait**
   - Submit job → Immediate response
   - User sees "Job queued" message
   - Can close tab and check later

2. **Real-time feedback**
   - Progress bar (5% → 25% → 50% → 100%)
   - Status messages ("Submitting...", "Generating...", "Uploading...")
   - User knows it's working

3. **Can handle multiple jobs**
   - User 1: submits job
   - User 2: submits job (same time)
   - User 3: submits job (same time)
   - All process in parallel (if GPUs available)

4. **Survives backend restart**
   - Job = Worker process (independent)
   - Backend crashes = Job keeps running
   - User refreshes page → Sees completed job

5. **Scales horizontally**
   - Add Worker A (GPU 0) → 1 job at a time
   - Add Worker B (GPU 1) → 2 jobs at a time
   - Add Worker C (GPU 2) → 3 jobs at a time
   - No code changes, just add hardware

---

## Why NOT Other Approaches?

### ❌ **Synchronous Processing (Bad)**
```
Frontend → Backend → GPU (blocks 50 seconds) → Frontend

Problems:
- HTTP timeout after 30 seconds
- User sees blank screen
- Can't submit other jobs
- Bad for mobile (connection drops)
- Can't scale (need 10 backends for 10 jobs)
```

### ❌ **WebSocket Only (Fragile)**
```
Frontend ←→ Backend (persistent connection)

Problems:
- Mobile: Reconnection issues
- Proxy/Firewall: Idle timeout after 30 minutes
- Scaling: Need connection affinity (hard load balancing)
- Memory: Holds connection for entire 50 seconds
- User closes tab mid-job: Uncertain state
```

### ❌ **Message Queue Only (No Progress)**
```
Frontend → Backend → MQ → Worker → GPU → Storage

No real-time updates. User sees:
- "Generating..." (for 50 seconds, nothing changes)
- User thinks app is frozen
- Bad UX
```

### ❌ **Serverless (Expensive & Slow)**
```
AWS Lambda / Fargate

Problems:
- Cold start: 2-5 second delay (adds to total time)
- Cost: $0.20 per job = $6/month if 30 jobs
- Vendor lock-in: AWS-specific
- Harder to debug: CloudWatch only
- Not suitable for 50-second jobs (billed by minute)
```

---

## The Four Pillars of Our Design

### **Pillar 1: Async Job Queue**
- Decouples frontend from GPU processing
- Jobs persist in Redis (survives restart)
- Multiple workers can process in parallel

### **Pillar 2: Real-Time Progress**
- WebSocket pushes updates to frontend
- Uses Redis pub/sub (scalable)
- User sees live progress bar

### **Pillar 3: Durable Storage**
- PostgreSQL: Job records survive crashes
- MinIO: Generated files are safe
- Celery: Tasks are retried if failed

### **Pillar 4: Horizontal Scaling**
- Add workers = Add GPU capacity
- No code changes needed
- Linear performance improvement

---

## Performance Characteristics

| Metric | Value | Why |
|--------|-------|-----|
| Time to First Response | 100ms | API returns job_id immediately |
| Time to See Progress | 500ms | WebSocket connection established |
| Job Completion Time | ~50s | GPU inference time (fixed) |
| Max Concurrent Jobs | = Number of GPUs | 1 GPU = 1 job at a time |
| Frontend Scalability | Unlimited | API is stateless |
| Database Overhead | Minimal | 3 queries per job |
| Memory per Worker | ~200MB | One Python process + libraries |

---

## Deployment Architecture

```
┌─── DEVELOPMENT ─────────────────────────┐
│ docker-compose up                       │
│ - Frontend :3000                        │
│ - Backend :8000                         │
│ - PostgreSQL :5433                      │
│ - Redis :6380                           │
│ - MinIO :9000                           │
│ - 3 Workers (image, video, chat)        │
│ - Nginx :80                             │
│                                         │
│ GPU Server: SSH to 202.51.2.50:41447   │
│ ComfyUI runs separately on GPU box      │
└─────────────────────────────────────────┘

┌─── PRODUCTION (if scaled) ──────────────┐
│ Kubernetes Cluster                      │
│ - Frontend Pod(s)                       │
│ - Backend Pod(s) with Load Balancer     │
│ - Worker Pod(s) with GPU node affinity  │
│ - PostgreSQL Instance (managed/RDS)     │
│ - Redis Cluster (managed/ElastiCache)   │
│ - MinIO → Migrate to S3                 │
│ - GPU Server(s) on dedicated nodes      │
│                                         │
│ Add: CloudFlare, WAF, monitoring        │
└─────────────────────────────────────────┘
```

---

## What Makes This "Better"?

✅ **Clear separation** - Frontend doesn't know about GPU  
✅ **No blocking** - User gets immediate feedback  
✅ **Real-time updates** - Progress bar works  
✅ **Reliable** - Jobs survive failures  
✅ **Scalable** - Add workers, not backends  
✅ **Simple ops** - Docker Compose locally, K8s in production  
✅ **Debuggable** - Logs at every layer  
✅ **No vendor lock-in** - All open source  

---

## Key Files & Their Roles

```
FRONTEND
├─ components/video-form.tsx        → T2V/I2V UI
├─ lib/useJobSocket.tsx             → Real-time progress
└─ lib/api.ts                        → API client

BACKEND
├─ api/routes/jobs.py               → REST endpoints
├─ workers/video_worker.py          → Job handler
├─ inference/comfyui_client.py      → GPU communication
├─ services/job_service.py          → Business logic
└─ models/job.py                    → Data model

GPU SERVER
├─ ComfyUI main.py                  → Workflow engine
├─ custom_nodes/WanVideoWrapper/   → Custom nodes
└─ models/                          → Model files

INFRASTRUCTURE
├─ docker-compose.yml               → All services
├─ docker-compose.worker.yml        → GPU workers only
└─ infra/nginx/nginx.conf           → Routing
```

---

## Troubleshooting Guide

| Issue | Cause | Fix |
|-------|-------|-----|
| Videos don't display | `<img>` tag instead of `<video>` | Use `<video>` in job-card.tsx |
| Job stuck on "running" | Worker crashed | Check worker logs |
| WebSocket not updating | Frontend not connected | Check browser console |
| Jobs queued forever | No workers available | Start worker containers |
| GPU server not found | Wrong IP/port | Check COMFYUI_URL env var |
| Videos not uploading | MinIO not running | Check docker-compose |
| Presigned URLs expire | Link older than 1 hour | Regenerate from job detail |

---

## The Bottom Line

**We chose this architecture because:**

1. It's simple enough to understand (one person built it)
2. It's robust enough for production (handles failures)
3. It scales naturally (add workers = better performance)
4. It's future-proof (easy to migrate to Kubernetes)
5. It provides good UX (real-time progress, no blocking)

**Is there a better way?** 

Only if you:
- Have infinite budget (serverless with cold start doesn't matter)
- Have ops team (Kubernetes is complex but enterprise-grade)
- Have different requirements (e.g., offline batch processing)

**For a creative AI studio? This is optimal.** 🎯

---

**Created:** April 1, 2026  
**Status:** Production-ready for single GPU, single region  
**Next Evolution:** Kubernetes when scaling beyond 1 GPU  
