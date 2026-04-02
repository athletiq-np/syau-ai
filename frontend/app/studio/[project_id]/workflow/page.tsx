"use client";

import { useCallback, useMemo, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
  Connection,
  useReactFlow,
  ReactFlowProvider,
  Node,
  Edge,
  useNodesInitialized,
} from "reactflow";
import { api, type ProjectDetail } from "@/lib/api";
import { NODE_TYPES_MAP } from "@/components/workflow/nodes/nodeTypes";
import { WorkflowEdge } from "@/components/workflow/edges/WorkflowEdge";
import { NodeLibraryPanel } from "@/components/workflow/panels/NodeLibraryPanel";
import { ActiveRunsPanel } from "@/components/workflow/panels/ActiveRunsPanel";
import { WorkflowTopBar } from "@/components/workflow/WorkflowTopBar";
import { useProjectWebSocket } from "@/components/workflow/useProjectWebSocket";
import { useWorkflowStore } from "@/lib/workflowStore";

interface Props {
  params: {
    project_id: string;
  };
}

function buildNodesAndEdges(project: ProjectDetail): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Column positions
  const cols = {
    script: 80,
    analysis: 360,
    shots: 640,
    stitch: 920,
    output: 1200,
  };

  // Script node
  nodes.push({
    id: "node-script",
    type: "script",
    position: { x: cols.script, y: 200 },
    data: {
      title: project.title,
      script: project.script,
    },
  });

  // Analysis node
  nodes.push({
    id: "node-analysis",
    type: "analysis",
    position: { x: cols.analysis, y: 200 },
    data: {
      model: "qwen-2.5-32b",
      totalScenes: project.scenes.length,
      totalShots: project.total_shots,
    },
  });

  edges.push({
    id: "edge-script-analysis",
    source: "node-script",
    target: "node-analysis",
    sourceHandle: "text-out",
    targetHandle: "text-in",
  });

  // Shot nodes
  let shotY = 80;
  const shotNodeIds: string[] = [];
  project.scenes.forEach((scene, sceneIdx) => {
    scene.shots.forEach((shot, shotIdx) => {
      const nodeId = `node-shot-${shot.id}`;
      shotNodeIds.push(nodeId);
      nodes.push({
        id: nodeId,
        type: "shot",
        position: { x: cols.shots, y: shotY },
        data: {
          shotId: shot.id,
          shotLabel: `Scene ${sceneIdx + 1} · Shot ${shotIdx + 1}`,
          shotType: shot.shot_type,
          model: "wan-2.2-14b",
          resolution: "512x512",
          frames: shot.duration_frames,
          steps: 2,
          prompt: shot.prompt,
          seed: shot.seed,
          outputUrl: shot.output_url,
        },
      });

      edges.push({
        id: `edge-analysis-shot-${shot.id}`,
        source: "node-analysis",
        target: nodeId,
        sourceHandle: "scenes-out",
        targetHandle: "scenes-in",
      });

      shotY += 140;
    });
  });

  // Stitch node (centered vertically in shot column)
  const stichYCenter = 80 + (shotNodeIds.length - 1) * 140 * 0.5;
  nodes.push({
    id: "node-stitch",
    type: "stitch",
    position: { x: cols.stitch, y: stichYCenter },
    data: {
      codec: "h264",
      fps: 16,
      inputCount: shotNodeIds.length,
    },
  });

  shotNodeIds.forEach((shotNodeId, idx) => {
    edges.push({
      id: `edge-shot-${shotNodeId}-stitch`,
      source: shotNodeId,
      target: "node-stitch",
      sourceHandle: "video-out",
      targetHandle: `video-in-${idx}`,
    });
  });

  // Output node
  nodes.push({
    id: "node-output",
    type: "output",
    position: { x: cols.output, y: stichYCenter },
    data: {
      outputUrl: project.output_url,
    },
  });

  edges.push({
    id: "edge-stitch-output",
    source: "node-stitch",
    target: "node-output",
    sourceHandle: "video-out",
    targetHandle: "video-in",
  });

  return { nodes, edges };
}

function validateConnection(connection: Connection): boolean {
  const handleTypeMap: Record<string, string> = {
    "text-out": "text",
    "text-in": "text",
    "scenes-out": "scenes",
    "scenes-in": "scenes",
    "video-out": "video",
    "video-in": "video",
  };

  const getType = (id: string | null): string | null => {
    if (!id) return null;
    if (id.startsWith("video-in-")) return "video";
    return handleTypeMap[id] ?? null;
  };

  const srcType = getType(connection.sourceHandle);
  const tgtType = getType(connection.targetHandle);

  return srcType !== null && srcType === tgtType;
}

