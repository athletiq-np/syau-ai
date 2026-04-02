"use client";

import { useState } from "react";
import { Code, ImageIcon, Layers } from "lucide-react";
import { useWorkflowStore } from "@/lib/workflowStore";
import { cn } from "@/lib/utils";

const NODES = [
  {
    id: "script",
    name: "Script Input",
    icon: "📝",
    description: "Start with a script",
  },
  {
    id: "analysis",
    name: "Scene Analysis",
    icon: "🧠",
    description: "Break into shots",
  },
  {
    id: "shot",
    name: "Shot Generation",
    icon: "🎬",
    description: "Generate video",
  },
  {
    id: "stitch",
    name: "Film Stitching",
    icon: "🎞️",
    description: "Combine shots",
  },
  {
    id: "output",
    name: "Final Output",
    icon: "🎥",
    description: "Download film",
  },
];

export function NodeLibraryPanel() {
  const { leftPanelTab, setLeftPanelTab, project } = useWorkflowStore();
  const tab = leftPanelTab;

  const handleDragStart = (
    e: React.DragEvent,
    nodeType: string
  ) => {
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("application/reactflow-nodetype", nodeType);
  };

  return (
    <div className="w-64 flex-none bg-slate-900/40 backdrop-blur border-r border-slate-800/50 rounded-xl overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-800/50 flex-shrink-0 bg-gradient-to-br from-slate-800/30 to-slate-900/30">
        <div className="flex items-center gap-2 mb-3">
          <Code className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-white">Workflow Tools</h3>
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setLeftPanelTab("library")}
            className={cn(
              "flex-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              tab === "library"
                ? "bg-cyan-600 text-white"
                : "bg-slate-800/40 text-slate-400 hover:bg-slate-800/60"
            )}
          >
            Nodes
          </button>
          <button
            onClick={() => setLeftPanelTab("assets")}
            className={cn(
              "flex-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              tab === "assets"
                ? "bg-cyan-600 text-white"
                : "bg-slate-800/40 text-slate-400 hover:bg-slate-800/60"
            )}
          >
            Assets
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === "library" && (
          <div className="space-y-2">
            {NODES.map((node) => (
              <div
                key={node.id}
                draggable
                onDragStart={(e) => handleDragStart(e, node.id)}
                className="cursor-grab active:cursor-grabbing p-3 rounded-lg bg-gradient-to-r from-slate-800 to-slate-800/50 hover:from-slate-700 hover:to-slate-700/50 border border-slate-700/50 hover:border-slate-600 transition-all"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{node.icon}</span>
                  <span className="text-sm font-semibold text-white flex-1">
                    {node.name}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{node.description}</p>
              </div>
            ))}
          </div>
        )}

        {tab === "assets" && (
          <div className="space-y-4">
            {project?.scenes && project.scenes.length > 0 ? (
              project.scenes.map((scene, sceneIdx) => (
                <div key={scene.id}>
                  <h4 className="text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
                    Scene {sceneIdx + 1}: {scene.title}
                  </h4>
                  <div className="space-y-1.5">
                    {scene.shots.map((shot, shotIdx) => (
                      <div
                        key={shot.id}
                        className="rounded-lg bg-slate-800/40 border border-slate-700/50 p-2"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="text-xs font-mono text-slate-400">
                            Shot {shotIdx + 1}
                          </span>
                          <span
                            className={cn(
                              "text-xs px-2 py-0.5 rounded-full font-medium",
                              shot.status === "done"
                                ? "bg-green-500/20 text-green-400"
                                : shot.status === "running"
                                  ? "bg-yellow-500/20 text-yellow-400"
                                  : shot.status === "failed"
                                    ? "bg-red-500/20 text-red-400"
                                    : "bg-slate-600/20 text-slate-400"
                            )}
                          >
                            {shot.status}
                          </span>
                        </div>
                        {shot.output_url && (
                          <div className="rounded bg-black/50 overflow-hidden h-12">
                            <video
                              src={shot.output_url}
                              className="w-full h-full object-cover"
                              muted
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <Layers className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-400">No assets yet</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
