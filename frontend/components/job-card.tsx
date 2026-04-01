"use client";
import { useState } from "react";
import Link from "next/link";
import type { Job } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  job: Job;
  expanded?: boolean;
}

export function JobCard({ job, expanded = false }: Props) {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const hasOutput = job.output_urls && job.output_urls.length > 0;
  const hasText = Boolean(job.output_text);
  const outputUrl = job.output_urls?.[0] ?? null;
  const isVideo = job.type === "video";
  const isImage = job.type === "image";

  const statusColor = {
    pending: "text-yellow-400",
    running: "text-blue-400",
    done: "text-green-400",
    failed: "text-red-400",
    cancelled: "text-muted-foreground",
  }[job.status] ?? "text-muted-foreground";

  async function copyPrompt(e: React.MouseEvent<HTMLButtonElement>) {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(job.prompt);
    } catch {
      // Clipboard support is optional in this lightweight UI.
    }
  }

  return (
    <div
      className={cn(
        "bg-card border border-border rounded-lg overflow-hidden cursor-pointer transition-all",
        isExpanded ? "col-span-2" : ""
      )}
      onClick={() => setIsExpanded((v) => !v)}
    >
      {/* Thumbnail */}
      <div className="aspect-square bg-muted relative overflow-hidden">
        {hasOutput ? (
          isVideo ? (
            <video
              src={outputUrl ?? undefined}
              className="absolute inset-0 h-full w-full object-cover"
              controls={false}
              autoPlay
              loop
              muted
            />
          ) : (
            <img
              src={outputUrl ?? undefined}
              alt={job.prompt}
              className="absolute inset-0 h-full w-full object-cover"
            />
          )
        ) : hasText ? (
          <div className="absolute inset-0 p-4 text-xs leading-5 text-foreground/90 overflow-hidden">
            {job.output_text}
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={cn("text-xs font-medium", statusColor)}>
              {job.status === "running" ? (
                <span className="flex items-center gap-1">
                  <span className="inline-block w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                  Running
                </span>
              ) : (
                job.status.toUpperCase()
              )}
            </span>
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="p-3 flex flex-col gap-1">
        <p className="text-xs text-foreground line-clamp-2">{job.prompt}</p>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-muted-foreground">{job.type} · {job.model}</span>
          <span className={cn("text-xs font-medium", statusColor)}>{job.status}</span>
        </div>
        {job.duration_seconds && (
          <span className="text-xs text-muted-foreground">{job.duration_seconds.toFixed(1)}s</span>
        )}
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t border-border p-4 flex flex-col gap-3" onClick={(e) => e.stopPropagation()}>
          {hasOutput && (
            <div className="w-full max-w-lg mx-auto overflow-hidden rounded border border-border bg-muted">
              {isVideo ? (
                <video
                  src={outputUrl ?? undefined}
                  className="w-full aspect-square object-cover"
                  controls
                  autoPlay
                  loop
                  muted
                />
              ) : (
                <img
                  src={outputUrl ?? undefined}
                  alt={job.prompt}
                  className={cn(
                    "w-full",
                    isImage ? "aspect-square object-contain" : "aspect-square object-cover"
                  )}
                />
              )}
            </div>
          )}
          {hasText && (
            <pre className="whitespace-pre-wrap text-sm leading-6 text-foreground bg-muted/40 rounded-md p-3">
              {job.output_text}
            </pre>
          )}
          {!hasOutput && !hasText && isVideo && (
            <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
              Video preview is still processing.
            </div>
          )}
          <div className="text-sm text-foreground">{job.prompt}</div>
          {job.negative_prompt && (
            <div className="text-xs text-muted-foreground">
              <span className="font-medium">Negative:</span> {job.negative_prompt}
            </div>
          )}
          {job.error && (
            <div className="text-xs text-red-400 bg-red-950/30 border border-red-800 rounded px-2 py-1">
              {job.error}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {outputUrl && (
              <Link
                href={outputUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs px-2.5 py-1.5 rounded border border-border hover:bg-accent text-foreground"
                onClick={(e) => e.stopPropagation()}
              >
                Open Asset
              </Link>
            )}
            {outputUrl && (
              <a
                href={outputUrl}
                download
                className="text-xs px-2.5 py-1.5 rounded border border-border hover:bg-accent text-foreground"
                onClick={(e) => e.stopPropagation()}
              >
                Download
              </a>
            )}
            <button
              type="button"
              className="text-xs px-2.5 py-1.5 rounded border border-border hover:bg-accent text-foreground"
              onClick={copyPrompt}
            >
              Copy Prompt
            </button>
          </div>
          <div className="text-xs text-muted-foreground grid grid-cols-2 gap-1">
            <span>Type: {job.type}</span>
            <span>Model: {job.model}</span>
            <span>Status: {job.status}</span>
            {job.seed_used !== null && <span>Seed: {job.seed_used}</span>}
            {job.duration_seconds !== null && <span>Time: {job.duration_seconds?.toFixed(1)}s</span>}
            {job.params?.width && <span>Size: {job.params.width}×{job.params.height}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
