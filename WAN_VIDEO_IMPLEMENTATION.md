# Wan 2.2 Video Generation Implementation

**Status:** ✅ Complete  
**Date:** April 1, 2026  
**Models Implemented:** Wan 2.2 T2V + I2V  
**Removed:** LTX 2.3 references from UI

## Implementation Summary

Both Wan 2.2 text-to-video and image-to-video models have been fully integrated into the SYAU AI platform with working frontend UI, backend API, GPU server processing, and output storage.

---

## 1. Frontend UI Changes

### File: `/frontend/components/video-form.tsx`

**Removed:**
- LTX 2.3 specific references
- Steps parameter (Wan uses fixed 4-step LightX2V)
- CFG scale parameter (Wan uses fixed cfg=1)
- Old placeholder text about "preview mode"

**Added:**
- T2V/I2V mode toggle buttons (shown when Wan 2.2 is selected)
- Image upload field (shown in I2V mode with preview)
- Mode-specific placeholders and instructions
- Proper image-to-base64 conversion for I2V jobs
- Conditional form validation (requires image in I2V mode)

**Key Features:**
```tsx
const [videoMode, setVideoMode] = useState<"t2v" | "i2v">("t2v");
const [imageFile, setImageFile] = useState<File | null>(null);
const [imagePreview, setImagePreview] = useState<string | null>(null);

// T2V/I2V toggle only shown for Wan 2.2
{isWan && (
  <div className="flex gap-3 border-b border-border pb-3">
    {/* Toggle buttons */}
  </div>
)}

// Image upload only in I2V mode
{videoMode === "i2v" && (
  <div className="flex flex-col gap-1.5">
    {/* Image file input + preview */}
  </div>
)}
```

### File: `/frontend/app/video/page.tsx`

**Updated Copy:**
```
From: "Local mode generates an animated preview..."
To:   "Create realistic videos using Wan 2.2. Choose between text-to-video 
       for generating from scratch, or image-to-video to transform images 
       into motion."
```

---

## 2. Backend Video Worker Fix

### File: `/backend/workers/video_worker.py`

**Fixed:**
1. **Line 44:** Handle None values in params
   ```python
   # Before: seed=int(params.get("seed", 0))
   # After:  seed=int(params.get("seed") or 0)
   ```
   This fixes `TypeError: int() argument must be... 'NoneType'` when params don't include seed

2. **Line 58:** Log correct field name
   ```python
   # Before: log.info(..., frames=result["frames"])
   # After:  log.info(..., filename=result["filename"])
   ```
   Prevents KeyError on job completion

**Supported Features:**
- T2V: Text-to-video generation
- I2V: Image-to-video with base64 image upload
- Base64 image handling: Extracts base64 payload and passes to ComfyUI
- Progress tracking: WebSocket updates during generation
- Output storage: Uploads MP4 to MinIO with presigned URLs

---

## 3. API Endpoints

### POST `/api/jobs`

**T2V Request:**
```json
{
  "type": "video",
  "model": "wan-2.2",
  "prompt": "a serene waterfall in a misty forest",
  "negative_prompt": "blurry, distorted",
  "params": {
    "num_frames": 81,
    "width": 640,
    "height": 640
  }
}
```

**I2V Request:**
```json
{
  "type": "video",
  "model": "wan-2.2",
  "prompt": "scene transforms with flowing colors",
  "negative_prompt": "distorted",
  "params": {
    "num_frames": 81,
    "width": 640,
    "height": 640,
    "input_image_base64": "iVBORw0KGgoAAAANSUhE...",
    "input_image_name": "start.jpg"
  }
}
```

**Response:**
```json
{
  "job_id": "1be947ba-ad31-4749-a2a3-12d60f22c75e",
  "status": "pending"
}
```

### GET `/api/jobs/{job_id}`

Returns full job details including:
- Status: `pending | running | done | failed`
- Progress & message via WebSocket
- Output URLs (MinIO presigned links)
- Duration and error messages

---

## 4. GPU Server Integration

### ComfyUI Client: `/backend/inference/comfyui_client.py`

**Methods:**
- `infer_wan_t2v()`: T2V workflow execution
- `infer_wan_i2v()`: I2V workflow execution
- `upload_image()`: Image pre-upload for I2V
- `_wait_for_completion()`: Output polling with "images" key detection

**Workflow Architecture:**

