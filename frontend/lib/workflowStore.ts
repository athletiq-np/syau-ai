import { create } from "zustand";
import { ProjectDetail } from "./api";

export interface NodeStatus {
  status: "pending" | "running" | "done" | "failed";
  progress: number; // 0-100
  message: string;
  startedAt: number | null; // Date.now() timestamp
}

export interface RunInfo {
  shotId: string;
  nodeId: string;
  shotLabel: string; // e.g., "Scene 1 · Shot 2"
  status: "pending" | "running" | "done" | "failed";
  progress: number;
  message: string;
  startedAt: number | null;
}

type RunInfoUpdate = Partial<Omit<RunInfo, "shotId">>;

interface WorkflowState {
  // Data
  project: ProjectDetail | null;
  // UI state
  selectedNodeId: string | null;
  leftPanelTab: "library" | "assets";
  rightPanelOpen: boolean;
  // Run state
  isRunning: boolean;
  runs: Record<string, RunInfo>; // keyed by shotId
  nodeStatuses: Record<string, NodeStatus>; // keyed by ReactFlow node id

  // Actions
  setProject: (p: ProjectDetail | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  setLeftPanelTab: (tab: "library" | "assets") => void;
  setRightPanelOpen: (open: boolean) => void;
  setIsRunning: (v: boolean) => void;
  updateRun: (shotId: string, partial: RunInfoUpdate) => void;
  clearRuns: () => void;
  updateNodeStatus: (nodeId: string, partial: Partial<NodeStatus>) => void;
  clearNodeStatus: (nodeId: string) => void;
}

export const useWorkflowStore = create<WorkflowState>()((set) => ({
  project: null,
  selectedNodeId: null,
  leftPanelTab: "library",
  rightPanelOpen: true,
  isRunning: false,
  runs: {},
  nodeStatuses: {},

  setProject: (p) => set({ project: p }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  setLeftPanelTab: (tab) => set({ leftPanelTab: tab }),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
  setIsRunning: (v) => set({ isRunning: v }),

  updateRun: (shotId, partial) =>
    set((state) => {
      const previous = state.runs[shotId];
      return {
        runs: {
          ...state.runs,
          [shotId]: {
            shotId,
            nodeId: previous?.nodeId ?? "",
            shotLabel: previous?.shotLabel ?? "",
            status: partial.status ?? previous?.status ?? "pending",
            progress: partial.progress ?? previous?.progress ?? 0,
            message: partial.message ?? previous?.message ?? "",
            startedAt: partial.startedAt ?? previous?.startedAt ?? null,
            ...partial,
          },
        },
      };
    }),

  clearRuns: () => set({ runs: {} }),

  updateNodeStatus: (nodeId, partial) =>
    set((state) => {
      const previous = state.nodeStatuses[nodeId];
      return {
        nodeStatuses: {
          ...state.nodeStatuses,
          [nodeId]: {
            status: partial.status ?? previous?.status ?? "pending",
            progress: partial.progress ?? previous?.progress ?? 0,
            message: partial.message ?? previous?.message ?? "",
            startedAt: partial.startedAt ?? previous?.startedAt ?? null,
          },
        },
      };
    }),

  clearNodeStatus: (nodeId) =>
    set((state) => {
      const updated = { ...state.nodeStatuses };
      delete updated[nodeId];
      return { nodeStatuses: updated };
    }),
}));