function withInlineEditors(
  nodes: Node[],
  updateNodeData: (nodeId: string, patch: Record<string, unknown>) => void
): Node[] {
  return nodes.map((node) => ({
    ...node,
    data: {
      ...node.data,
      updateNodeData,
    },
  }));
}

function WorkflowEditorContent({ projectId }: { projectId: string }) {
  const reactFlowInstance = useReactFlow();
  const nodesInitialized = useNodesInitialized();
  const projectSaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shotSaveTimeoutsRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  // Load project
  const { project, setProject, isRunning, setIsRunning, updateRun, updateNodeStatus, clearRuns } =
    useWorkflowStore();

  const updateNodeData = useCallback(
    (nodeId: string, patch: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId
            ? {
                ...node,
                data: {
                  ...node.data,
                  ...patch,
                },
              }
            : node
        )
      );

      if (nodeId === "node-script") {
        if (projectSaveTimeoutRef.current) {
          clearTimeout(projectSaveTimeoutRef.current);
        }
        projectSaveTimeoutRef.current = setTimeout(async () => {
          try {
            await api.updateProject(projectId, {
              title: typeof patch.title === "string" ? patch.title : undefined,
              script: typeof patch.script === "string" ? patch.script : undefined,
            });
          } catch (err) {
            console.error("Failed to persist project node edits:", err);
          }
        }, 500);
      }

      if (nodeId.startsWith("node-shot-")) {
        const shotId = nodeId.replace("node-shot-", "");
        if (shotId) {
          const existingTimeout = shotSaveTimeoutsRef.current[shotId];
          if (existingTimeout) {
            clearTimeout(existingTimeout);
          }
          shotSaveTimeoutsRef.current[shotId] = setTimeout(async () => {
            try {
              await api.updateShot(projectId, shotId, {
                prompt: typeof patch.prompt === "string" ? patch.prompt : undefined,
              });
            } catch (err) {
              console.error("Failed to persist shot node edits:", err);
            } finally {
              delete shotSaveTimeoutsRef.current[shotId];
            }
          }, 500);
        }
      }
    },
    [projectId]
  );

  // Initialize nodes/edges from project
  const { nodes: projectNodes, edges: projectEdges } = useMemo(() => {
    if (!project) return { nodes: [], edges: [] };
    const graph = buildNodesAndEdges(project);
    return {
      nodes: withInlineEditors(graph.nodes, updateNodeData),
      edges: graph.edges,
    };
  }, [project, updateNodeData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(projectNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(projectEdges);

  // Load project on mount
  const loadProject = useCallback(async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);
    } catch (err) {
      console.error("Failed to load project:", err);
    }
  }, [projectId, setProject]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  useEffect(() => {
    return () => {
      if (projectSaveTimeoutRef.current) {
        clearTimeout(projectSaveTimeoutRef.current);
      }
      Object.values(shotSaveTimeoutsRef.current).forEach(clearTimeout);
    };
  }, []);

  useEffect(() => {
    setNodes(projectNodes);
    setEdges(projectEdges);
  }, [projectNodes, projectEdges, setNodes, setEdges]);

  useEffect(() => {
    if (!nodesInitialized || projectNodes.length === 0) return;

    const timeout = window.setTimeout(() => {
      reactFlowInstance.fitView({
        padding: 0.24,
        minZoom: 0.5,
        maxZoom: 1.05,
        duration: 550,
      });
    }, 80);

    return () => window.clearTimeout(timeout);
  }, [nodesInitialized, projectNodes, reactFlowInstance]);

  // WebSocket integration
  const handleShotStart = useCallback(
    (shotId: string) => {
      const nodeId = `node-shot-${shotId}`;
      updateNodeStatus(nodeId, {
        status: "running",
        progress: 0,
        message: "Starting generation...",
        startedAt: Date.now(),
      });
      updateRun(shotId, {
        status: "running",
        progress: 0,
        message: "Starting generation...",
        startedAt: Date.now(),
      });
    },
    [updateNodeStatus, updateRun]
  );

  const handleShotProgress = useCallback(
    (shotId: string, progress: number, message: string) => {
      const nodeId = `node-shot-${shotId}`;
      updateNodeStatus(nodeId, { progress, message });
      updateRun(shotId, { progress, message });

      // Trigger ReactFlow re-render
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, _statusVersion: Date.now(), outputUrl: n.data.outputUrl } } : n
        )
      );
    },
    [updateNodeStatus, updateRun, setNodes]
  );

  const handleShotComplete = useCallback(
    (shotId: string) => {
      const nodeId = `node-shot-${shotId}`;
      updateNodeStatus(nodeId, { status: "done", progress: 100, message: "Complete" });
      updateRun(shotId, { status: "done", progress: 100, message: "Complete" });

      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, _statusVersion: Date.now() } } : n
        )
      );

      // Reload project to get output_url
      loadProject();
    },
    [updateNodeStatus, updateRun, setNodes, loadProject]
  );

  const handleShotFailed = useCallback(
    (shotId: string, error: string) => {
      const nodeId = `node-shot-${shotId}`;
      updateNodeStatus(nodeId, { status: "failed", progress: 0, message: error });
      updateRun(shotId, { status: "failed", progress: 0, message: error });

      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, _statusVersion: Date.now() } } : n
        )
      );
    },
    [updateNodeStatus, updateRun, setNodes]
  );

  const handleStitchStart = useCallback(() => {
    updateNodeStatus("node-stitch", {
      status: "running",
      progress: 0,
      message: "Stitching shots...",
      startedAt: Date.now(),
    });
  }, [updateNodeStatus]);

  const handleStitchComplete = useCallback(() => {
    updateNodeStatus("node-stitch", { status: "done", progress: 100, message: "Complete" });
    setIsRunning(false);
    clearRuns();
    loadProject();
  }, [updateNodeStatus, setIsRunning, clearRuns, loadProject]);

  const handleStitchFailed = useCallback(
    (error: string) => {
      updateNodeStatus("node-stitch", { status: "failed", progress: 0, message: error });
      setIsRunning(false);
    },
    [updateNodeStatus, setIsRunning]
  );

  useProjectWebSocket(
    projectId,
    handleShotStart,
    handleShotProgress,
    handleShotComplete,
    handleShotFailed,
    handleStitchStart,
    handleStitchComplete,
    handleStitchFailed
  );

  // Handle connections
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection }, eds));
    },
    [setEdges]
  );

  // Handle drop for new nodes
  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();

      const type = event.dataTransfer.getData("application/reactflow-nodetype");
      if (!type) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: {
          title: `New ${type}`,
          updateNodeData,
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes, updateNodeData]
  );

  // Handle run
  const handleRun = useCallback(async () => {
    if (!project) return;

    try {
      setIsRunning(true);
      clearRuns();
      const res = await api.generateProject(projectId);
      console.log("Generation started:", res);
    } catch (err) {
      console.error("Failed to start generation:", err);
      setIsRunning(false);
    }
  }, [project, projectId, setIsRunning, clearRuns]);

  if (!project) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950 flex items-center justify-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-700 border-t-cyan-500" />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-950 flex flex-col overflow-hidden">
      <WorkflowTopBar
        projectTitle={project.title}
        isRunning={isRunning}
        onRun={handleRun}
      />

      <div className="flex flex-1 overflow-hidden gap-1 p-1">
        <NodeLibraryPanel />

        <div className="flex-1 relative bg-gradient-to-br from-slate-950 to-slate-900 rounded-xl border border-slate-800/50 overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={NODE_TYPES_MAP}
            edgeTypes={{ default: WorkflowEdge }}
            isValidConnection={validateConnection}
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            fitView={false}
            nodesDraggable
            nodesConnectable
            elementsSelectable
            panOnDrag
            zoomOnScroll
            zoomOnPinch
            zoomOnDoubleClick={false}
            panOnScroll={false}
            selectionOnDrag={false}
            preventScrolling={false}
            minZoom={0.1}
            maxZoom={3}
            defaultEdgeOptions={{ animated: false }}
            proOptions={{ hideAttribution: true }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1.5}
              color="#1e293b"
            />
            <Controls
              style={{
                background: "#0f172a",
                border: "1px solid #1e293b",
              }}
              showInteractive={false}
            />
          </ReactFlow>
        </div>
      </div>

      <ActiveRunsPanel />
    </div>
  );
}

export default function WorkflowEditor({ params }: Props) {
  return (
    <ReactFlowProvider>
      <WorkflowEditorContent projectId={params.project_id} />
    </ReactFlowProvider>
  );
}
