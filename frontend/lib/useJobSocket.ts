"use client";
import { useEffect, useRef, useState } from "react";
import type { Job } from "./api";

export type JobUpdate = Partial<Job> & {
  job_id?: string;
  progress?: number;
  message?: string;
};

function getWebSocketUrl(path: string): string {
  if (typeof window === "undefined") return `ws://localhost/ws${path}`;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const wsBase = (process.env.NEXT_PUBLIC_WS_URL ?? "/ws").replace(/\/$/, "");
  return `${protocol}//${host}${wsBase}${path}`;
}

export function useJobSocket(jobId: string | null, onUpdate: (update: JobUpdate) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    const ws = new WebSocket(getWebSocketUrl(`/jobs/${jobId}`));
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (event) => {
      try {
        const data: JobUpdate = JSON.parse(event.data);
        onUpdate(data);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    return () => {
      ws.close();
      wsRef.current = null;
      setConnected(false);
    };
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  return { connected };
}
