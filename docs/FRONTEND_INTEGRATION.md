# Frontend API Authentication Integration

**Date:** April 2, 2026  
**Status:** ✅ Implemented (Phase 1 Stability)

---

## Overview

The frontend has been updated to automatically include API key authentication in all API requests. This guide explains how the integration works and how to customize it.

---

## Setup (3 Steps)

### Step 1: Create `.env.local`

Copy the template and customize:

```bash
cp frontend/.env.local.example frontend/.env.local
```

**`.env.local` content:**
```env
NEXT_PUBLIC_API_URL=http://localhost/api
NEXT_PUBLIC_WS_URL=ws://localhost/ws
NEXT_PUBLIC_API_KEY=syauai_dev_key_12345
```

**Options for NEXT_PUBLIC_API_KEY:**
- `syauai_dev_key_12345` — Dev user (local development)
- `syauai_test_key_67890` — Test user (for testing)

### Step 2: Wrap App with AuthProvider (Optional)

For global auth error handling, wrap your app root:

**`app/layout.tsx`:**
```tsx
import { AuthProvider } from "@/components/AuthProvider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
```

This shows a red error banner if any API call returns 403.

### Step 3: Restart Frontend Dev Server

```bash
npm run dev
```

Frontend will automatically read `NEXT_PUBLIC_API_KEY` from `.env.local` and add it to all requests.

---

## How It Works

### Automatic Authorization Header

Every API call now includes:
```
Authorization: Bearer {NEXT_PUBLIC_API_KEY}
```

**Example:**
```typescript
// Before (no auth)
const response = await fetch('/api/jobs', { method: 'GET' });

// After (automatic auth)
const response = await fetch('/api/jobs', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer syauai_dev_key_12345'
  }
});
```

### Error Handling

**Modified File:** `lib/api.ts`

```typescript
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // ... automatically adds Authorization header ...
  
  if (!res.ok) {
    if (res.status === 403) {
      throw new AuthError(`API Authentication Failed: ${body}`, 403);
    }
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}
```

**Catch auth errors in components:**
```typescript
import { AuthError } from "@/lib/api";

try {
  await api.createJob(jobData);
} catch (error) {
  if (error instanceof AuthError) {
    console.error("Auth failed:", error.message);
    // Show user-friendly message
  }
}
```

### Optional: Global Auth Error Display

Use the `AuthProvider` to catch ALL auth errors automatically:

```typescript
import { dispatchAuthError } from "@/components/AuthProvider";

// In any component, dispatch a global auth error:
try {
  await api.createJob(jobData);
} catch (error) {
  if (error instanceof AuthError) {
    dispatchAuthError("Your API key is invalid. Please check your configuration.");
  }
}
```

A red banner will appear at the top-right of the page.

---

## Files Changed

### Created Files

1. **`frontend/.env.local`** — Local environment variables (API key)
2. **`frontend/.env.local.example`** — Template for .env.local
3. **`frontend/hooks/useAuthError.ts`** — Hook for handling auth errors
4. **`frontend/components/AuthProvider.tsx`** — Global error boundary

### Modified Files

1. **`frontend/lib/api.ts`**
   - Added `AuthError` class
   - Updated `request()` function to include Bearer token
   - Special handling for 403 Forbidden responses
   - Updated `cancelJob()` and `deleteProject()` to include auth headers

---

## Troubleshooting

### Error: "API Authentication Failed"

**Cause:** API key in `.env.local` is invalid or missing

**Solution:**
1. Check `frontend/.env.local` exists
2. Verify `NEXT_PUBLIC_API_KEY` matches backend (see `backend/.env`)
3. Restart dev server: `npm run dev`

### Error: "Missing Authorization header"

**Cause:** Frontend stopped including auth header (shouldn't happen)

**Solution:**
1. Check `lib/api.ts` has the Bearer token logic
2. Check `.env.local` has `NEXT_PUBLIC_API_KEY`
3. Verify Next.js rebuilt: `rm -rf .next && npm run dev`

### All API calls fail with 403

**Possible causes:**
- Wrong API key in `.env.local`
- API key not registered in `backend/.env`
- Backend restarted but frontend wasn't

**Solution:**
1. Verify both `.env` files match:
   - `backend/.env`: `API_KEY_DEV=syauai_dev_key_12345`
   - `frontend/.env.local`: `NEXT_PUBLIC_API_KEY=syauai_dev_key_12345`
2. Restart both:
   ```bash
   docker-compose restart backend
   npm run dev
   ```

---

## Multi-User Testing

To test with different users:

### Test with Dev User

1. Set in `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_KEY=syauai_dev_key_12345
   ```
2. Refresh browser
3. Create jobs → they appear under "dev-user"

### Test with Test User

1. Set in `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_KEY=syauai_test_key_67890
   ```
2. Refresh browser
3. Create jobs → they appear under "test-user"
4. Dev user's jobs are hidden (403 Forbidden)

### Verify User Isolation

1. Open two browser tabs/windows
2. Tab 1: Use dev key → create job → note job_id
3. Tab 2: Use test key → try to access that job → 403 error

---

## Advanced: Custom API Keys

To add a new user:

### Backend (`backend/.env`):
```env
API_KEY_ENABLED=true
API_KEY_DEV=syauai_dev_key_12345
API_KEY_TEST=syauai_test_key_67890
API_KEY_ALICE=alice_custom_secret_xyz  # New user
```

### Backend (`backend/core/security.py`):
```python
VALID_API_KEYS: Dict[str, str] = {
    settings.api_key_dev: "dev-user",
    settings.api_key_test: "test-user",
    settings.api_key_alice: "alice",  # Add this
}
```

### Frontend (choose one):
```env
NEXT_PUBLIC_API_KEY=alice_custom_secret_xyz
```

### Restart both:
```bash
docker-compose restart backend
npm run dev
```

---

## Next Steps

1. ✅ Frontend automatically sends auth header
2. ✅ Error handling shows 403 errors
3. ✅ User isolation prevents cross-user access
4. ⏳ (Phase 2) Implement user login UI
5. ⏳ (Phase 2) Add API key rotation
6. ⏳ (Phase 2) Rate limiting per user

---

## Testing Checklist

- [ ] Frontend loads without errors
- [ ] Create job with dev key → succeeds
- [ ] Create job with test key → succeeds
- [ ] Dev user sees only own jobs
- [ ] Test user sees only own jobs
- [ ] Try to access other user's job → 403 error
- [ ] Auth error banner appears on 403
- [ ] Change `.env.local` API key → user changes
- [ ] Delete `.env.local` → auth error (no key provided)

---

**Generated by:** Claude Code  
**Last Updated:** April 2, 2026, 23:50 UTC
