"use client";

import { Handle, NodeProps, Position } from "reactflow";
import { cn } from "@/lib/utils";
import { Download, CheckCircle2 } from "lucide-react";
import { HANDLE_COLORS } from "./nodeTypes";

export interface OutputNodeData {
  outputUrl?: string | null;
}

export function OutputNode({ data, selected, id }: NodeProps<OutputNodeData>) {
  return (
    <div
      className={cn(
        "min-w-[240px] rounded-xl overflow-hidden shadow-lg shadow-black/40",
        "border border-slate-700/60 bg-slate-800/70",
        "transition-all duration-150",
        selected && "ring-2 ring-cyan-400 ring-offset-1 ring-offset-slate-900"
      )}
    >
      {/* Header */}
      <div className="h-12 bg-gradient-to-r from-emerald-700 to-teal-500 flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <Download className="w-5 h-5 text-white flex-shrink-0" />
          <h3 className="text-sm font-semibold text-white truncate">Final Film</h3>
        </div>
        {data.outputUrl && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/30 text-green-400 text-xs font-semibold">
            <CheckCircle2 className="w-3 h-3" /> Ready
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-3">
        {data.outputUrl ? (
          <div className="space-y-3">
            <video
              src={data.outputUrl}
              controls
              className="w-full rounded-lg bg-slate-900 max-h-24 object-cover"
            />
            <a
              href={data.outputUrl}
              download
              className="block w-full px-3 py-2 text-center text-sm font-medium rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 text-white hover:from-green-700 hover:to-emerald-700 transition-all"
            >
              Download Film
            </a>
          </div>
        ) : (
          <div className="text-center py-6">
            <p className="text-sm text-slate-400">Awaiting final film...</p>
          </div>
        )}
      </div>

      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="video-in"
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
