#!/bin/bash
# Deploy the private GPU inference API to the model server.
# Usage: ./infra/scripts/deploy-gpu-api.sh

set -euo pipefail

GPU_SERVER="202.51.2.50"
GPU_SSH_PORT="41447"
GPU_USER="${GPU_USER:-root}"
REMOTE_DIR="/opt/syauai"

echo "==> Syncing gpu_server/ to GPU host..."
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.env' \
  -e "ssh -p ${GPU_SSH_PORT}" \
  ./gpu_server/ ${GPU_USER}@${GPU_SERVER}:${REMOTE_DIR}/gpu_server/

if [ -f ./gpu_server/.env ]; then
  echo "==> Syncing gpu server env file..."
  rsync -avz -e "ssh -p ${GPU_SSH_PORT}" \
    ./gpu_server/.env ${GPU_USER}@${GPU_SERVER}:${REMOTE_DIR}/gpu_server/.env
else
  echo "==> No local gpu_server/.env found; leaving remote .env untouched."
fi

echo "==> Installing GPU API dependencies..."
ssh -p ${GPU_SSH_PORT} ${GPU_USER}@${GPU_SERVER} \
  "cd ${REMOTE_DIR}/gpu_server && python3 -m pip install -r requirements.txt"

echo "==> GPU API files deployed."
