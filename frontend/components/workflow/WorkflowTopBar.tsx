"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft, Play, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

interface WorkflowTopBarProps {
  projectTitle: string;
  isRunning: boolean;
  onRun: () => void;
}

export function WorkflowTopBar({ projectTitle, isRunning, onRun }: WorkflowTopBarProps) {
  const router = useRouter();

  return (
    <div className="h-14 flex-none bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/50 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
      {/* Left: Back + Title */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="p-2 hover:bg-slate-800 rounded-lg transition-all hover:text-cyan-400"
        >
          <ChevronLeft className="w-5 h-5 text-slate-400" />
        </button>
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            {projectTitle}
          </h1>
          <p className="text-xs text-slate-500">Workflow Editor</p>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={onRun}
          disabled={isRunning}
          className={cn(
            "px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-all",
            isRunning
              ? "opacity-50 cursor-not-allowed bg-slate-700 text-slate-400"
              : "bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white"
          )}
        >
          <Play className="w-4 h-4" />
          {isRunning ? "Running..." : "Run Workflow"}
        </button>

        <button className="p-2 hover:bg-slate-800 rounded-lg transition-all text-slate-400 hover:text-slate-300">
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
