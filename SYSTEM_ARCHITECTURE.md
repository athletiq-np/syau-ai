# SYAU AI - Complete System Architecture

## 1. System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER LAYER (Browser)                              │
│                                                                              │
│  Frontend (Next.js + React)  ───────────────────────────────────────────── │
│  ├─ Image Generation Page                                                  │
│  ├─ Video Generation Page (T2V + I2V)                                      │
│  ├─ Chat Interface                                                         │
│  ├─ Job History & Gallery                                                 │
│  └─ Real-time Progress via WebSocket                                       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               │ HTTP/WebSocket
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                        GATEWAY LAYER (Nginx)                                │
│                                                                              │
│  Reverse Proxy (localhost:80)                                              │
│  ├─ Route /api → Backend :8000                                             │
│  ├─ Route /ws → WebSocket :8000                                            │
│  ├─ Route /* → Frontend :3000                                              │
│  └─ SSL/TLS termination (optional)                                         │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        
┌─────────────────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI Backend :8000)                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ REST Endpoints                                                      │   │
│  ├─ POST /api/jobs              (Submit image/video/chat job)         │   │
│  ├─ GET  /api/jobs              (List jobs with filters)              │   │
│  ├─ GET  /api/jobs/{id}         (Get single job status)               │   │
│  ├─ GET  /api/models            (List available models)               │   │
│  ├─ GET  /health                (Health check)                        │   │
│  └─ DELETE /api/jobs/{id}       (Cancel job)                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WebSocket Handler (/ws)                                             │   │
│  ├─ Real-time job progress updates                                    │   │
│  ├─ Status: pending → running → done/failed                           │   │
│  ├─ Progress: 0-100%                                                  │   │
│  └─ Messages: "Submitting...", "Generating...", "Uploading..."        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Services                                                            │   │
│  ├─ JobService (CRUD operations)                                      │   │
│  ├─ AuthService (JWT tokens - optional)                               │   │
│  ├─ ModelService (Model registry)                                     │   │
│  └─ StorageService (MinIO integration)                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   PostgreSQL DB      │  │   Redis Cache        │  │    MinIO Storage     │
│   :5432              │  │   :6379              │  │    :9000             │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ ┌────────────────┐   │  │ ┌────────────────┐   │  │ ┌────────────────┐   │
│ │ jobs table     │   │  │ │ job:tasks      │   │  │ │ syau-outputs   │   │
│ │ models table   │   │  │ │ cache          │   │  │ │ bucket         │   │
│ │ users table    │   │  │ │ rate limiting  │   │  │ │ (generated     │   │
│ │ (optional)     │   │  │ │ pub/sub        │   │  │ │  files)        │   │
│ └────────────────┘   │  │ └────────────────┘   │  │ └────────────────┘   │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
        ▲                          │                        ▲
        │                          │                        │
        └──────────────┬───────────┴────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   Job Dispatch System       │
        │   (in FastAPI startup)      │
        │                             │
        │  When job created:          │
        │  1. Write to PostgreSQL     │
        │  2. Publish to Redis        │
        │  3. Dispatch Celery task    │
        └──────────────┬──────────────┘
                       │
                       ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│              TASK QUEUE LAYER (Celery + Redis)                              │
│                                                                              │
│  Task Queues:                                                               │
│  ├─ image    → Worker processes image generation jobs                       │
│  ├─ video    → Worker processes video generation jobs                       │
│  └─ chat     → Worker processes chat/LLM jobs                              │
│                                                                              │
│  Task Flow:                                                                 │
│  1. API creates Job in DB                                                  │
│  2. API enqueues Celery task                                               │
│  3. Worker picks up task (when available)                                  │
│  4. Worker processes job (GPU-heavy operations)                            │
│  5. Worker publishes progress via Redis pub/sub                            │
│  6. Worker uploads output to MinIO                                         │
│  7. Worker updates job status in DB                                        │
│  8. API/WebSocket notifies frontend                                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼

┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│  Image Worker      │ │  Video Worker      │ │  Chat Worker       │
│  (Qwen)            │ │  (Wan 2.2)         │ │  (Qwen LLM)        │
├────────────────────┤ ├────────────────────┤ ├────────────────────┤
│ ┌────────────────┐ │ │ ┌────────────────┐ │ │ ┌────────────────┐ │
│ │ run_image_job  │ │ │ │ run_video_job  │ │ │ │ run_chat_job   │ │
│ │ (in container) │ │ │ │ (in container) │ │ │ │ (in container) │ │
│ │ ┌────────────┐ │ │ │ ┌────────────┐ │ │ │ ┌────────────┐   │ │
│ │ │ Handler:   │ │ │ │ │ Handler:   │ │ │ │ │ Handler:   │   │ │
│ │ │ Qwen       │ │ │ │ │ ComfyUI    │ │ │ │ │ Ollama/    │   │ │
│ │ │ Image Gen  │ │ │ │ │ Client     │ │ │ │ │ Local LLM  │   │ │
│ │ └────────────┘ │ │ │ └────────────┘ │ │ │ └────────────┘   │ │
│ └────────────────┘ │ │ └────────────────┘ │ │ └────────────────┘ │
└────────────────────┘ └────────────────────┘ └────────────────────┘
        ▼                       ▼                       ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│              GPU SERVER (Remote - 202.51.2.50:41447)                        │
│                                                                              │
│  ComfyUI Server                                                             │
│  ├─ HTTP API :8188                                                          │
│  ├─ Prompt submission endpoint                                              │
│  ├─ History polling endpoint                                                │
│  └─ Output file serving endpoint                                            │
│                                                                              │
│  Models (Downloaded in /data/models/):                                      │
│  ├─ Wan 2.2 14B T2V Model                                                   │
│  ├─ Wan 2.2 14B I2V Model                                                   │
│  ├─ LightX2V 4-step LoRAs (high_noise + low_noise)                          │
│  ├─ UMT5-XXL Text Encoder (with blocks.* → encoder.block.* conversion)     │
│  ├─ Wan 2.1 VAE (joint T2V/I2V)                                            │
│  └─ Support nodes (CLIP, VAE, Sampler, Video encoder/decoder)              │
│                                                                              │
│  Workflows:                                                                 │
│  ├─ T2V: CLIPLoader → TextEncode → DualUNet+LoRA → KSampler (2-stage)      │
│  └─ I2V: LoadImage → WanImageToVideo → DualUNet+LoRA → KSampler (2-stage)  │
│                                                                              │
│  Processing:                                                                │
│  1. Worker sends JSON workflow to /prompt                                   │
│  2. ComfyUI queues workflow & returns prompt_id                            │
│  3. Worker polls /history/{prompt_id} until "outputs" appear               │
│  4. Worker downloads video from /view endpoint                             │
│  5. Worker uploads to MinIO                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Request-Response Flow

### **Scenario: User Generates T2V Video**

```
TIME  COMPONENT              ACTION                                    STATE
──────────────────────────────────────────────────────────────────────────────

T+0s  User (Browser)         Click "Generate Video" button
      ↓
      VideoForm (React)       Validates form (prompt, params)
      ↓
      API Client (JS)         POST /api/jobs with:
                              {
                                "type": "video",
                                "model": "wan-2.2",
                                "prompt": "a cat playing",
                                "params": {
                                  "num_frames": 81,
                                  "width": 640,
                                  "height": 640
                                }
                              }
      ↓
T+0.1s Backend (FastAPI)    Create Job record:
                              id=abc123, status="pending"
                              Save to PostgreSQL
      ↓
      JobService             Dispatch Celery task:
                              run_video_job.apply_async(
                                args=[job_id],
                                queue="video"
                              )
      ↓
T+0.2s Redis Broker         Task enqueued to "video" queue

      ┌──────────────────────────────────────────────────────────┐
      │ API RESPONSE to Frontend (202 Accepted):                │
      │ {                                                         │
      │   "job_id": "abc123",                                    │
      │   "status": "pending"                                    │
      │ }                                                         │
      └──────────────────────────────────────────────────────────┘
      
      Frontend receives response, sets activeJobId
      ↓
T+0.3s Frontend             Connect WebSocket: ws://localhost/ws
                            Subscribe to job updates

T+0.5s Video Worker         Pulls task from Redis "video" queue
                            status → "running"
                            Publish to Redis pub/sub: "job:abc123"
      ↓
      WebSocket Handler      Receives Redis message
                            Sends to connected browser:
                            {
                              "job_id": "abc123",
                              "status": "running",
                              "progress": 5,
                              "message": "Submitting to ComfyUI..."
                            }
      ↓
      Browser UI            Update spinner + progress message
                            "Submitting to ComfyUI... 5%"

T+1s  Video Worker         Create T2V workflow JSON
      ↓
      HTTP Client           POST http://gpu-server:8188/prompt
                            {
                              "prompt": {
                                "1": {"inputs": {...}, "class_type": "CLIPLoader"},
                                "2": {"inputs": {...}, "class_type": "CLIPTextEncode"},
                                ...
                                "16": {..., "class_type": "SaveVideo"}
                              }
                            }
      ↓
T+1.1s GPU Server         Queue workflow
      ComfyUI              Return: {"prompt_id": "xyz789"}

T+1.2s Video Worker       Start polling loop:
                          GET /history/xyz789
      ↓
      ComfyUI              Return: {} (not started)
                          Publish progress: 10%

T+5s  ComfyUI             Load UMT5-XXL text encoder
                          Convert blocks.* → encoder.block.* keys
                          Encode prompt: "a cat playing"
      ↓
      Progress             15%

T+15s ComfyUI             Load dual UNets + LoRAs
                          Stage 1: KSampler (steps 0→2)
      ↓
      Progress             25%

T+30s ComfyUI             Stage 2: KSampler (steps 2→4)
                          Decode latents to images
      ↓
      Progress             60%

T+45s ComfyUI             Encode frames to MP4 video
                          Save to /data/ComfyUI/output/video/
      ↓
      Progress             80%

T+50s ComfyUI             POST /history/xyz789
                          Return:
                          {
                            "xyz789": {
                              "outputs": {
                                "16": {
                                  "images": [{
                                    "filename": "video_00001_.mp4",
                                    "subfolder": "video",
                                    "type": "output"
                                  }]
                                }
                              }
                            }
                          }

T+50.1s Video Worker     Detect "images" key + .mp4 extension
                         Download video via:
                         GET /view?filename=video_00001_.mp4&subfolder=video
      ↓
T+50.2s GPU Server       Stream MP4 bytes

T+50.3s Video Worker     Receive video bytes (949 KB)
                         Create MinIO presigned PUT URL
      ↓
T+50.4s MinIO            Upload: PUT /syau-outputs/outputs/abc123_0.mp4
                         Store in bucket

T+50.5s Video Worker     Update job in PostgreSQL:
                         status="done"
                         output_keys=["outputs/abc123_0.mp4"]
                         duration_seconds=50.3
      ↓
T+50.6s Publish           Redis pub/sub: "job:abc123"
                         {
                           "job_id": "abc123",
                           "status": "done",
                           "progress": 100,
                           "message": "Complete"
                         }

T+50.7s WebSocket        Send to browser:
                         {
                           "job_id": "abc123",
                           "status": "done",
                           "progress": 100
                         }

T+50.8s Browser          Update UI:
                         - Hide spinner
                         - Fetch full job via GET /api/jobs/abc123
                         - Receive output_urls (presigned MinIO links)
                         - Display video in <video> tag
                         - Show download button

T+51s  User              Sees generated MP4 video playing
                         Can download, reuse prompt, or generate new video
```

---

## 3. Architecture Components Explained

### **A. Frontend (Next.js + React)**

**Why this choice:**
- ✅ Server-side rendering (SSR) for fast initial page load
- ✅ TypeScript for type safety
- ✅ Built-in image optimization
- ✅ File-based routing (clean structure)
- ✅ Native WebSocket support
- ✅ Hot module reloading for development

**Responsibilities:**
- Form submission (image, video, chat prompts)
- Real-time progress tracking via WebSocket
- Job history and filtering
- Video/image display with preview

**Why NOT:**
- Vue/Svelte: Smaller ecosystems, fewer component libraries
- Plain HTML: No real-time updates, bad UX

---

### **B. Reverse Proxy (Nginx)**

**Why this choice:**
- ✅ Single entry point (localhost:80)
- ✅ Route separation (API vs Frontend)
- ✅ WebSocket upgrade handling
- ✅ Load balancing (if scaled)
- ✅ Low overhead (native C)

**Configuration:**
```nginx
location /api { proxy_pass http://backend:8000; }
location /ws { proxy_pass http://backend:8000; upgrade=websocket; }
location / { proxy_pass http://frontend:3000; }
```

**Why NOT:**
- HAProxy: More complex for single entry point
- No proxy: Frontend/Backend on different ports (bad UX)

---

### **C. FastAPI Backend**

**Why this choice:**
- ✅ Async/await for concurrent requests
- ✅ Built-in WebSocket support
- ✅ Automatic API documentation (Swagger)
- ✅ Pydantic validation
- ✅ Fast execution (near-C speed)
- ✅ Native Redis/Celery integration

**Responsibilities:**
- REST API endpoints (job CRUD)
- WebSocket server (progress updates)
- Job orchestration (dispatch to Celery)
- Service layer logic
- Database queries

**Why NOT:**
- Django: Overkill, slower, sync-by-default
- Flask: No built-in async, less structured
- Node.js: Python ecosystem better for ML/AI

---

### **D. PostgreSQL Database**

**Why this choice:**
- ✅ ACID transactions (job state consistency)
- ✅ JSON fields (flexible params storage)
- ✅ Full-text search (job history filtering)
- ✅ Native UUID support (job IDs)
- ✅ Mature, production-tested

**Data Model:**
```sql
jobs
├─ id (UUID, PK)
├─ type (image|video|chat)
├─ model (string)
├─ prompt (text)
├─ negative_prompt (text)
├─ params (JSON: {width, height, seed, num_frames, ...})
├─ status (pending|running|done|failed)
├─ celery_task_id (string)
├─ output_keys (JSON array: ["outputs/abc123_0.mp4"])
├─ output_urls (JSON array: ["http://minio:9000/..."])
├─ error (text)
├─ duration_seconds (float)
├─ created_at (timestamp)
├─ started_at (timestamp)
└─ completed_at (timestamp)

models
├─ id (UUID, PK)
├─ name (string: "wan-2.2")
├─ display_name (string: "WAN 2.2 (Primary)")
├─ type (video|image|chat)
├─ is_enabled (boolean)
└─ metadata (JSON: {max_width, max_height, ...})
```

**Why NOT:**
- MongoDB: No ACID, harder to query job history
- SQLite: Not concurrent-safe, single file
- MySQL: PostgreSQL more reliable for this use case

---

### **E. Redis Cache & Message Broker**

**Why this choice:**
- ✅ In-memory (fast pub/sub for progress)
- ✅ Celery integration (task queue)
- ✅ TTL support (auto-cleanup)
- ✅ Atomic operations (rate limiting)
- ✅ Persistence (optional, via AOF/RDB)

**Usage:**
1. **Task Queue:** Celery tasks enqueued here
2. **Pub/Sub:** Progress messages from workers → WebSocket
3. **Cache:** (Optional) Cache model metadata
4. **Rate Limiting:** (Optional) Limit API requests

**Why NOT:**
- Kafka: Overkill, slower for simple pub/sub
- RabbitMQ: More complex, slower than Redis
- Direct DB polling: Latency, database load

---

### **F. Celery + Workers**

**Why this choice:**
- ✅ Distributed task execution
- ✅ Retry logic built-in
- ✅ Job persistence (in Redis)
- ✅ Multiple queues (image, video, chat)
- ✅ Progress reporting via Redis

**Architecture:**
```
┌─────────────────┐
│ FastAPI Backend │
└────────┬────────┘
         │ enqueue task
         ▼
    ┌─────────────┐
    │ Redis Broker│
    └────────┬────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
 Worker1          Worker2
 (image)          (video)
```

**Why NOT:**
- AWS Lambda: Not suitable for long-running jobs (50+ seconds)
- Direct threading: Process limits, no distribution
- Kubernetes Jobs: Overkill for development, complex

---

### **G. MinIO Object Storage**

**Why this choice:**
- ✅ S3-compatible API (easy migration to AWS)
- ✅ Presigned URLs (expiring download links)
- ✅ Built-in Docker support
- ✅ Self-hosted (no cloud dependency)
- ✅ Bucket-based organization

**Workflow:**
```
1. Worker generates video → video_bytes
2. Worker PUT /outputs/job_id_0.mp4 → MinIO
3. MinIO stores in bucket
4. Backend generates presigned URL (expires 1 hour)
5. Frontend displays download link
6. User can share link, it expires automatically
```

**Why NOT:**
- Local disk: No presigned URLs, permission issues in Docker
- AWS S3: Cost, external dependency
- GCS: Cost, overkill for self-hosted
- Dropbox: Limited features, not designed for this

---

### **H. GPU Server (ComfyUI)**

**Why this choice:**
- ✅ Node-based workflow execution
- ✅ Custom node support (WanVideoWrapper)
- ✅ Automatic VRAM management
- ✅ HTTP API (easy remote integration)
- ✅ Output file serving built-in

**Why NOT:**
- Ollama: Text-only, not for vision/video
- LM Studio: Text-only
- vLLM: Text-only
- Custom Python: More fragile, harder to maintain

---

## 4. Why We Chose This Architecture

### **Principles:**

1. **Separation of Concerns**
   - Frontend: Presentation only
   - Backend: Business logic & orchestration
   - Workers: Heavy computation
   - Storage: Durability
   - GPU Server: Inference only

2. **Asynchronous Processing**
   - Long-running jobs (50+ seconds) don't block frontend
   - Users see immediate response (job queued)
   - Real-time progress via WebSocket
   - Workers can be scaled independently

3. **Loose Coupling**
   - Workers don't need to know about frontend
   - GPU server is just HTTP endpoint
   - Easy to swap storage (disk → S3)
   - Easy to add more workers

4. **Durability & Consistency**
   - PostgreSQL ensures job state persists
   - Redis ensures no task is lost
   - MinIO ensures outputs aren't deleted
   - Celery retries failed jobs

5. **Scalability**
   - Add more workers without changing code
   - Load balance across multiple GPUs
   - Cache presigned URLs
   - (Future) Replace MinIO with S3

---

## 5. Alternative Architectures Considered

### **Alternative A: Synchronous Processing (REJECTED)**

```
Frontend → Backend → GPU Server → Frontend (wait 50+ seconds)
```

**Problems:**
- ❌ HTTP timeout (typically 30s)
- ❌ Bad UX (spinning wheel for 50s)
- ❌ Can't scale (1 backend instance = 1 job max)
- ❌ No progress feedback
- ❌ Can't handle mobile (lost connection)

---

### **Alternative B: WebSocket Only (REJECTED)**

```
Frontend ←→ Backend (WebSocket persistent)
Backend ←→ GPU Server (HTTP polling)
Backend → MinIO
```

**Problems:**
- ❌ Backend holds connection for entire job (memory leak)
- ❌ Reconnection causes issues
- ❌ Hard to scale (connection affinity)
- ❌ Browser tab closes = job orphaned

---

### **Alternative C: Message Queue Only (REJECTED)**

```
Frontend → Backend → Redis
GPU Server ← Redis
GPU Server → MinIO → Backend → Frontend
```

**Problems:**
- ❌ No progress updates (can't push from worker)
- ❌ Workers need to know backend URL
- ❌ Hard to correlate outputs with jobs
- ❌ No API contract

---

### **Alternative D: Direct Backend ↔ GPU (REJECTED)**

```
Frontend → Backend → GPU Server (direct)
```

**Problems:**
- ❌ GPU server becomes bottleneck
- ❌ Can't run multiple inference engines
- ❌ Tight coupling (hard to upgrade GPU code)
- ❌ GPU server downtime blocks API

---

### **Alternative E: Kubernetes + Serverless (REJECTED)**

```
Frontend → Backend (K8s)
Worker Pods (K8s Horizontal Scaling)
GPU Nodes (K8s with GPU driver)
MinIO (S3)
```

**Problems for development:**
- ❌ Overkill for single dev environment
- ❌ Complex setup (Docker Desktop issues)
- ❌ YAML configuration hell
- ❌ Debugging is painful
- ✅ BUT: Good for production scaling

---

## 6. Current Architecture Strengths

| Aspect | Strength |
|--------|----------|
| **User Experience** | Real-time progress, instant job queuing, downloads |
| **Reliability** | Jobs survive backend restarts, retryable tasks |
| **Scalability** | Add workers = add compute, no code changes |
| **Maintainability** | Clear separation, each piece is simple |
| **Debuggability** | Logs at each layer, easy to trace |
| **Flexibility** | Can swap any component (Redis→MQ, MinIO→S3) |
| **Cost** | Self-hosted, no cloud lock-in |
| **Development** | Docker Compose, reproducible locally |

---

## 7. Current Architecture Weaknesses

| Weakness | Impact | Mitigation |
|----------|--------|-----------|
| Single GPU Worker | Sequential job processing | Add more workers (need more GPUs) |
| Redis Memory | Job data lost on restart | Add AOF persistence |
| No Auth | Anyone can submit jobs | Add JWT + rate limiting |
| PostgreSQL Single Instance | DB failure = no jobs | Add replication (in production) |
| Hard-coded GPU URL | Can't load-balance ComfyUI | Use DNS, add multiple ComfyUI endpoints |
| No job cancellation | Can't stop long jobs | Add cancel handler in worker |
| Presigned URLs expire | Links break after 1 hour | Increase expiry or regenerate |

---

## 8. Scaling Strategy (if needed)

### **Phase 1: Current (Development)**
- 1 Frontend
- 1 Backend
- 1 Worker (all queues)
- 1 GPU Server
- 1 PostgreSQL
- 1 Redis
- 1 MinIO

### **Phase 2: Multi-Worker**
```
Backend → Redis → ┬─ Worker (image) 
                  ├─ Worker (video)
                  └─ Worker (chat)
              ↓
           Multiple GPU Servers (ComfyUI instances)
```

**Implementation:**
- Duplicate worker containers (docker-compose)
- Load-balance GPU URLs via DNS or proxy
- Monitor queue lengths, auto-scale workers

### **Phase 3: Multi-Region**
```
Frontend → CloudFlare CDN
Backend → API Gateway → Load Balancer
         ├─ DC1 (GPU Server A)
         └─ DC2 (GPU Server B)
         
Database → Read Replicas
Cache → Redis Cluster
Storage → S3 (multi-region)
```

---

## 9. Recommended Improvements (No Breaking Changes)

### **Short Term (1-2 weeks)**

1. **Add Authentication**
   ```python
   # Backend: Add JWT tokens
   POST /auth/login → {"token": "jwt..."}
   
   # Frontend: Store token in localStorage
   # All requests: Add Authorization header
   ```

2. **Add Job Cancellation**
   ```python
   # Worker checks for cancel signal
   def run_video_job(job_id):
       if should_cancel(job_id):
           celery.current_task.revoke()
   
   # API endpoint
   DELETE /api/jobs/{id} → revoke task
   ```

3. **Add Rate Limiting**
   ```python
   # Backend: 10 jobs per user per day
   from slowapi import Limiter
   
   @app.post("/api/jobs")
   @limiter.limit("10/day")
   def create_job():
       ...
   ```

4. **Add Job Timeout**
   ```python
   @app.task(time_limit=3600)  # 1 hour max
   def run_video_job():
       ...
   ```

---

### **Medium Term (1-2 months)**

1. **Add Database Backup**
   ```bash
   # Automated daily backups to S3
   pg_dump | gzip | aws s3 cp - s3://backups/db.sql.gz
   ```

2. **Add Redis Persistence**
   ```bash
   # AOF: Append-only file
   redis-cli CONFIG SET appendonly yes
   ```

3. **Add Prometheus Metrics**
   ```python
   from prometheus_client import Counter, Histogram
   
   jobs_submitted = Counter('jobs_submitted_total', '', ['type'])
   job_duration = Histogram('job_duration_seconds', '', ['type', 'status'])
   ```

4. **Add Job Retry Logic**
   ```python
   @app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
   def run_video_job(job_id):
       try:
           # ... processing ...
       except Exception as e:
           retry_or_fail_task(self, job_id, e)
   ```

---

### **Long Term (3+ months)**

1. **Migrate to Kubernetes**
   - Helm charts for each component
   - Auto-scaling based on queue length
   - Node affinity (video jobs → GPU nodes)

2. **Add S3 Storage**
   - Replace MinIO with S3
   - Multi-region replicas
   - CloudFront CDN

3. **Add User Management**
   - User profiles
   - Job ownership
   - Billing/quotas

4. **Add Model Management**
   - Download models on-demand
   - Model versioning
   - A/B testing different model versions

---

## 10. Conclusion

### **Why This Architecture?**

This architecture balances **simplicity** (good for development) with **production-readiness** (reliable, scalable):

- ✅ **Frontend & Backend Separation**: Easy to develop independently
- ✅ **Asynchronous Processing**: Real-time progress without blocking
- ✅ **Distributed Workers**: Scale compute independently
- ✅ **Durable Storage**: Jobs and outputs persist
- ✅ **Self-Contained**: Everything runs locally (no cloud dependency)
- ✅ **Clear Data Flow**: Easy to debug and understand

### **Is There a Better Way?**

**For Development:** ✅ Current approach is optimal
- Simple to understand
- Easy to iterate
- Reproducible (Docker Compose)
- All patterns scale to production

**For Production:** 
- **Yes, if you need:** High availability, multi-region, auto-scaling, 99.9% uptime
- **Then use:** Kubernetes + S3 + RDS + Managed Redis (AWS/GCP)
- **Cost:** ~$500-2000/month depending on traffic

**For This Project:** ✅ Current approach is best
- Self-hosted (no cloud lock-in)
- Transparent (understand every layer)
- Cost-effective ($0 if you own hardware)
- Educational (learn real-world patterns)

---

**Architecture Designed:** April 1, 2026  
**Status:** Production-ready for single-GPU, single-region deployment  
**Next Evolution:** Kubernetes migration when scaling beyond 1 GPU
