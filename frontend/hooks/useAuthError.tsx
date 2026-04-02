/**
 * Hook to handle authentication errors globally
 * Shows a user-friendly message when API returns 403 Forbidden
 */

import { useEffect, useState } from "react";
import { AuthError } from "@/lib/api";

export function useAuthError() {
  const [authError, setAuthError] = useState<string | null>(null);

  const handleError = (error: Error) => {
    if (error instanceof AuthError) {
      setAuthError(
        "Authentication failed. Please check your API key configuration. " +
        "See docs/API_AUTHENTICATION.md for setup instructions."
      );
      return true;
    }
    return false;
  };

  const clearError = () => setAuthError(null);

  return {
    authError,
    handleError,
    clearError,
  };
}

/**
 * Global error boundary for auth issues
 */
export function AuthErrorDisplay({ error, onDismiss }: { error: string | null; onDismiss: () => void }) {
  if (!error) return null;

  return (
    <div className="fixed top-4 right-4 max-w-sm bg-red-950 border border-red-800 rounded-lg p-4 z-50">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-red-400 mb-1">API Authentication Error</h3>
          <p className="text-sm text-red-300">{error}</p>
          <p className="text-xs text-red-400 mt-2">
            Check: backend/.env (API keys) and frontend/.env.local (NEXT_PUBLIC_API_KEY)
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="text-red-400 hover:text-red-300 ml-2"
          aria-label="Close"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
