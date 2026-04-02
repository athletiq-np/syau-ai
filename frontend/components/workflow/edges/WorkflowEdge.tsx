"use client";

import { EdgeProps, getBezierPath } from "reactflow";
import { HANDLE_COLORS } from "../nodes/nodeTypes";

function getEdgeColor(sourceHandle: string | null | undefined): string {
  if (!sourceHandle) return "#64748b";

  if (sourceHandle.includes("text")) return HANDLE_COLORS.text;
  if (sourceHandle.includes("scenes")) return HANDLE_COLORS.scenes;
  if (sourceHandle.includes("video")) return HANDLE_COLORS.video;
  if (sourceHandle.includes("image")) return HANDLE_COLORS.image;

  return "#64748b";
}

export function WorkflowEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  sourceHandleId,
  markerEnd,
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const color = getEdgeColor(sourceHandleId);

  return (
    <>
      {/* Glow/shadow effect */}
      <path
        d={edgePath}
        fill="none"
        stroke={color}
        strokeWidth={5}
        opacity="0.2"
      />
      {/* Main edge */}
      <path
        d={edgePath}
        fill="none"
        stroke={color}
        strokeWidth="2"
        markerEnd={markerEnd}
      />
    </>
  );
}
