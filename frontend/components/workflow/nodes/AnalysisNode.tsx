"use client";

import { Handle, NodeProps, Position } from "reactflow";
import { cn } from "@/lib/utils";
import { Brain } from "lucide-react";
import { HANDLE_COLORS } from "./nodeTypes";

export interface AnalysisNodeData {
  model: string;
  totalShots: number;
  totalScenes: number;
  updateNodeData?: (nodeId: string, patch: Record<string, unknown>) => void;
}

export function AnalysisNode({ data, selected, id }: NodeProps<AnalysisNodeData>) {
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
      <div className="h-12 bg-gradient-to-r from-violet-700 to-violet-500 flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <Brain className="w-5 h-5 text-white flex-shrink-0" />
          <h3 className="text-sm font-semibold text-white truncate">Scene Analysis</h3>
        </div>
      </div>

      {/* Body */}
      <div className="p-3 space-y-3">
        <select
          value={data.model}
          onChange={(e) => data.updateNodeData?.(id, { model: e.target.value })}
          className="nodrag nopan w-full rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs font-medium text-cyan-300 outline-none transition focus:border-cyan-500"
        >
          <option value="qwen-2.5-32b">Qwen 2.5 32B</option>
          <option value="qwen-2.5-14b">Qwen 2.5 14B</option>
          <option value="qwen-1.8b">Qwen 1.8B</option>
        </select>
        <p className="text-xs text-slate-400">
          {data.totalScenes} scenes · {data.totalShots} shots
        </p>
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        id="text-in"
        style={{
          background: HANDLE_COLORS.text,
          width: 12,
          height: 12,
          border: "2px solid rgba(255,255,255,0.2)",
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="scenes-out"
        style={{
          background: HANDLE_COLORS.scenes,
          width: 12,
          height: 12,
          border: "2px solid rgba(255,255,255,0.2)",
        }}
      />
    </div>
  );
}
