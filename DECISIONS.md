# Decisions

## No ComfyUI by default
Original plan avoided ComfyUI as the main inference gateway.
Reason: cleaner API architecture, fewer open ports, and easier engineering ownership.
Current caveat: hard video runtimes like true LTX-2.3 may justify revisiting this for that model family only.

## Handlers are synchronous
Celery runs in synchronous threads. Async handlers cause event loop conflicts.
All handler methods (load, unload, infer) use regular `def`, not `async def`.

## Workers run on GPU server, API runs on VPS
Workers need the GPU. The API needs none. Separating them means the cheap VPS
can scale independently and a GPU crash does not take down the whole API.
In local development, the GPU API is reached through an SSH tunnel from the Windows host.

## Output keys stored, not presigned URLs
Presigned URLs expire. Storing the MinIO object key means URLs can be
regenerated anytime. Generate at read time with 1-hour expiry.

## Phase 1 has no auth
Getting inference working is the priority. Auth, payments, and credits
are Phase 2. Do not build them during Phase 1.

## qwen-image-2512 should prefer safe offload over forced full CUDA
The qwen-image-2512 model is large enough to cause device-placement or OOM issues on the 44GB GPU.
The current remote GPU API path works with CPU offload and warm model reuse.
It is slower, but stable enough for current development.

## Treat true LTX-2.3 separately from temporary Diffusers LTX experiments
The user wants true LTX-2.3 from raw checkpoint weights in `/data/models/ltx-2.3`.
A temporary Diffusers-based LTX-Video integration was made to get something running, but it is not the same thing and should not be mislabeled.
