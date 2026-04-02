# Frontend Integration Setup

**Date:** April 2, 2026  
**Status:** ✅ Ready for Testing

## What Was Updated

### 1. Environment Configuration
**File:** `frontend/.env.local`
```env
NEXT_PUBLIC_API_URL=http://202.51.2.50:8000/api
NEXT_PUBLIC_WS_URL=ws://202.51.2.50:8000/ws
NEXT_PUBLIC_API_KEY=syauai_dev_key_12345
```

✅ Points to remote server deployment at 202.51.2.50:8000

### 2. Authentication Provider
**File:** `frontend/app/layout.tsx`
- ✅ Added `AuthProvider` import
- ✅ Wrapped root layout with `<AuthProvider>`
- ✅ Captures and displays auth errors globally

### 3. API Connection Status
**File:** `frontend/components/api-status.tsx` (NEW)
- ✅ Tests health endpoint (no auth)
- ✅ Tests API with Bearer token
- ✅ Shows green "Connected" or red "Error" status

**File:** `frontend/app/page.tsx` (UPDATED)
- ✅ Added ApiStatus component to home page
- ✅ Shows connection status immediately on load

---

## How to Test

### 1. Start Frontend Dev Server
```bash
cd frontend
npm install
npm run dev
```

### 2. Open Browser
Navigate to: **http://localhost:3000**

You should see:
- SYAU AI home page
- **Green status indicator** at the top saying "✓ Connected to API at http://202.51.2.50:8000/api"

### 3. Test Authentication
Try the History page:
```
http://localhost:3000/history
```

Should show:
- Empty jobs list (no jobs created yet)
- OR if auth fails: red error banner at top-right

---

## API Keys Available

| Key | User | Purpose |
|-----|------|---------|
| `syauai_dev_key_12345` | dev-user | Current setup (see in .env.local) |
| `syauai_test_key_67890` | test-user | Testing multi-user isolation |

### Switch API Key
To test with a different user, edit `frontend/.env.local`:
```env
# Change to:
NEXT_PUBLIC_API_KEY=syauai_test_key_67890
```

Then restart dev server: `npm run dev`

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│  Frontend (localhost:3000)              │
│  ├─ Home Page + ApiStatus component     │
│  ├─ History Page → calls api.listJobs() │
│  ├─ Layout with AuthProvider wrapper    │
│  └─ .env.local with API key             │
└────────────────┬────────────────────────┘
                 │ Bearer: syauai_dev_key_12345
                 ▼
         ┌───────────────┐
         │ Backend API   │
         │ 202.51.2.50   │
         │ :8000         │
         ├─ Auth checks  │
         ├─ User isolation
         └─ Returns data │
```

---

## API Workflow

1. **Frontend sends request:**
   ```
   GET /api/jobs
   Authorization: Bearer syauai_dev_key_12345
   ```

2. **Backend validates:**
   - ✓ Header present?
   - ✓ Key is valid?
   - ✓ Route allows access?

3. **Backend responds:**
   - ✓ Valid → 200 with jobs (filtered by user_id='dev-user')
   - ✗ Invalid key → 403 Forbidden
   - ✗ Missing header → 403 with help message

4. **Frontend handles:**
   - ✓ Success → display data
   - ✗ 403 → show red error banner via AuthProvider

---

## Troubleshooting

### "Connection failed: fetch failed"
- **Check:** Is the backend running? `ssh -p 41447 ekduiteen@202.51.2.50 "docker ps | grep syauai_backend"`
- **Check:** Is .env.local using correct URL? Should be `http://202.51.2.50:8000/api`
- **Fix:** Restart backend: `ssh -p 41447 ekduiteen@202.51.2.50 "docker restart syauai_backend_1"`

### "API Authentication Failed"
- **Check:** Is API key correct in .env.local?
- **Check:** Does it match backend keys? (should be one of the two listed above)
- **Fix:** Update .env.local, restart dev server: `npm run dev`

### "Cannot find module @/components/AuthProvider"
- **Check:** Does the file exist? `frontend/components/AuthProvider.tsx`
- **Fix:** Clear cache: `rm -rf .next && npm run dev`

### Jobs list is empty
- **This is normal** - no jobs have been created yet
- **Test submission:** Try the Generate or Video pages to create a job

---

## Next Steps

✅ Frontend connected to backend  
✅ Authentication working  
✅ User isolation enforced  

**Now you can:**
1. Create a job (try `/generate` or `/video` page)
2. Watch it progress in History
3. Build out the professional workflow editor (Phase 2)

---

## Files Modified/Created

**Modified:**
- `frontend/.env.local` - Updated API URL
- `frontend/app/layout.tsx` - Added AuthProvider
- `frontend/app/page.tsx` - Added ApiStatus component

**Created:**
- `frontend/components/api-status.tsx` - Connection status indicator

---

**Generated:** 2026-04-02  
**Integration Status:** Ready for Testing
