import { useEffect } from "react";
import { api } from "@/lib/api";

export function useProjectWebSocket(
  projectId: string,
  onShotStart: (shotId: string) => void,
  onShotProgress: (shotId: string, progress: number, message: string) => void,
  onShotComplete: (shotId: string) => void,
  onShotFailed: (shotId: string, error: string) => void,
  onStitchStart: () => void,
  onStitchComplete: () => void,
  onStitchFailed: (error: string) => void
) {

  useEffect(() => {
    let isMounted = true;
    let fallbackToPolling = false;
    let pollingTimeoutRef: NodeJS.Timeout | null = null;
    let wsRef: WebSocket | null = null;
    let pollIntervalRef: NodeJS.Timeout | null = null;
    let lastProjectStateRef = "";
    let hasReceivedProjectEvent = false;

    function schedulePollingFallback() {
      if (pollingTimeoutRef) clearTimeout(pollingTimeoutRef);
      pollingTimeoutRef = setTimeout(() => {
        if (!fallbackToPolling && !hasReceivedProjectEvent) {
          console.warn("[WebSocket] No live project events received, falling back to polling");
          fallbackToPolling = true;
          if (wsRef?.readyState === WebSocket.OPEN) {
            wsRef.close();
          }
          startPolling();
        }
      }, 5000);
    }

    function connectWebSocket() {
      try {
        const wsUrl = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost/ws")
          .replace(/\/$/, "");
        const fullUrl = `${wsUrl}/projects/${projectId}`;

        wsRef = new WebSocket(fullUrl);

        wsRef.onopen = () => {
          console.log("[WebSocket] Connected to project events");
          schedulePollingFallback();
        };

        wsRef.onmessage = (event) => {
          if (!isMounted) return;

          try {
            const data = JSON.parse(event.data);
            console.log("[WebSocket] Event:", data.type, data);

            // Track if we receive init (backend always sends this)
            if (data.type === "init") {
              schedulePollingFallback();
              return;
            }

            // Any other event type means WebSocket is working
            hasReceivedProjectEvent = true;
            if (pollingTimeoutRef) clearTimeout(pollingTimeoutRef);

            switch (data.type) {
              case "shot_start":
                onShotStart(data.shot_id);
                break;
              case "shot_progress":
                onShotProgress(data.shot_id, data.progress || 0, data.message || "");
                break;
              case "shot_complete":
                onShotComplete(data.shot_id);
                break;
              case "shot_failed":
                onShotFailed(data.shot_id, data.error || "Unknown error");
                break;
              case "stitch_start":
                onStitchStart();
                break;
              case "stitch_complete":
                onStitchComplete();
                break;
              case "stitch_failed":
                onStitchFailed(data.error || "Stitch failed");
                break;
            }
          } catch (err) {
            console.error("[WebSocket] Failed to parse message:", err);
          }
        };

        wsRef.onerror = (err) => {
          console.error("[WebSocket] Error:", err);
        };

        wsRef.onclose = () => {
          console.log("[WebSocket] Closed");
          if (!fallbackToPolling && !hasReceivedProjectEvent) {
            startPolling();
          }
        };
      } catch (err) {
        console.error("[WebSocket] Failed to create connection:", err);
      }
    }

    function startPolling() {
      if (pollIntervalRef) clearInterval(pollIntervalRef);

      pollIntervalRef = setInterval(async () => {
        if (!isMounted) return;

        try {
          const project = await api.getProject(projectId);
          const currentState = JSON.stringify(project.scenes);

          // Detect shot status changes by comparing with previous state
          if (lastProjectStateRef !== "") {
            const prevProject = JSON.parse(lastProjectStateRef);
            // Compare shots to find changes
            project.scenes.forEach((scene, sceneIdx) => {
              const prevScene = prevProject[sceneIdx];
              if (!prevScene) return;

              scene.shots.forEach((shot, shotIdx) => {
                const prevShot = prevScene.shots?.[shotIdx];
                if (!prevShot) return;

                if (prevShot.status !== shot.status) {
                  if (shot.status === "running" && prevShot.status !== "running") {
                    onShotStart(shot.id);
                  } else if (shot.status === "done" && prevShot.status !== "done") {
                    onShotComplete(shot.id);
                  } else if (shot.status === "failed" && prevShot.status !== "failed") {
                    onShotFailed(shot.id, shot.error || "Unknown error");
                  }
                }
              });
            });
          }

          lastProjectStateRef = currentState;
        } catch (err) {
          console.error("[Polling] Failed to fetch project:", err);
        }
      }, 2000);
    }

    // Attempt WebSocket first
    connectWebSocket();

    return () => {
      isMounted = false;
      if (wsRef?.readyState === WebSocket.OPEN) {
        wsRef?.close();
      }
      if (pollIntervalRef) {
        clearInterval(pollIntervalRef);
      }
      if (pollingTimeoutRef) {
        clearTimeout(pollingTimeoutRef);
      }
    };
  }, [projectId, onShotStart, onShotProgress, onShotComplete, onShotFailed, onStitchStart, onStitchComplete, onStitchFailed]);
}
