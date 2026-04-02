"use client";

import { Handle, NodeProps, Position } from "reactflow";
import { cn } from "@/lib/utils";
import { Clapperboard, AlertCircle, CheckCircle2 } from "lucide-react";
import { HANDLE_COLORS } from "./nodeTypes";
import { useWorkflowStore } from "@/lib/workflowStore";

export interface ShotNodeData {
  shotId: string;
  shotLabel: string;
  shotType: "t2v" | "i2v";
  model: string;
  resolution: string;
  frames: number;
  steps: number;
  prompt: string;
  seed: number | null;
  outputUrl?: string | null;
  updateNodeData?: (nodeId: string, patch: Record<string, unknown>) => void;
}

export function ShotNode({ data, selected, id }: NodeProps<ShotNodeData>) {
  const nodeStatus = useWorkflowStore((s) => s.nodeStatuses[id]);

  const status = nodeStatus?.status || "pending";
  const progress = nodeStatus?.progress || 0;
  const message = nodeStatus?.message || "";

  return (
    <div
      className={cn(
        "min-w-[360px] max-w-[360px] rounded-2xl overflow-hidden shadow-lg shadow-black/40",
        "border border-slate-700/60 bg-slate-800/70",
        "transition-all duration-150",
        selected && "ring-2 ring-cyan-400 ring-offset-1 ring-offset-slate-900"
      )}
    >
      {/* Header */}
      <div className="h-12 bg-gradient-to-r from-cyan-700 to-cyan-500 flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <Clapperboard className="w-5 h-5 text-white flex-shrink-0" />
          <h3 className="text-sm font-semibold text-white truncate">{data.shotLabel}</h3>
        </div>
        {/* Status Badge */}
        {status === "done" && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/30 text-green-400 text-xs font-semibold whitespace-nowrap">
            <CheckCircle2 className="w-3 h-3" /> Done
          </div>
        )}
        {status === "running" && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-500/30 text-yellow-400 text-xs font-semibold whitespace-nowrap animate-pulse">
            ● Running
          </div>
        )}
        {status === "failed" && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/30 text-red-400 text-xs font-semibold whitespace-nowrap">
            <AlertCircle className="w-3 h-3" /> Failed
          </div>
        )}
        {status === "pending" && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-600/50 text-slate-300 text-xs font-semibold whitespace-nowrap">
            ○ Pending
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-3 space-y-3">
        <textarea
          value={data.prompt}
          onChange={(e) => data.updateNodeData?.(id, { prompt: e.target.value })}
          rows={4}
          className="nodrag nopan w-full resize-none rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs leading-relaxed text-slate-200 outline-none transition focus:border-cyan-500"
          placeholder="Describe the shot..."
        />

        <div className="grid grid-cols-2 gap-2">
          <select
            value={data.model}
            onChange={(e) => data.updateNodeData?.(id, { model: e.target.value })}
            className="nodrag nopan rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs text-cyan-300 outline-none transition focus:border-cyan-500"
          >
            <option value="wan-2.2-14b">Wan 2.2 14B</option>
            <option value="wan-2.1-7b">Wan 2.1 7B</option>
          </select>
          <select
            value={data.resolution}
            onChange={(e) => data.updateNodeData?.(id, { resolution: e.target.value })}
            className="nodrag nopan rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs text-slate-200 outline-none transition focus:border-cyan-500"
          >
            <option value="256x256">256x256</option>
            <option value="384x384">384x384</option>
            <option value="512x512">512x512</option>
            <option value="640x640">640x640</option>
          </select>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <label className="rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2">
            <span className="mb-1 block text-[10px] uppercase tracking-wide text-slate-500">Frames</span>
            <input
              type="number"
              min={16}
              max={128}
              value={data.frames}
              onChange={(e) => data.updateNodeData?.(id, { frames: Number(e.target.value) || 16 })}
              className="nodrag nopan w-full bg-transparent text-xs text-white outline-none"
            />
          </label>
          <label className="rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2">
            <span className="mb-1 block text-[10px] uppercase tracking-wide text-slate-500">Steps</span>
            <input
              type="number"
              min={1}
              max={8}
              value={data.steps}
              onChange={(e) => data.updateNodeData?.(id, { steps: Number(e.target.value) || 1 })}
              className="nodrag nopan w-full bg-transparent text-xs text-white outline-none"
            />
          </label>
          <label className="rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2">
            <span className="mb-1 block text-[10px] uppercase tracking-wide text-slate-500">Type</span>
            <select
              value={data.shotType}
              onChange={(e) => data.updateNodeData?.(id, { shotType: e.target.value })}
              className="nodrag nopan w-full bg-transparent text-xs text-white outline-none"
            >
              <option value="t2v">T2V</option>
              <option value="i2v">I2V</option>
            </select>
          </label>
        </div>

        {/* Running state - progress ring */}
        {status === "running" && (
          <div className="flex flex-col items-center justify-center py-4">
            <svg className="w-14 h-14" viewBox="0 0 60 60">
              <circle
                cx="30"
                cy="30"
                r="25"
                fill="none"
                stroke="#1e293b"
                strokeWidth="2"
              />
              <circle
                cx="30"
                cy="30"
                r="25"
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2"
                strokeDasharray={`${2 * Math.PI * 25}`}
                strokeDashoffset={`${2 * Math.PI * 25 * (1 - progress / 100)}`}
                strokeLinecap="round"
                style={{
                  transformOrigin: "30px 30px",
                  transform: "rotateZ(-90deg)",
                  transition: "stroke-dashoffset 0.3s ease",
                }}
              />
              <text
                x="30"
                y="30"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-xs font-bold"
                fill="#06b6d4"
              >
                {Math.round(progress)}%
              </text>
            </svg>
            {message && <p className="text-xs text-slate-400 text-center mt-2 line-clamp-2">{message}</p>}
          </div>
        )}

        {/* Done state - show thumbnail if available */}
        {status === "done" && data.outputUrl && (
          <div className="rounded-lg overflow-hidden bg-slate-900">
            <video
              src={data.outputUrl}
              className="w-full h-20 object-cover"
              muted
              autoPlay
              loop
            />
          </div>
        )}

        {/* Done state - no output yet */}
        {status === "done" && !data.outputUrl && (
          <div className="text-center py-3">
            <p className="text-xs text-slate-400">✓ Generated (no preview)</p>
          </div>
        )}

        {/* Failed state */}
        {status === "failed" && (
          <div className="rounded-lg bg-red-950/30 border border-red-800/50 p-2">
            <p className="text-xs text-red-400 line-clamp-3">{message || "Generation failed"}</p>
          </div>
        )}

        {/* Pending state - show params */}
        {status === "pending" && (
          <div className="flex items-center justify-between rounded-lg border border-slate-700/70 bg-slate-900/40 px-3 py-2 text-[11px] text-slate-400">
            <span>{data.model}</span>
            <span>{data.resolution}</span>
            <span>{data.frames}f</span>
            <span>{data.steps} steps</span>
          </div>
        )}
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        id="scenes-in"
        style={{
          background: HANDLE_COLORS.scenes,
          width: 12,
          height: 12,
          border: "2px solid rgba(255,255,255,0.2)",
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="video-out"
        style={{
          background: HANDLE_COLORS.video,
          width: 12,
          height: 12,
          border: "2px solid rgba(255,255,255,0.2)",
        }}
      />
    </div>
  );
}
