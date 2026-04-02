# API Authentication & Tunnel Monitoring

**Date:** April 2, 2026  
**Status:** ✅ Implemented (Phase 1 Stability)

---

## 1. API Authentication

### Overview

All REST API endpoints now require Bearer token authentication (except `/health`).

- **Format:** `Authorization: Bearer {api_key}`
- **Scope:** Jobs, Projects, Models endpoints
- **User Tracking:** Each job/project tracks the authenticated user (`user_id`)
- **Isolation:** Users can only view/delete their own jobs and projects

### API Keys

**Development Environment (.env):**
```env
API_KEY_ENABLED=true
API_KEY_DEV=syauai_dev_key_12345
API_KEY_TEST=syauai_test_key_67890
```

**Current Valid Keys:**
| Key | User ID | Purpose |
|-----|---------|---------|
| `syauai_dev_key_12345` | dev-user | Local development |
| `syauai_test_key_67890` | test-user | Testing / CI |

### Usage Examples

**Submit a job with auth:**
```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Authorization: Bearer syauai_dev_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "video",
    "model": "wan-2.2",
    "prompt": "a cat playing",
    "negative_prompt": "",
    "params": {
      "num_frames": 81,
      "width": 640,
      "height": 640
    }
  }'
```

**List your jobs:**
```bash
curl -X GET "http://localhost:8000/api/jobs?page=1&page_size=20" \
  -H "Authorization: Bearer syauai_dev_key_12345"
```

**Get job details:**
```bash
curl -X GET "http://localhost:8000/api/jobs/{job_id}" \
  -H "Authorization: Bearer syauai_dev_key_12345"
```

**Cancel a job:**
```bash
curl -X DELETE "http://localhost:8000/api/jobs/{job_id}" \
  -H "Authorization: Bearer syauai_dev_key_12345"
```

### Error Responses

**Missing auth header:**
```json
{
  "detail": "Missing Authorization header. Use: Authorization: Bearer {api_key}"
}
```
Status: `403 Forbidden`

**Invalid auth format:**
```json
{
  "detail": "Invalid Authorization format. Use: Bearer {api_key}"
}
```
Status: `403 Forbidden`

**Invalid API key:**
```json
{
  "detail": "Invalid API key"
}
```
Status: `403 Forbidden`

