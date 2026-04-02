"use client";

import { useState } from "react";
import { ChevronUp, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { useWorkflowStore } from "@/lib/workflowStore";
import * as Progress from "@radix-ui/react-progress";
import { cn } from "@/lib/utils";

export function ActiveRunsPanel() {
  const { isRunning, runs } = useWorkflowStore();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const visibleRuns = Object.values(runs).sort((a, b) => {
    // Show running first, then done, then failed
    const statusOrder = { running: 0, pending: 1, done: 2, failed: 3 };
    return (statusOrder[a.status] ?? 99) - (statusOrder[b.status] ?? 99);
  });

  if (visibleRuns.length === 0) return null;

  return (
    <div className="border-t border-slate-800/50 bg-slate-900/40 backdrop-blur flex-none">
      {/* Header */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-800/20 transition-all"
      >
        <div className="flex items-center gap-3">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-semibold text-white">
            Active Runs ({visibleRuns.length})
          </span>
        </div>
        <ChevronUp
          className={cn(
            "w-4 h-4 text-slate-400 transition-transform",
            isCollapsed && "rotate-180"
          )}
        />
      </button>

      {/* Content */}
      {!isCollapsed && (
        <div className="px-4 pb-4 space-y-3 max-h-48 overflow-y-auto">
          {visibleRuns.map((run) => (
            <div key={run.shotId} className="rounded-lg bg-slate-800/40 border border-slate-700/50 p-3">
              {/* Title + Status */}
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-slate-200 truncate">
                  {run.shotLabel}
                </h4>
                {run.status === "done" && (
                  <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                )}
                {run.status === "failed" && (
                  <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                )}
                {run.status === "running" && (
                  <div className="w-4 h-4 rounded-full border-2 border-yellow-400 border-t-transparent animate-spin" />
                )}
              </div>

              {/* Progress Bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>{run.status === "running" ? "Generating..." : run.status}</span>
                  <span>{run.progress}%</span>
                </div>
                <Progress.Root
                  value={run.progress}
                  max={100}
                  className="w-full h-2 bg-slate-700 rounded-full overflow-hidden"
                >
                  <Progress.Indicator
                    className={cn(
                      "h-full transition-all",
                      run.status === "done"
                        ? "bg-gradient-to-r from-green-500 to-emerald-500"
                        : run.status === "failed"
                          ? "bg-gradient-to-r from-red-500 to-rose-500"
                          : "bg-gradient-to-r from-cyan-500 to-blue-500"
                    )}
                    style={{ width: `${run.progress}%` }}
                  />
                </Progress.Root>
              </div>

              {/* Message */}
              {run.message && (
                <p className="text-xs text-slate-400 mt-2 line-clamp-2">{run.message}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