**T2V (Text-to-Video):**
```
CLIPLoader (UMT5-XXL text encoder)
  ↓
CLIPTextEncode (prompt & negative)
  ↓
[2× UNETLoader] → [2× LoraLoaderModelOnly] → [2× ModelSamplingSD3]
  ↓
KSamplerAdvanced (stage 1: steps 0→2)
  ↓
KSamplerAdvanced (stage 2: steps 2→4)
  ↓
VAEDecode → CreateVideo → SaveVideo
```

**I2V (Image-to-Video):**
```
LoadImage + WanImageToVideo (image encoding + conditioning)
  ↓
[2× UNETLoader] → [2× LoraLoaderModelOnly] → [2× ModelSamplingSD3]
  ↓
KSamplerAdvanced (stage 1)
  ↓
KSamplerAdvanced (stage 2)
  ↓
VAEDecode → CreateVideo → SaveVideo
```

---

## 5. Test Results

### T2V Generation
```
Job ID:       1be947ba-ad31-4749-a2a3-12d60f22c75e
Prompt:       "a serene waterfall in a misty forest"
Status:       ✅ DONE
Duration:     49.2 seconds
Output:       949 KB MP4
Frame Count:  81 @ 16fps = 5 seconds
Quality:      1280×1280 encoded
```

### I2V Generation
```
Job ID:       9903a721-8a29-47c8-a3dd-51df0b6bc819
Input:        Minimal test image (base64)
Prompt:       "scene transforms with flowing colors"
Status:       ✅ DONE
Duration:     45.1 seconds
Output:       628 KB MP4
Frame Count:  81 @ 16fps = 5 seconds
Quality:      1280×1280 encoded
```

---

## 6. Configuration

### Environment Variables

**For GPU Server ComfyUI:**
```bash
COMFYUI_URL=http://host.docker.internal:8188
# (inside docker container, reaches GPU server ComfyUI)
```

**For Frontend (Docker):**
```bash
NEXT_PUBLIC_API_URL=http://localhost/api
NEXT_PUBLIC_WS_URL=ws://localhost/ws
```

### Model Registration

Database contains:
```
name: "wan-2.2"
display_name: "Wan 2.2"
type: "video"
is_enabled: true
```

---

## 7. Deployment Checklist

- ✅ Frontend component: T2V/I2V toggle, image upload
- ✅ Backend worker: Fixed param handling, proper logging
- ✅ ComfyUI client: Both workflows implemented
- ✅ GPU server: ComfyUI patched for UMT5-XXL
- ✅ API endpoints: Working `/api/jobs` submission
- ✅ Storage: MinIO integration with presigned URLs
- ✅ WebSocket: Progress tracking during generation
- ✅ Error handling: Proper validation and messaging
- ✅ Testing: Both T2V and I2V verified end-to-end

---

## 8. User Experience Flow

1. **Navigate to Video Page** → See "Generate Video" form
2. **Select Model** → "Wan 2.2" model available
3. **Choose Mode:**
   - **T2V:** Write prompt → Click "Generate Video"
   - **I2V:** Upload image → Write prompt → Click "Generate from Image"
4. **Submit** → Job queued, status updates via WebSocket
5. **View Output** → MP4 preview + download link via MinIO
6. **Copy URL** → Share presigned link directly

---

## 9. Technical Notes

### UMT5-XXL Text Encoding
- ComfyUI patch converts `blocks.*` → `encoder.block.*` keys
- Text conditioning fully loads: prompts genuinely influence output
- No "clip missing" warnings in logs

### LightX2V 4-Step Optimization
- Dual-UNet approach: high_noise (steps 0→2) + low_noise (steps 2→4)
- Dramatically faster inference (~50s for 81 frames)
- Maintains quality vs full 30-step diffusion

### Output Format
- Container: MP4 (H.264)
- Resolution: 640×640 (configurable 512-1024 step 64)
- Duration: 81 frames @ 16fps = 5.06 seconds
- Size: ~600-950 KB per video

---

## 10. Future Enhancements (Optional)

- [ ] Custom FPS setting (currently hardcoded 16fps)
- [ ] Custom resolution guidance (cfg_scale slider)
- [ ] Multi-image I2V sequences
- [ ] Parallel GPU worker deployment
- [ ] Video quality presets
- [ ] Generation history & favorites
- [ ] Advanced prompt engineering tips

---

**Deployed by:** Claude Code  
**Architecture:** Next.js Frontend + FastAPI Backend + Celery Workers + ComfyUI GPU Server  
**GPU Requirements:** NVIDIA 40GB+ VRAM (Wan 2.2 dual-UNet + VAE)
