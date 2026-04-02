"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function ApiStatus() {
  const [status, setStatus] = useState<"loading" | "connected" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const testConnection = async () => {
      try {
        // Test the health endpoint (no auth required)
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL?.replace("/api", "")}/health`);
        if (!res.ok) throw new Error("Health check failed");
        const data = await res.json();

        // Test API with auth
        await api.listJobs({ page: 1, page_size: 1 });

        setStatus("connected");
        setMessage(`✓ Connected to API at ${process.env.NEXT_PUBLIC_API_URL}`);
      } catch (err) {
        setStatus("error");
        setMessage(`✗ Connection failed: ${err instanceof Error ? err.message : "Unknown error"}`);
      }
    };

    testConnection();
  }, []);

  const bgColor = status === "connected" ? "bg-green-900/20" : status === "error" ? "bg-red-900/20" : "bg-blue-900/20";
  const textColor = status === "connected" ? "text-green-400" : status === "error" ? "text-red-400" : "text-blue-400";

  return (
    <div className={`rounded-lg border border-border ${bgColor} p-3`}>
      <p className={`text-sm ${textColor} font-medium`}>{message}</p>
    </div>
  );
}
