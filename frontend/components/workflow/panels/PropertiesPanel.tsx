"use client";

import { Dispatch, SetStateAction } from "react";
import { Node } from "reactflow";
import { Settings, Trash2 } from "lucide-react";
import { useWorkflowStore } from "@/lib/workflowStore";

interface PropertiesPanelProps {
  nodes: Node[];
  setNodes: Dispatch<SetStateAction<Node[]>>;
}

export function PropertiesPanel({ nodes, setNodes: updateNodes }: PropertiesPanelProps) {
  const { selectedNodeId, setSelectedNodeId } = useWorkflowStore();
  const node = nodes.find((n) => n.id === selectedNodeId);

  if (!node) {
    return (
      <div className="w-72 flex-none bg-slate-900/40 backdrop-blur border-l border-slate-800/50 rounded-xl overflow-hidden flex flex-col justify-center items-center">
        <Settings className="w-8 h-8 text-slate-600 mb-2" />
        <p className="text-sm text-slate-400">Select a node to edit</p>
      </div>
    );
  }

  const updateNode = (field: string, value: any) => {
    updateNodes((nds) =>
      nds.map((n) =>
        n.id === selectedNodeId
          ? { ...n, data: { ...n.data, [field]: value } }
          : n
      )
    );
  };

  const deleteNode = () => {
    updateNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
    setSelectedNodeId(null);
  };

  return (
    <div className="w-72 flex-none bg-slate-900/40 backdrop-blur border-l border-slate-800/50 rounded-xl overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-800/50 flex-shrink-0 bg-gradient-to-br from-slate-800/30 to-slate-900/30">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold text-white">{node.data.title || `Node: ${node.type}`}</h3>
          <button
            onClick={deleteNode}
            className="p-1 hover:bg-red-600/20 text-red-400 hover:text-red-300 rounded transition-all"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-slate-500 capitalize">{node.type} node</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Common: Title */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
            Title
          </label>
          <input
            type="text"
            value={node.data.title || ""}
            onChange={(e) => updateNode("title", e.target.value)}
            className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50"
          />
        </div>

        {/* AnalysisNode & ShotNode: Model */}
        {(node.type === "analysis" || node.type === "shot") && (
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
              Model
            </label>
            <select
              value={node.data.model || ""}
              onChange={(e) => updateNode("model", e.target.value)}
              className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {node.type === "analysis" && (
                <>
                  <option value="qwen-2.5-32b">Qwen 2.5 32B</option>
                  <option value="qwen-2.5-14b">Qwen 2.5 14B</option>
                  <option value="qwen-1.8b">Qwen 1.8B</option>
                </>
              )}
              {node.type === "shot" && (
                <>
                  <option value="wan-2.2-14b">Wan 2.2 14B</option>
                  <option value="wan-2.1-7b">Wan 2.1 7B</option>
                </>
              )}
            </select>
          </div>
        )}

        {/* ShotNode: Prompt */}
        {node.type === "shot" && (
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
              Prompt
            </label>
            <textarea
              value={node.data.prompt || ""}
              onChange={(e) => updateNode("prompt", e.target.value)}
              rows={3}
              className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 resize-none"
              placeholder="Describe the shot..."
            />
          </div>
        )}

        {/* ShotNode: Resolution */}
        {node.type === "shot" && (
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
              Resolution
            </label>
            <select
              value={node.data.resolution || "512x512"}
              onChange={(e) => updateNode("resolution", e.target.value)}
              className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="256x256">256×256 (Fast)</option>
              <option value="384x384">384×384 (Balanced)</option>
              <option value="512x512">512×512 (Quality)</option>
              <option value="640x640">640×640 (Best)</option>
            </select>
          </div>
        )}

        {/* ShotNode: Frames */}
        {node.type === "shot" && (
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Frames
              </label>
              <span className="text-sm font-bold text-cyan-400">{node.data.frames || 25}</span>
            </div>
            <input
              type="range"
              min="16"
              max="128"
              value={node.data.frames || 25}
              onChange={(e) => updateNode("frames", parseInt(e.target.value))}
              className="w-full accent-cyan-500"
            />
            <p className="text-xs text-slate-500 mt-1">16 = 1s @ 16fps, 81 = 5s</p>
          </div>
        )}

        {/* ShotNode: Steps */}
        {node.type === "shot" && (
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Inference Steps
              </label>
              <span className="text-sm font-bold text-cyan-400">{node.data.steps || 2}</span>
            </div>
            <input
              type="range"
              min="1"
              max="8"
              value={node.data.steps || 2}
              onChange={(e) => updateNode("steps", parseInt(e.target.value))}
              className="w-full accent-cyan-500"
            />
            <p className="text-xs text-slate-500 mt-1">Higher = better quality but slower</p>
          </div>
        )}

        {/* ShotNode: Shot Type */}
        {node.type === "shot" && (
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
              Shot Type
            </label>
            <select
              value={node.data.shotType || "t2v"}
              onChange={(e) => updateNode("shotType", e.target.value)}
              className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="t2v">Text to Video</option>
              <option value="i2v">Image to Video</option>
            </select>
          </div>
        )}

        {/* StitchNode: FPS */}
        {node.type === "stitch" && (
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
              FPS
            </label>
            <input
              type="number"
              value={node.data.fps || 16}
              onChange={(e) => updateNode("fps", parseInt(e.target.value) || 16)}
              min="1"
              max="60"
              className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>
        )}

        {/* StitchNode: Codec */}
        {node.type === "stitch" && (
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">
              Codec
            </label>
            <select
              value={node.data.codec || "h264"}
              onChange={(e) => updateNode("codec", e.target.value)}
              className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="h264">H.264 (MP4)</option>
              <option value="h265">H.265 (HEVC)</option>
              <option value="vp9">VP9 (WebM)</option>
            </select>
          </div>
        )}
      </div>
    </div>
  );
}
