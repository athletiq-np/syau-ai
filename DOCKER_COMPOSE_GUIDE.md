# Docker Compose - Local Development Guide

**Date:** April 2, 2026  
**Status:** ✅ RUNNING

---

## Quick Start

```bash
cd /path/to/Syau-ai
docker-compose up -d
```

That's it! Everything runs in containers with one command.

---

## What's Running (10 Services)

| Service | Port(s) | Purpose |
|---------|---------|---------|
| **nginx** | 80 | Reverse proxy (frontend + API) |
| **frontend** | 3000 | Next.js dev server |
| **backend** | 8000 | FastAPI application |
| **postgres** | 5433 | Database |
| **redis** | 6380 | Cache/Queue |
| **minio** | 9000, 9001 | Object storage |
| **worker-image** | - | Image generation worker |
| **worker-video** | - | Video generation worker |
| **worker-chat** | - | Chat worker |
| **worker-studio** | - | Cinema pipeline worker |

---

## Access Points

### Development URLs
```
Frontend:   http://localhost          (via Nginx)
API Direct: http://localhost:8000     (direct backend)
API Proxied: http://localhost/api     (via Nginx)
MinIO UI:   http://localhost:9001     (storage console)
```

### Commands
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend        # Backend logs
docker-compose logs -f frontend       # Frontend logs
docker-compose logs -f nginx          # Nginx logs

# Monitor services
docker-compose ps

# Shell into container
docker-compose exec backend bash
docker-compose exec frontend bash

# Rebuild images
docker-compose build

# Full reset (removes volumes)
docker-compose down -v
```

---

## Architecture

```
┌────────────────────────────────────────┐
│ Browser                                 │
│ http://localhost                        │
└────────────┬─────────────────────────┘
             │
             ▼
    ┌───────────────────┐
    │ Nginx (port 80)   │
    │ ├─ /      → frontend:3000
    │ ├─ /api   → backend:8000
    │ └─ /ws    → backend:8000
    └─────┬───────┬─────┘
          │       │
    ┌─────▼─┐   ┌─▼──────────┐
    │       │   │            │
    │       │   │            │
    ▼       ▼   ▼            ▼
 Frontend  │  Backend     Workers
 (Next.js) │  (FastAPI)   (Celery)
 3000      │  8000
           │
    ┌──────┴────────────┬──────────┐
    │                   │          │
    ▼                   ▼          ▼
 PostgreSQL           Redis      MinIO
 5433                 6380        9000
```

---

## Network Communication

All services on `syauai-network`:
- Containers reach each other by service name: `postgres`, `redis`, `backend`, etc.
- Browser accesses through Nginx on port 80

**Example:**
- Frontend (in container) calls: `http://backend:8000/api`
- Nginx proxies: `/api` → `http://backend:8000`
- Browser sees: `http://localhost/api`

---

## Configuration

### Environment Variables

**Backend** (from `.env` file):
```env
DATABASE_URL=postgresql://syau:syau@postgres:5432/syau
REDIS_URL=redis://redis:6379/0
API_KEY_DEV=syauai_dev_key_12345
API_KEY_TEST=syauai_test_key_67890
```

**Frontend** (from `frontend/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost/api
NEXT_PUBLIC_WS_URL=ws://localhost/ws
NEXT_PUBLIC_API_KEY=syauai_dev_key_12345
```

---

## Development Workflow

### 1. Make Changes
Edit files in `backend/`, `frontend/`, etc.
- Backend changes → auto-reload in container
- Frontend changes → auto-reload (Next.js hot reload)

### 2. View Logs
```bash
docker-compose logs -f
```

### 3. Test Changes
- Frontend: http://localhost
- Backend: http://localhost/api

### 4. Stop Services
```bash
docker-compose down
```

---

## Common Tasks

### Create a Database Migration
```bash
docker-compose exec backend alembic revision --autogenerate -m "Description"
```

### Run Database Migrations
```bash
docker-compose exec backend alembic upgrade head
```

### Connect to Database
```bash
docker-compose exec postgres psql -U syau -d syau
```

### Clear Cache
```bash
docker-compose exec redis redis-cli FLUSHDB
```

### View MinIO Files
```
http://localhost:9001
Username: changeme
Password: changeme_also
```

---

## Troubleshooting

### Port Already in Use
If port 80 is in use, modify `docker-compose.yml`:
```yaml
nginx:
  ports:
    - "8080:80"  # Changed from "80:80"
```
Then access: `http://localhost:8080`

### Services Won't Start
Check logs:
```bash
docker-compose logs backend
```

### Database Connection Error
Ensure postgres is healthy:
```bash
docker-compose ps postgres
```

Should show `(healthy)` status.

### Frontend Not Hot-Reloading
Ensure these are set in `docker-compose.yml`:
```yaml
environment:
  WATCHPACK_POLLING: "true"
  CHOKIDAR_USEPOLLING: "true"
```

### Clear Everything and Start Fresh
```bash
docker-compose down -v
docker-compose up -d
```

---

## Performance Tips

### Reduce Docker Compose Overhead
Remove unused services in `docker-compose.yml`:
- Comment out worker services if you don't need them
- Reduces startup time and resource usage

### Faster Builds
```bash
docker-compose build --parallel
```

### Monitor Resources
```bash
docker stats
```

---

## Production Deployment

For remote server (like 202.51.2.50):
1. Skip hot-reload settings (remove WATCHPACK_POLLING)
2. Use production Next.js build: `npm run build && npm run start`
3. Set environment variables for remote server addresses
4. Use production docker-compose file with smaller resources

See `DEPLOYMENT_SUMMARY.md` for remote deployment.

---

## Ports Reference

| Port | Service | Usage |
|------|---------|-------|
| 80 | Nginx | Frontend + API proxy |
| 3000 | Frontend | Direct Next.js access |
| 8000 | Backend | Direct API access |
| 5433 | PostgreSQL | Database |
| 6380 | Redis | Cache/Queue |
| 9000 | MinIO | Object storage API |
| 9001 | MinIO | Management UI |

---

## Status Check

All services healthy:
```bash
docker-compose ps
```

Expected output:
```
NAMES                    STATUS           
syau-ai-backend-1        Up (healthy)
syau-ai-frontend-1       Up
syau-ai-postgres-1       Up (healthy)
syau-ai-redis-1          Up (healthy)
syau-ai-minio-1          Up (healthy)
syau-ai-nginx-1          Up
syau-ai-worker-*         Up (4 total)
```

---

**Everything running in Docker locally!** 🐳
