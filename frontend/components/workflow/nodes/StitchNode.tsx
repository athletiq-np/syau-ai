"use client";

import { Handle, NodeProps, Position } from "reactflow";
import { cn } from "@/lib/utils";
import { Film } from "lucide-react";
import { HANDLE_COLORS } from "./nodeTypes";
import { useWorkflowStore } from "@/lib/workflowStore";

export interface StitchNodeData {
  codec: string;
  fps: number;
  inputCount: number;
  updateNodeData?: (nodeId: string, patch: Record<string, unknown>) => void;
}

export function StitchNode({ data, selected, id }: NodeProps<StitchNodeData>) {
  const nodeStatus = useWorkflowStore((s) => s.nodeStatuses[id]);
  const status = nodeStatus?.status || "pending";
  const progress = nodeStatus?.progress || 0;

  return (
    <div
      className={cn(
        "min-w-[280px] max-w-[280px] rounded-2xl overflow-hidden shadow-lg shadow-black/40",
        "border border-slate-700/60 bg-slate-800/70",
        "transition-all duration-150",
        selected && "ring-2 ring-cyan-400 ring-offset-1 ring-offset-slate-900"
      )}
    >
      {/* Header */}
      <div className="h-12 bg-gradient-to-r from-green-700 to-emerald-500 flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <Film className="w-5 h-5 text-white flex-shrink-0" />
          <h3 className="text-sm font-semibold text-white truncate">Stitch Film</h3>
        </div>
        {status === "running" && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-500/30 text-yellow-400 text-xs font-semibold animate-pulse">
            ● Running
          </div>
        )}
        {status === "done" && (
          <div className="px-2 py-0.5 rounded-full bg-green-500/30 text-green-400 text-xs font-semibold">
            ✓ Done
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-3 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <select
            value={data.codec}
            onChange={(e) => data.updateNodeData?.(id, { codec: e.target.value })}
            className="nodrag nopan rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs text-cyan-300 outline-none transition focus:border-cyan-500"
          >
            <option value="h264">H.264</option>
            <option value="h265">H.265</option>
            <option value="vp9">VP9</option>
          </select>
          <input
            type="number"
            min={1}
            max={60}
            value={data.fps}
            onChange={(e) => data.updateNodeData?.(id, { fps: Number(e.target.value) || 16 })}
            className="nodrag nopan rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs text-white outline-none transition focus:border-cyan-500"
          />
        </div>
        {status === "running" && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-400">
              <span>Stitching</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                style={{ width: `${progress}%`, transition: "width 0.3s ease" }}
              />
            </div>
          </div>
        )}

        {status !== "running" && (
          <>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500">Codec:</span>
              <span className="text-cyan-400 font-mono">{data.codec}</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500">FPS:</span>
              <span className="text-cyan-400 font-mono">{data.fps}</span>
            </div>
            <div className="text-xs text-slate-400">
              {data.inputCount} input{data.inputCount !== 1 ? "s" : ""} connected
            </div>
          </>
        )}
      </div>

      {/* Input handles - multiple for each shot */}
      {Array.from({ length: Math.max(1, data.inputCount) }).map((_, i) => (
        <Handle
          key={`video-in-${i}`}
          type="target"
          position={Position.Left}
          id={`video-in-${i}`}
          style={{
            background: HANDLE_COLORS.video,
            width: 12,
            height: 12,
            border: "2px solid rgba(255,255,255,0.2)",
            top: `${60 + i * 28}px`,
          }}
        />
      ))}

      {/* Output handle */}
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
