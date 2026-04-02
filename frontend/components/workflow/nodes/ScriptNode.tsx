"use client";

import { Handle, NodeProps, Position } from "reactflow";
import { cn } from "@/lib/utils";
import { FileText } from "lucide-react";
import { HANDLE_COLORS } from "./nodeTypes";

export interface ScriptNodeData {
  title: string;
  script: string;
  updateNodeData?: (nodeId: string, patch: Record<string, unknown>) => void;
}

export function ScriptNode({ data, selected, id }: NodeProps<ScriptNodeData>) {
  const wordCount = data.script.split(/\s+/).length;

  return (
    <div
      className={cn(
        "min-w-[320px] max-w-[320px] rounded-2xl overflow-hidden shadow-lg shadow-black/40",
        "border border-slate-700/60 bg-slate-800/70",
        "transition-all duration-150",
        selected && "ring-2 ring-cyan-400 ring-offset-1 ring-offset-slate-900"
      )}
    >
      {/* Header */}
      <div className="h-12 bg-gradient-to-r from-blue-700 to-blue-500 flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-5 h-5 text-white flex-shrink-0" />
          <h3 className="text-sm font-semibold text-white truncate">{data.title}</h3>
        </div>
      </div>

      {/* Body */}
      <div className="p-3 space-y-3">
        <input
          value={data.title}
          onChange={(e) => data.updateNodeData?.(id, { title: e.target.value })}
          className="nodrag nopan w-full rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-sm font-semibold text-white outline-none transition focus:border-cyan-500"
          placeholder="Project title"
        />
        <textarea
          value={data.script}
          onChange={(e) => data.updateNodeData?.(id, { script: e.target.value })}
          rows={5}
          className="nodrag nopan w-full resize-none rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs leading-relaxed text-slate-200 outline-none transition focus:border-cyan-500"
          placeholder="Write your script here..."
        />
        <p className="text-xs text-slate-500 font-mono">{wordCount} words</p>
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="text-out"
        style={{
          background: HANDLE_COLORS.text,
          width: 12,
          height: 12,
          border: "2px solid rgba(255,255,255,0.2)",
        }}
      />
    </div>
  );
}
