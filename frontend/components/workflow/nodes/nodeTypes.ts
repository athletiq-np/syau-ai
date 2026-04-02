import { ScriptNode } from "./ScriptNode";
import { AnalysisNode } from "./AnalysisNode";
import { ShotNode } from "./ShotNode";
import { StitchNode } from "./StitchNode";
import { OutputNode } from "./OutputNode";

export const HANDLE_COLORS = {
  text: "#06b6d4", // cyan-500
  scenes: "#22c55e", // green-500
  image: "#f97316", // orange-500
  video: "#a855f7", // purple-500
} as const;

export const NODE_TYPES_MAP = {
  script: ScriptNode,
  analysis: AnalysisNode,
  shot: ShotNode,
  stitch: StitchNode,
  output: OutputNode,
} as const;

export const NODE_HEADER_COLORS = {
  script: "#1e40af", // blue-800
  analysis: "#6b21a8", // violet-800
  shot: "#0c4a6e", // cyan-900
  stitch: "#15803d", // green-800
  output: "#0d5f48", // teal-800
} as const;
