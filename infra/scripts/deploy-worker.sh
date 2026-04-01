#!/bin/bash
# Deploy workers to GPU server
# Usage: ./infra/scripts/deploy-worker.sh

set -euo pipefail

GPU_SERVER="202.51.2.50"
GPU_SSH_PORT="41447"
GPU_USER="${GPU_USER:-root}"
REMOTE_DIR="/opt/syauai"

echo "==> Syncing code to GPU server..."
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.env' --exclude='.docker-data' \
  -e "ssh -p ${GPU_SSH_PORT}" \
  ./backend/ ${GPU_USER}@${GPU_SERVER}:${REMOTE_DIR}/backend/

echo "==> Syncing .env to GPU server..."
rsync -avz -e "ssh -p ${GPU_SSH_PORT}" \
  ./.env ${GPU_USER}@${GPU_SERVER}:${REMOTE_DIR}/.env

echo "==> Installing Python dependencies on GPU server..."
ssh -p ${GPU_SSH_PORT} ${GPU_USER}@${GPU_SERVER} \
  "cd ${REMOTE_DIR} && pip install -r backend/requirements.txt --quiet"

echo "==> Restarting Celery workers..."
ssh -p ${GPU_SSH_PORT} ${GPU_USER}@${GPU_SERVER} \
  "cd ${REMOTE_DIR} && docker compose -f docker-compose.worker.yml up -d --build"

echo "==> Workers deployed."
