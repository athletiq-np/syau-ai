"use client";
import type { Job } from "@/lib/api";

interface Props {
  job: Job | null;
}

export function ChatWindow({ job }: Props) {
  if (!job) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm border border-dashed border-border rounded-lg">
        Your chat response will appear here
      </div>
    );
  }

  if (job.status !== "done" && !job.error) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm border border-dashed border-border rounded-lg">
        Waiting for response...
      </div>
    );
  }

  return (
    <div className="h-full border border-border rounded-lg bg-card/70 overflow-hidden">
      <div className="border-b border-border px-4 py-3 text-xs uppercase tracking-[0.24em] text-muted-foreground">
        Model Output
      </div>
      <div className="p-5 flex flex-col gap-4">
        <div className="text-xs text-muted-foreground">
          {job.model} · {job.status}
        </div>
        {job.error ? (
          <div className="text-sm text-red-400 bg-red-950/30 border border-red-800 rounded px-3 py-2">
            {job.error}
          </div>
        ) : (
          <pre className="whitespace-pre-wrap text-sm leading-6 text-foreground font-sans">
            {job.output_text ?? "No text output returned."}
          </pre>
        )}
      </div>
    </div>
  );
}