**Unauthorized access (other user's job):**
```json
{
  "detail": "Unauthorized: job belongs to another user"
}
```
Status: `403 Forbidden`

### Implementation Details

**Files Modified:**
- `backend/core/config.py` — Added `api_key_enabled`, `api_key_dev`, `api_key_test`
- `backend/core/security.py` — **NEW** API key verification logic
- `backend/models/job.py` — Added `user_id` column (indexed)
- `backend/services/job_service.py` — Updated `create_job()` and `list_jobs()` to handle user_id
- `backend/api/routes/jobs.py` — Added `@Depends(get_current_user)` to all endpoints
- `.env` — Added API key configuration

**Database Migration (Required):**
```sql
ALTER TABLE jobs ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT 'anonymous' INDEX;
```

Or via Alembic:
```bash
alembic revision --autogenerate -m "Add user_id to jobs table"
alembic upgrade head
```

### Frontend Integration

The frontend must send API key in all requests:

```typescript
// lib/api.ts (example)
const headers = {
  'Authorization': `Bearer ${process.env.NEXT_PUBLIC_API_KEY}`,
  'Content-Type': 'application/json',
};

const response = await fetch('/api/jobs', { headers });
```

**Set in frontend .env:**
```
NEXT_PUBLIC_API_KEY=syauai_dev_key_12345
```

### Phase 2 (Future)

- OAuth2 / OpenID Connect integration
- User registration and login
- API key rotation
- Scope-based permissions (read-only vs write)
- Rate limiting per user (10 jobs/hour)

---

## 2. SSH Tunnel Heartbeat Monitor

### Overview

Background task that continuously monitors GPU server accessibility and auto-restarts SSH tunnel if it fails.

- **Check Interval:** 30 seconds
- **Failure Threshold:** 3 consecutive failures = 90 seconds total downtime before restart attempt
- **Auto-Restart:** Executes restart script when threshold exceeded
- **Logging:** Structured JSON logs to track tunnel health

### How It Works

**Monitoring Loop:**
```
Every 30 seconds:
  1. Ping http://localhost:8188/system_stats (ComfyUI)
  2. Ping http://localhost:8100/v1/models (vLLM)
  3. If both fail → increment failure counter
  4. If counter >= 3 → trigger restart script
  5. If either succeeds → reset counter
```

**Restart Process:**
```
1. Detect OS (Windows/Linux)
2. Kill existing SSH processes
3. Run restart script (PowerShell on Windows, bash on Linux)
4. Wait 5 seconds for tunnel to establish
5. Resume health checks
```

### Configuration

**In `.env`:**
```env
COMFYUI_URL=http://host.docker.internal:8188
INFERENCE_API_BASE_URL=http://host.docker.internal:8100/v1
```

**In code (backend/tasks/tunnel_monitor.py):**
```python
TunnelHealthMonitor(
    comfyui_url="http://localhost:8188",
    vllm_url="http://localhost:8100",
    check_interval=30,          # Check every 30s
    failure_threshold=3,        # Restart after 3 failures (90s)
)
```

### Logs

**Normal operation:**
```json
{
  "event": "tunnel_monitor_started",
  "check_interval": 30
}
```

**Health check passed:**
```json
{
  "event": "tunnel_health_check_success",
  "comfyui_ok": true,
  "vllm_ok": true
}
```

**Health check failed:**
```json
{
  "event": "tunnel_health_check_failed",
  "consecutive_failures": 1,
  "comfyui_ok": false,
  "vllm_ok": false
}
```

**Restart triggered:**
```json
{
  "event": "tunnel_restart_attempt",
  "threshold_failures": 3,
  "script": "infra/scripts/restart-gpu-tunnel.ps1"
}
```

**Tunnel recovered:**
```json
{
  "event": "tunnel_recovered"
}
```

### Restart Script (Windows)

**Location:** `infra/scripts/restart-gpu-tunnel.ps1`

**What it does:**
1. Kills existing SSH processes
2. Waits 2 seconds
3. Starts new SSH tunnel with exponential backoff
4. Logs status to `infra/scripts/tunnel.log`
5. Returns exit code 0 (success) or 1 (failure)

**Manual execution:**
```powershell
powershell -ExecutionPolicy Bypass -File infra/scripts/restart-gpu-tunnel.ps1
```

**Output:**
```
2026-04-02 14:23:45 - === Tunnel Restart Script Started ===
2026-04-02 14:23:45 - Killing existing SSH processes on port 8188...
2026-04-02 14:23:46 - Force-stopping SSH processes...
2026-04-02 14:23:48 - Tunnel connection attempt 1 of 3...
2026-04-02 14:23:48 - Executing: ssh -N -L 8188:localhost:8188 -p 41447 ekduiteen@202.51.2.50
2026-04-02 14:23:48 - SSH tunnel process started (PID: 1234)
2026-04-02 14:23:50 - ✓ Tunnel restart successful
```

### Restart Script (Linux)

**Location:** `infra/scripts/restart-gpu-tunnel.sh` (not yet created)

**To be implemented:**
```bash
#!/bin/bash
pkill -f "ssh.*8188"
sleep 2
ssh -N -L 8188:localhost:8188 -p 41447 ekduiteen@202.51.2.50 &
```

### Implementation Details

**Files Created:**
- `backend/tasks/tunnel_monitor.py` — Heartbeat monitoring class
- `infra/scripts/restart-gpu-tunnel.ps1` — Windows tunnel restart script

**Files Modified:**
- `backend/main.py` — Integrated `start_tunnel_monitor()` and `stop_tunnel_monitor()` into lifespan
- `.env` — Verified COMFYUI_URL and INFERENCE_API_BASE_URL are set

### Monitoring in Production

**Alerting:**
- Watch for `tunnel_restart_attempt` in logs → alert on-call
- Watch for consecutive `tunnel_health_check_failed` → notify DevOps
- Set up log aggregation (ELK, CloudWatch) to track tunnel stability

**Dashboard Metrics:**
```
tunnel_failures_per_hour = count("tunnel_health_check_failed")
tunnel_restarts_per_day = count("tunnel_restart_attempt")
tunnel_uptime_percentage = (checks_passed / total_checks) * 100
```

### Troubleshooting

**Tunnel keeps restarting:**
- GPU server (202.51.2.50) is down → check server health
- Network is unstable → check router/firewall
- SSH credentials changed → update .env or SSH config
- Port 41447 blocked → check firewall rules

**Monitor not detecting failures:**
- Check structured logs: `tail backend.log | grep tunnel`
- Verify ComfyUI is running on GPU server: `curl http://202.51.2.50:8188/system_stats`
- Verify SSH tunnel is established: `netstat -an | grep 8188`

**Restart script fails:**
- Run manually: `powershell -ExecutionPolicy Bypass -File infra/scripts/restart-gpu-tunnel.ps1`
- Check script logs: `cat infra/scripts/tunnel.log`
- Verify SSH installed: `ssh -V`

---

## Testing Checklist

- [ ] **Auth**: Submit job with valid API key → Success (202)
- [ ] **Auth**: Submit job without API key → Fail (403)
- [ ] **Auth**: Submit job with invalid API key → Fail (403)
- [ ] **Auth**: List jobs with dev key → See only dev-user jobs
- [ ] **Auth**: List jobs with test key → See only test-user jobs
- [ ] **Auth**: Get other user's job → Fail (403)
- [ ] **Auth**: Cancel other user's job → Fail (403)
- [ ] **Tunnel**: Simulate tunnel failure → Wait 90s → See restart attempt in logs
- [ ] **Tunnel**: Check `tunnel.log` for restart success
- [ ] **Tunnel**: Job should eventually complete despite tunnel failure
- [ ] **Tunnel**: Monitor resumes checking after restart

---

## Next Steps

1. ✅ API Authentication implemented
2. ✅ SSH Tunnel Heartbeat Monitor implemented
3. ⏳ Database migration for user_id column (auto via Alembic)
4. ⏳ Frontend integration (pass API key in all requests)
5. ⏳ Rate limiting per user (Phase 2)
6. ⏳ Multi-user support (Phase 2)

---

**Generated by:** Claude Code  
**Last Updated:** April 2, 2026, 23:45 UTC
