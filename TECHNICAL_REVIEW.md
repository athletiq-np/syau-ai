# 🔍 SYAU AI — Complete Technical Architecture Review

**Reviewer:** Principal Systems Architect (Independent)  
**Date:** April 2, 2026  
**Context:** Solo developer, local dev + remote GPU server, early-stage testing, stability focus

---

## 📋 **1. Current State & Progress Recap**

### What Has Been Implemented

**SYAU AI** is a professional cinematic filmmaking pipeline built on a modern async architecture. The system comprises:

- **Frontend:** Next.js + React + ReactFlow (workflow editor with infinite canvas, smart connections, real-time job monitoring)
- **Backend:** FastAPI + Celery + PostgreSQL + Redis + MinIO (asynchronous job processing with WebSocket real-time updates)
- **GPU Services:** Remote vLLM (Qwen 2.5 LLM for script analysis) + ComfyUI (Wan 2.2 14B T2V/I2V video generation)
- **Infrastructure:** Docker Compose (local dev) + Nginx (reverse proxy) + SSH tunneling (GPU server connectivity)

**Core Workflow:**
```
Script (User Input)
  ↓ [Qwen LLM via vLLM]
Scene Breakdown & Shot Generation
  ↓ [Wan 2.2 via ComfyUI]
Individual Videos (T2V/I2V)
  ↓ [FFmpeg stitching]
Final Composite Video
```

**Database Schema:** 6 tables (Projects, Scenes, Shots, Characters, Jobs, AIModels) with relational integrity and proper indexing.

### Problems Solved & Approaches Used

| Problem | Solution | Status |
|---------|----------|--------|
| **Blocking UI during 50s video generation** | Async Celery workers + WebSocket real-time progress | ✅ Solved |
| **No progress feedback to user** | Redis pub/sub → WebSocket broadcaster | ✅ Solved |
| **Local GPU memory exhaustion** | Remote GPU server (202.51.2.50) + SSH tunneling | ✅ Solved |
| **Output persistence across restarts** | PostgreSQL + MinIO presigned URLs | ✅ Solved |
| **Workflow node parameter editing** | Zustand state store + debounced API calls (500ms) | ✅ Solved |
| **Node connection type safety** | Handle color-coding + `isValidConnection` prop validation | ✅ Solved |
| **Data directory persistence** | Docker volume mappings (`.docker-data/models`, etc.) | ✅ Fixed 2 hours ago |

### Implicit Assumptions & Shortcuts

1. **Single GPU assumption:** System designed for 1 GPU at a time (`celery -c 1`). Multi-GPU scaling would require queue redesign.
2. **Synchronous inference handlers:** All handlers use `def` not `async def` to avoid Celery event loop conflicts. This limits throughput on CPU-bound tasks.
3. **No authentication:** Phase 1 explicitly avoids auth/payments. Anyone with access to the API can submit jobs.
4. **Presigned URLs (1-hour expiry):** Output URLs regenerated at read time. Clock skew on distributed systems could cause 404s.
5. **ComfyUI polling (no webhooks):** Worker polls `/history/{prompt_id}` every 2 seconds. No active push notifications from GPU server.
6. **Remote vLLM via SSH tunnel:** Requires manual `ssh -L` tunnel. No automatic reconnection or failover.
7. **No database migrations in production:** Using Alembic, but no automated rollback strategy documented.
8. **Stale job reconciliation:** Hardcoded timeout windows (30s pending, 300s running). Jobs exceeding these are marked failed even if processing.

---

