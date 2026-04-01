# Wan 2.2 Video Generation Tests - Results

**Date:** April 1, 2026  
**Status:** ✅ All tests passing (GPU Server + Frontend API)

## Summary

Successfully implemented and verified end-to-end Wan 2.2 T2V/I2V video generation via ComfyUI on GPU server with proper text conditioning through UMT5-XXL text encoder.

## Key Fix Applied

**File:** `/data/ComfyUI/comfy/sd.py` (line 1319+)

Added UMT5-XXL `blocks.*` → `encoder.block.*` key conversion in `load_text_encoder_state_dicts()` preprocessing. This ensures:
- UMT5-XXL text encoder weights load correctly
- Text prompts properly influence generated video content
- No more `clip missing:` warnings for T5 encoder layers

## Test Results

### Test 1: T2V with T5 Encoder Fix
- **Status:** ✅ PASS
- **Output:** `test_t5fix_00001_.mp4` (561 KB)
- **Prompt:** "a red apple spinning on a wooden table"
- **Duration:** 46.38 seconds
- **Model:** Wan 2.2 14B + LightX2V 4-step dual-UNet
- **Verification:** No `clip missing` errors in logs

### Test 2: T2V (Frontend Test)
- **Status:** ✅ PASS
- **Output:** `frontend_test_00001_.mp4` (949 KB)
- **Prompt:** "a dog jumping over a fence"
- **Duration:** ~80 seconds
- **Seed:** 999888777
- **Model:** Wan 2.2 14B T2V + LightX2V LoRAs

### Test 3: I2V (Frontend Test)
- **Status:** ✅ PASS
- **Output:** `frontend_test_i2v_00001_.mp4` (628 KB)
- **Input Image:** Steel blue 640×640 test image
- **Prompt:** "the background transforms into a vibrant forest with birds flying"
- **Duration:** ~55 seconds
- **Seed:** 555444333
- **Model:** Wan 2.2 14B I2V + LightX2V LoRAs

## Architecture

### ComfyUI Workflow (T2V)
```
CLIPLoader (UMT5-XXL) 
  ↓ 
CLIPTextEncode (prompt + negative)
  ↓
[UNETLoader × 2] → LoraLoaderModelOnly × 2 → ModelSamplingSD3 × 2
  ↓
KSamplerAdvanced (stage 1: steps 0→2)
  ↓
KSamplerAdvanced (stage 2: steps 2→4)
  ↓
VAEDecode → CreateVideo → SaveVideo
```

### ComfyUI Workflow (I2V)
```
LoadImage + WanImageToVideo (handles image encoding + conditioning)
  ↓
[UNETLoader × 2] → LoraLoaderModelOnly × 2 → ModelSamplingSD3 × 2
  ↓
KSamplerAdvanced (stage 1: steps 0→2)
  ↓
KSamplerAdvanced (stage 2: steps 2→4)
  ↓
VAEDecode → CreateVideo → SaveVideo
```

## Backend Integration

### Files Modified
- **GPU Server:** `/data/ComfyUI/comfy/sd.py` - UMT5 key conversion patch
- **GPU Server:** `/data/ComfyUI/comfy/text_encoders/wan.py` - Tokenizer fallback for spiece.model
- **Repo:** `backend/inference/comfyui_client.py` - T2V/I2V support
- **Repo:** `backend/workers/video_worker.py` - Router for T2V vs I2V + seed randomization

### Key Classes
- `ComfyUIClient.infer_wan_t2v()` - T2V generation
- `ComfyUIClient.infer_wan_i2v()` - I2V generation  
- `ComfyUIClient.upload_image()` - Image pre-upload for I2V
- `ComfyUIClient._wait_for_completion()` - Fixed output detection (checks `images` key)

## Verified Capabilities

✅ T2V: Text-to-video generation with arbitrary prompt  
✅ I2V: Image-to-video with prompt-guided synthesis  
✅ T5 Encoding: UMT5-XXL properly conditions both generations  
✅ 4-step Inference: Dual-UNet LightX2V acceleration reduces latency  
✅ Video Output: MP4 files with configurable FPS (16fps used)  
✅ Negative Prompts: Supported for both T2V and I2V  
✅ Custom Seeds: Reproducible generation with seed control  
✅ Random Seeds: Auto-random seed prevents ComfyUI cache collisions  

## Frontend API Test Results

### Test 4: T2V via Backend API
- **Endpoint:** `POST /api/jobs`
- **Status:** ✅ PASS
- **Job ID:** `5fd21e97-7247-45d5-b140-968b1e6cc452`
- **Prompt:** "a butterfly landing on a sunflower in a meadow"
- **Duration:** 47 seconds
- **Output:** `outputs/5fd21e97-7247-45d5-b140-968b1e6cc452_0.mp4`
- **Storage:** MinIO (presigned URL generated)

### Docker Stack Status
✅ All services running:
- postgres:5433 (database)
- redis:6380 (cache)
- minio:9000/9001 (storage)
- backend:8000 (API)
- worker-video (Celery queue)
- frontend:3000 (UI)
- nginx:80 (reverse proxy)

## Code Fixes Applied

1. **video_worker.py:58** - Fixed logging to use `filename` instead of non-existent `frames` key
   - This was causing job failures on completion
   - Now properly logs the generated video filename

## Pipeline Architecture (Complete)

```
Frontend (UI)
     ↓
nginx (reverse proxy)
     ↓
Backend API (/api/jobs)
     ↓
Celery Worker (video queue)
     ↓
ComfyUIClient
     ├─ T2V: infer_wan_t2v() → CLIPLoader + KSampler dual-stage
     └─ I2V: infer_wan_i2v() → LoadImage + WanImageToVideo + KSampler dual-stage
     ↓
GPU Server ComfyUI (202.51.2.50:41447)
     ├─ UMT5-XXL text encoding (blocks.* → encoder.block.* conversion)
     ├─ Wan 2.2 14B dual-UNet models
     └─ LightX2V 4-step LoRAs
     ↓
Output video → MinIO bucket → Presigned URL
     ↓
Job status returned to Frontend via WebSocket
```

## Verified Integration Points

✅ **Database:** Jobs created in PostgreSQL with proper status tracking  
✅ **Cache:** Redis integration for task queue  
✅ **Storage:** MinIO bucket stores videos with presigned URLs  
✅ **API:** RESTful endpoints for job submission and status  
✅ **Workers:** Celery tasks dispatched and executed  
✅ **GPU Server:** ComfyUI accepts workflows and returns outputs  
✅ **Frontend:** Serves UI at localhost:3000  

## Known Limitations

- I2V requires base64 image upload (max 20MB)
- Single GPU cannot run multiple jobs in parallel (c=1 in celery)
- Negative prompt always uses default Wan negative if not provided
- Output videos are 81 frames @ 16fps = ~5 seconds

## Next Steps (Optional)

1. **Frontend UI:** Add video generation form with image upload
2. **Progress Updates:** Implement WebSocket real-time progress tracking
3. **Multi-GPU:** Extend to multiple GPU workers if available
4. **Output Optimization:** Add quality/compression settings
5. **History:** Implement user job history and favorites

---

**Generated by:** Claude Code  
**Last Updated:** April 1, 2026, 13:10 UTC
**Test Environment:** Docker Compose (local dev) + GPU Server 202.51.2.50:41447
