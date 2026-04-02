"use client";

import { ReactNode, useState, useEffect } from "react";
import { AuthErrorDisplay } from "@/hooks/useAuthError";

/**
 * Provider component that handles auth errors globally
 * Wrap your app with this to catch and display auth failures
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [authError, setAuthError] = useState<string | null>(null);

  // Listen for auth errors from window events
  useEffect(() => {
    const handleAuthError = (event: CustomEvent) => {
      setAuthError(event.detail.message);
    };

    window.addEventListener("auth:error", handleAuthError as EventListener);
    return () => window.removeEventListener("auth:error", handleAuthError as EventListener);
  }, []);

  return (
    <>
      {children}
      <AuthErrorDisplay error={authError} onDismiss={() => setAuthError(null)} />
    </>
  );
}

/**
 * Dispatch auth error event globally
 * Use this in API error handlers: dispatchAuthError("Invalid API key")
 */
export function dispatchAuthError(message: string) {
  window.dispatchEvent(
    new CustomEvent("auth:error", {
      detail: { message },
    })
  );
}