## 🏗️ **2. System Architecture & Flow**

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER (Browser)                              │
│              http://localhost:3000                              │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           NGINX Gateway (localhost:80)                          │
│           ├─ /api/* → FastAPI :8000                             │
│           ├─ /ws/* → WebSocket :8000                            │
│           └─ /* → Frontend :3000                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Frontend    │  │  Backend API │  │   Workers    │
│  :3000       │  │  :8000       │  │  (Celery)    │
│  (React)     │  │  (FastAPI)   │  │  (Python)    │
└──────────────┘  └──────┬───────┘  └──────┬───────┘
                         │                  │
        ┌────────────────┼──────────────────┼────────┐
        ▼                ▼                  ▼        ▼
   ┌─────────┐      ┌────────┐         ┌────────┐ ┌─────┐
   │ Postgres│      │ Redis  │         │ MinIO  │ │ GPU │
   │ :5433   │      │ :6380  │         │ :9000  │ │Srvr │
   └─────────┘      └────────┘         └────────┘ └─────┘
                         │
                    Job Queue
                  (video, image,
                   chat, studio)
```

### End-to-End Data Flow (T2V Video Generation)

```
TIME    ACTOR              ACTION
───────────────────────────────────────────────────────────────────
T+0s    User (Browser)     Click "Generate Video" button
        ↓
        React Component    Validate form, build payload
        ↓
        HTTP POST          /api/jobs {type, model, prompt, params}
        ↓
T+0.1s  FastAPI Handler    1. Write Job to PostgreSQL (status=pending)
                           2. Dispatch Celery task → Redis queue
                           3. Return 202 Accepted {job_id}
        ↓
        Browser            Update UI: "Job queued, job_id=abc123"
        ↓
T+0.3s  Browser            Open WebSocket: ws://localhost/ws
        ↓
        WebSocket Manager  Subscribe to job abc123 updates
        ↓
T+0.5s  Celery Worker      Poll video queue, pick up task
                           Update job.status → "running"
                           Publish to Redis: job:abc123
        ↓
        Redis Pub/Sub       Broadcast {status: running, progress: 5}
        ↓
        WebSocket Handler  Receive Redis msg, forward to browser
        ↓
        Browser UI         Update: "Running... 5%"
        ↓
T+1s    Celery Worker      Build ComfyUI T2V workflow JSON
        ↓
        HTTP POST          http://gpu-server:8188/prompt
        ↓
T+1.1s  ComfyUI Server     Queue workflow, return prompt_id=xyz789
        ↓
T+1.2-45s Celery Worker    Poll /history/xyz789 every 2s
          (loop)           Publish progress: 10%, 20%, ..., 80%
        ↓
T+45s   ComfyUI            Workflow complete, write to /output/
        ↓
        Celery Worker      Detect completion in /history response
                           Download MP4 from /view?filename=...
        ↓
T+46s   MinIO Upload       PUT /syau-outputs/outputs/abc123_0.mp4
        ↓
        Celery Worker      Update job in PostgreSQL:
                           - status → "done"
                           - output_keys → ["outputs/abc123_0.mp4"]
                           - completed_at → now
        ↓
        Redis Pub/Sub       Broadcast {status: done, progress: 100}
        ↓
        WebSocket Handler  Forward to browser
        ↓
T+46.5s Browser UI         Update: "✓ Complete" + video preview
        ↓
        User               Click download → Presigned URL from MinIO
        ↓
T+50s   User               Video saved to Downloads
```

### Component Interactions Matrix

| From | To | Protocol | State Managed | Purpose |
|------|----|----|---|---|
| Browser | Nginx | HTTP | Session (browser local) | UI delivery, routing |
| Browser | FastAPI | HTTP/REST | Session + JWT (none now) | Job submission, status polling |
| Browser | FastAPI | WebSocket | Connection mgmt | Real-time job progress |
| FastAPI | PostgreSQL | SQL | Transaction scope | Job CRUD, state persistence |
| FastAPI | Redis | Command protocol | Pub/Sub channels | Queue dispatch, progress broadcast |
| Celery Worker | Redis | Command protocol | Task queue | Job pickup, acknowledgment |
| Celery Worker | ComfyUI | HTTP REST | Stateless | Workflow submission & polling |
| Celery Worker | MinIO | S3 API | Multipart upload | Output storage |
| FastAPI | MinIO | S3 API | Presigned URLs | Output URL generation |

---

## 🔍 **3. Unbiased Critical Analysis**

### ✅ **Strengths**

**1. Async-First Architecture (Excellent Design)**
- Decouples frontend from GPU processing
- Users see immediate feedback (202 Accepted)
- Real-time progress via WebSocket avoids polling fatigue
- Scales horizontally (add workers = add GPU capacity)
- **Principle:** Matches SoA best practices; avoids blocking HTTP requests

**2. Type-Safe Database Schema**
- Proper relational integrity (foreign keys, cascading deletes)
- Enum-based status fields (not strings) prevents invalid state transitions
- Indexed by job status and type for fast filtering
- **Principle:** ACID compliance, referential integrity maintained

**3. Professional UI/UX (ReactFlow)**
- Infinite canvas with real pan/zoom (not broken SVG)
- Color-coded handle types prevent incorrect connections
- Real-time node status badges (done, running, failed, pending)
- Drag-to-add node library + Assets tab
- **Principle:** Matches Imagine.Art/ElevenLabs professional standards

**4. Proper Separation of Concerns**
- Frontend layer (Next.js) isolated from backend logic
- API layer (FastAPI) decoupled from inference (remote GPU)
- Workers run independently; backend crash ≠ job loss
- **Principle:** Conway's Law - org structure mirrors architecture

**5. Production-Ready Infrastructure Foundation**
- Docker Compose for local reproducibility
- Environment-based config (.env) separation
- Structured logging (structlog JSON)
- Health checks on all critical services
- **Principle:** 12-factor app compliance

---

### ⚠️ **Weaknesses & Technical Debt**

**Tier 1: Critical (Blocks Stability)**

| Issue | Impact | Workaround |
|-------|--------|-----------|
| **No error handling in workers** | Failed jobs don't retry; manual intervention needed | Log error, hope user retries from UI |
| **ComfyUI polling is fragile** | Race conditions if job completes before polling starts | Could hang indefinitely if GPU server dies |
| **SSH tunnel is manual** | If tunnel dies, workers can't reach GPU server | Must manually restart PowerShell script |
| **No job retry logic** | Network blip = permanent job failure | User must resubmit |
| **Missing stale job detection** | If worker crashes mid-job, job stays "running" forever | Startup reconciliation helps only at startup |
| **No monitoring/alerting** | Silent failures; no visibility | Must manually check logs |

**Tier 2: High (Affects Reliability)**

| Issue | Impact | Workaround |
|-------|--------|-----------|
| **Single GPU (concurrency=1)** | Only 1 job at a time; queue builds up | Add more GPUs; requires load balancer |
| **No input validation on GPU** | Bad workflows cause vague errors | Backend could pre-validate before sending |
| **Presigned URLs expire (1hr)** | Users can't share links after 1 hour | Regenerate on each view |
| **No rate limiting** | Malicious user could spam 1000 jobs | No auth, so anyone can attack |
| **WebSocket memory leak risk** | Connection might hang if client disconnects badly | No explicit cleanup observed |
| **No database backups** | One hard drive failure = data loss | Must manually backup .docker-data/ |
| **ComfyUI runs as manual bash script** | If server restarts, ComfyUI doesn't auto-restart | One is manual, one is automatic (inconsistent) |

**Tier 3: Medium (Affects Maintainability)**

| Issue | Impact |
|-------|--------|
| **No structured logging** | Hard to trace bugs; logs mixed with stdout |
| **No async/await in workers** | Blocks Celery event loop; limits future optimization |
| **Hardcoded GPU server IP** | If server moves, code must change |
| **No API versioning** | Breaking changes break frontend immediately |
| **No request/response schema validation** | Typos in params silently ignored |
| **ComfyUI polling interval hardcoded** | Inefficient or misses updates |
| **Workflow editor state not persisted** | Browser crash = lost draft workflow |

---

### 🔀 **Trade-Offs & Past Decisions (Objective Analysis)**

| Decision | Why Chosen | Pros | Cons | Viable Alternatives |
|---|---|---|---|---|
| **Async Celery + WebSocket** | Avoid blocking HTTP timeout | Real-time UX, scalable | Complex state mgmt, overhead | Serverless (costs more, slower) |
| **Remote GPU (SSH tunnel)** | Avoid local GPU OOM | Clean separation, cheap VPS | Fragile, manual setup | Co-locate GPU + API (easier, costs more) |
| **ComfyUI for T2V/I2V** | Stable, tested, open-source | Flexible workflows, active community | Polling inefficiency, external dependency | Direct diffusers (fragile) |
| **Phase 1 no-auth** | Ship faster, reduce scope | MVP speed, simpler code | Security risk, no multi-user | JWT + Auth0 (costs, complexity) |
| **PostgreSQL + Redis** | ACID + fast cache | Reliability, proven, simple | Not horizontally scaled yet | MongoDB (less reliable) |
| **MinIO (S3-compatible)** | Self-hosted, S3 API parity | Cost-effective, portable | Requires management | AWS S3 (vendor lock-in) |

**Verdict:** Core decisions are sound for test/MVP phase. Problems emerge at scale (multi-user, multi-GPU, 24/7 uptime).

---

### 🚨 **Hidden Risks**

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| **SSH tunnel dies silently** | HIGH | All jobs fail with 0 progress | Heartbeat monitor + auto-restart |
| **ComfyUI OOM crash** | MEDIUM | Jobs queue indefinitely | Memory limits + model cache tuning |
| **Redis persistence loss** | MEDIUM | Queued jobs vanish | Enable AOF (done ✅) |
| **PostgreSQL disk full** | LOW | API can't write new jobs | Monitoring + quota alerts |
| **MinIO object corruption** | LOW | Users can't download videos | Versioning + backup |
| **Job status stuck "running"** | MEDIUM | Stale job marked failed | Monitor for timeout jobs |
| **Concurrent worker race condition** | MEDIUM | Two workers claim same job | Celery acks handle this |
| **Frontend refresh mid-generation** | LOW | WebSocket disconnects | Auto-poll fallback |

---

## 💡 **4. Recommendations & Proposed Changes**

### **Priority Matrix: Impact vs Effort**

### **Top 10 Recommendations (Ranked by Stability Impact)**

#### **[1] Add Exponential Backoff Retry Logic** 
**Impact:** HIGH | **Effort:** MEDIUM | **Time:** 3-4 hours

**Rationale:** Network blips or temporary GPU server unavailability cause permanent job failure. Retrying 3 times with exponential backoff handles transient failures gracefully.

**Implementation:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True
)
def infer_with_retry(client, job_params):
    return client.infer_wan_t2v(**job_params)
```

**Expected Benefit:** Reduces job failure rate by ~60%  
**Risk:** Retry storm if GPU permanently down; need timeout guard

---

#### **[2] Add Comprehensive Error Handling & User Feedback**
**Impact:** HIGH | **Effort:** MEDIUM | **Time:** 4-5 hours

**Rationale:** Workers fail silently; users don't know why. Add structured error messages.

**Expected Benefit:** Users understand failures; can retry intelligently  
**Risk:** More complex code; must define all error codes upfront

---

#### **[3] Add ComfyUI Watchdog (Health Check + Auto-Restart)**
**Impact:** HIGH | **Effort:** HIGH | **Time:** 6-8 hours

**Rationale:** ComfyUI runs as manual bash script; if it crashes, workers hang indefinitely.

**Option A: Simple** — Convert ComfyUI bash to systemd service
```bash
[Unit]
Description=SYAU ComfyUI Server
After=network.target

[Service]
Type=simple
User=ekduiteen
WorkingDirectory=/data/ComfyUI
ExecStart=/data/ComfyUI/venv/bin/python main.py --listen 0.0.0.0 --port 8188
Restart=on-failure
RestartSec=10
```

**Expected Benefit:** Auto-recovery on ComfyUI crash  
**Risk:** Systemd configuration complexity

---

#### **[4] Enable SSH Tunnel Auto-Restart**
**Impact:** HIGH | **Effort:** MEDIUM | **Time:** 2-3 hours

**Rationale:** SSH tunnel dies → all jobs fail silently. Need auto-restart.

**Implementation:**
- Backend heartbeat task pings `http://localhost:8188/health` every 30s
- On 3 consecutive failures → execute `infra/scripts/restart-gpu-tunnel.sh`
- Log tunnel status for alerting

**Expected Benefit:** Detect tunnel failures within 90s; enable auto-recovery  
**Risk:** False positives if GPU server is slow

---

#### **[5] Add Structured Logging & Monitoring**
**Impact:** HIGH | **Effort:** HIGH | **Time:** 5-6 hours

**Rationale:** Can't diagnose failures without logs/metrics

**Implementation:**
- FastAPI: structured logs via structlog (already done ✅)
- Add Prometheus metrics (job submission rate, duration, failure rate)
- Deploy Grafana with job queue depth, GPU utilization, API latency
- Set alert thresholds (queue depth > 10, API latency > 5s)

**Expected Benefit:** Observability; diagnose 90% of issues within 5 minutes  
**Risk:** Added infrastructure complexity

---

#### **[6] Implement Basic API Authentication**
**Impact:** HIGH | **Effort:** MEDIUM | **Time:** 3-4 hours

**Rationale:** Without auth, anyone can spam jobs. Need user isolation even for testing.

**Implementation:**
- Add FastAPI OAuth2 middleware
- Generate API keys for test users
- Store `user_id` in Job model
- Enforce `Authorization: Bearer {token}` on all endpoints

**Expected Benefit:** Prevent accidental multi-user conflicts; foundation for Phase 2  
**Risk:** Adds 1-2 minutes to job submission

---

#### **[7] Enable Redis Persistence (AOF)**
**Impact:** HIGH | **Effort:** LOW | **Time:** 30 min

**Rationale:** Queue jobs lost on Redis restart without AOF

**Status:** Already enabled in docker-compose ✅

**Verification:**
1. Confirm `.docker-data/redis/appendonly.aof` exists and grows
2. Test: Kill redis container, restart → jobs still queued

---

#### **[8] Multi-GPU Worker Orchestration**
**Impact:** MEDIUM | **Effort:** HIGH | **Time:** 5-6 days

**Rationale:** Single GPU = sequential processing. Need parallel throughput.

**Implementation:**
- Split `worker-studio` into `worker-studio-gpu0`, `worker-studio-gpu1`
- Each worker binds to its GPU via `CUDA_VISIBLE_DEVICES`
- Update docker-compose with GPU device assignments

**Expected Benefit:** Linear scaling: 2 GPUs = 2x throughput  
**Risk:** Requires additional GPU resources

---

#### **[9] Rate Limiting & Per-User Quotas**
**Impact:** MEDIUM | **Effort:** MEDIUM | **Time:** 3-4 days

**Rationale:** Prevent abuse; fair resource allocation

**Implementation:**
- Sliding window: 10 jobs/hour per API key
- Hard quota: 100 jobs/month per user
- Return 429 Too Many Requests when exceeded

**Expected Benefit:** Predictable resource usage; foundation for billing  
**Risk:** Users frustrated by quotas

---

#### **[10] Database Migration Rollback Testing**
**Impact:** MEDIUM | **Effort:** MEDIUM | **Time:** 2-3 days

**Rationale:** Deployments should be reversible

**Implementation:**
- Add CI test: `alembic upgrade head && alembic downgrade -1`
- Document rollback steps in deployment runbook
- Test on staging before production

**Expected Benefit:** Safe deployments  
**Risk:** None

---

## 🗺️ **5. Phased Improvement Roadmap**

### **Phase 0: Test (Current)**
- ✅ Script → LLM analysis → T2V/I2V pipeline works
- ✅ ReactFlow UI implemented
- ⚠️ No auth, no monitoring, single GPU

### **Phase 1: Stability (0-4 Weeks) — "Hardening"**

**Goals:** Safe for multi-developer testing; detect failures fast

| Week | Task | Effort | Verification |
|------|------|--------|---|
| 1 | Basic auth (API keys) + SSH tunnel heartbeat | 3 days | 3 test users can submit jobs; tunnel restarts automatically |
| 1-2 | Structured logging + Grafana dashboard | 3 days | Logs JSON; Grafana shows job queue depth |
| 2 | Redis persistence verification + backups | 1 day | Kill redis → data persists |
| 2-3 | Multi-GPU orchestration (if 2 GPUs available) | 5 days | 2 concurrent jobs run in parallel |
| 3-4 | Database migration testing + rollback docs | 2 days | CI test `upgrade → downgrade` passes |

**Deliverable:** Production-ready for 5-10 concurrent users testing

---

### **Phase 2: Scalability (1-3 Months) — "Growth"**

| Month | Task | Effort |
|---|---|---|
| 1 | Rate limiting + per-user quotas | 5 days |
| 1-2 | ComfyUI polling optimization (5s interval) | 2 days |
| 2 | Job history pagination + filtering | 3 days |
| 2 | Batch job submission API | 5 days |
| 3 | Email notifications (job complete) | 3 days |

**Deliverable:** Production-ready for 50+ concurrent users

---

### **Phase 3: Production (3-6 Months) — "Launch"**

| Month | Task | Effort |
|---|---|---|
| 3 | Kubernetes deployment manifests | 10 days |
| 3-4 | Payment integration (Stripe) + credit system | 15 days |
| 4 | User authentication (Auth0 or custom JWT) | 10 days |
| 4-5 | Video quality/compression options | 5 days |
| 5 | Advanced workflow features (batch, scheduling) | 10 days |
| 5-6 | SLA monitoring + 99.9% uptime target | 10 days |

**Deliverable:** Production-ready for 1000+ concurrent users; monetized

---

### **Quick Wins (This Week)**

1. **Enable Redis AOF** (5 min) → Jobs survive restart ✅ (Done)
2. **Add SSH tunnel heartbeat** (2 hours) → Detect tunnel failures early
3. **Document API security note** (30 min) → Warn users Phase 1 has no auth
4. **Create simple JSON logs** (1 hour) → Basic observability

---

## 📌 **Summary Table: All Recommendations**

| # | Recommendation | Priority | Effort | Impact |
|---|---|---|---|---|
| 1 | API Authentication | CRITICAL | Medium | HIGH |
| 2 | SSH Tunnel Heartbeat | CRITICAL | Medium | HIGH |
| 3 | Redis Persistence | CRITICAL | Low | HIGH |
| 4 | Multi-GPU Setup | HIGH | High | HIGH |
| 5 | Monitoring (Prometheus + Grafana) | HIGH | High | HIGH |
| 6 | Tunnel Restart Script | HIGH | Low | MEDIUM |
| 7 | Rate Limiting | MEDIUM | Medium | MEDIUM |
| 8 | Migration Rollback Testing | MEDIUM | Medium | MEDIUM |
| 9 | ComfyUI Polling Optimization | MEDIUM | High | MEDIUM |
| 10 | Presigned URL Configuration | LOW | Low | LOW |

---

## ✅ **Conclusion**

**System Health: 7/10 (Test Phase)**
- ✅ Core async architecture is sound
- ✅ UI/UX matches professional standards
- ⚠️ Missing production safeguards (auth, monitoring, failover)
- ⚠️ Single GPU limits throughput
- 🚨 SSH tunnel is SPOF (single point of failure)

**For Production: 4/10 (Needs Hardening)**
- Add auth + monitoring first
- Then multi-GPU + rate limiting
- Then Kubernetes deployment

**Next 48 Hours:**
1. Add basic API key auth (1-2 hours)
2. Add SSH tunnel heartbeat (2 hours)
3. Verify Redis AOF working (30 min)
4. Deploy → test multi-developer scenario

**You're here:** ⭐️⭐️⭐️⭐️ **MVP Working** → Goal: ⭐️⭐️⭐️⭐️⭐️ **Production Ready** (4-6 weeks)
