"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ProjectDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  params: {
    project_id: string;
  };
}

export default function ProjectDetailPage({ params }: Props) {
  const router = useRouter();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scriptText, setScriptText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState<Record<string, any>>({});

  useEffect(() => {
    loadProject();
  }, [params.project_id]);

  // WebSocket for project generation progress
  useEffect(() => {
    const wsUrl = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost/ws")
      .replace(/\/$/, "");
    const ws = new WebSocket(`${wsUrl}/projects/${params.project_id}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setGenerationProgress((prev) => ({
          ...prev,
          [data.type]: data,
        }));

        // Reload project when shots complete or stitch finishes
        if (data.type === "shot_complete" || data.type === "stitch_complete") {
          setTimeout(() => loadProject(), 500);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => {
      ws.close();
    };
  }, [params.project_id]);

  async function loadProject() {
    try {
      setLoading(true);
      const res = await api.getProject(params.project_id);
      setProject(res);
      setScriptText(res.script);
    } catch (err) {
      console.error("Failed to load project:", err);
      setError("Failed to load project");
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeScript() {
    if (!scriptText.trim()) return;

    try {
      setAnalyzing(true);
      setError(null);

      // First, update the project with new script text
      await api.updateProject(params.project_id, {
        script: scriptText,
      });

      // Analyze the script using Qwen
      await api.analyzeScript(params.project_id);

      // Reload project to show updated scenes/shots
      await loadProject();
    } catch (err) {
      console.error("Failed to analyze script:", err);
      setError(
        err instanceof Error ? err.message : "Failed to analyze script"
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleGenerateAll() {
    try {
      setGenerating(true);
      setError(null);
      setGenerationProgress({});

      const res = await api.generateProject(params.project_id);
      console.log("Generation started:", res);
    } catch (err) {
      console.error("Failed to start generation:", err);
      setError(
        err instanceof Error ? err.message : "Failed to start generation"
      );
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900 flex items-center justify-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-700 border-t-cyan-500" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white">Project not found</h1>
          <button
            onClick={() => router.push("/studio")}
            className="mt-4 rounded-lg bg-cyan-500/20 px-4 py-2 text-cyan-400 hover:bg-cyan-500/30"
          >
            Back to Studio
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <button
            onClick={() => router.push("/studio")}
            className="text-cyan-400 hover:text-cyan-300 text-sm mb-4"
          >
            ← Back to Studio
          </button>
          <h1 className="text-4xl font-bold text-white">{project.title}</h1>
          <p className="mt-2 text-slate-400">{project.description}</p>
        </div>
      </div>

      {/* Main grid layout */}
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Left panel - Script editor */}
          <div className="lg:col-span-1">
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Script</h2>

              <textarea
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                placeholder="Paste your script here..."
                className="w-full h-96 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none resize-none"
              />

              <button
                onClick={handleAnalyzeScript}
                disabled={!scriptText.trim() || analyzing}
                className={cn(
                  "mt-4 w-full rounded-lg px-4 py-2 font-medium transition-all",
                  analyzing || !scriptText.trim()
                    ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                    : "bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:from-cyan-600 hover:to-blue-600"
                )}
              >
                {analyzing ? "Analyzing..." : "Analyze Script"}
              </button>

              {error && (
                <div className="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-red-400 text-sm">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* Center panel - Shot timeline */}
          <div className="lg:col-span-1">
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">
                Shots ({project.total_shots})
              </h2>

              {project.scenes.length === 0 ? (
                <div className="rounded-lg border border-slate-700 border-dashed px-4 py-6 text-center">
                  <p className="text-slate-400">No shots yet. Analyze the script to get started.</p>
                </div>
              ) : (
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {project.scenes.map((scene, sceneIdx) => (
                    <div key={scene.id}>
                      <h3 className="text-sm font-semibold text-cyan-400 mb-2">
                        Scene {sceneIdx + 1}: {scene.title}
                      </h3>
                      <div className="space-y-2 ml-2">
                        {scene.shots.map((shot, shotIdx) => (
                          <div
                            key={shot.id}
                            className="rounded-lg border border-slate-700 bg-slate-900/50 p-3 text-sm"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="font-mono text-slate-400">
                                  Shot {shotIdx + 1}
                                </div>
                                <p className="mt-1 line-clamp-2 text-slate-300">
                                  {shot.prompt}
                                </p>
                              </div>
                              <div
                                className={cn(
                                  "ml-2 rounded-full px-2 py-1 text-xs font-medium whitespace-nowrap",
                                  shot.status === "done"
                                    ? "bg-green-500/20 text-green-400"
                                    : shot.status === "running"
                                      ? "bg-yellow-500/20 text-yellow-400"
                                      : shot.status === "failed"
                                        ? "bg-red-500/20 text-red-400"
                                        : "bg-slate-700 text-slate-300"
                                )}
                              >
                                {shot.status}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={handleGenerateAll}
                className={cn(
                  "mt-4 w-full rounded-lg px-4 py-2 font-medium transition-all",
                  project.scenes.length === 0 || generating
                    ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                    : "bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600"
                )}
                disabled={project.scenes.length === 0 || generating}
              >
                {generating ? "Generating..." : "Generate All"}
              </button>
            </div>
          </div>

          {/* Right panel - Preview / Progress */}
          <div className="lg:col-span-1">
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">
                {generationProgress.stitch_complete ? "Film" : "Preview"}
              </h2>

              {generationProgress.stitch_start ? (
                // Generation in progress
                <div className="space-y-4">
                  <div className="rounded-lg bg-slate-900 aspect-video flex items-center justify-center flex-col gap-4 p-6">
                    <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-700 border-t-cyan-500" />
                    <div className="text-center">
                      <p className="text-white font-semibold">
                        {generationProgress.stitch_progress?.message || "Generating..."}
                      </p>
                      {generationProgress.shot_progress && (
                        <p className="text-sm text-slate-400 mt-2">
                          {generationProgress.shot_progress.message}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ) : project.output_url ? (
                // Film ready
                <div className="space-y-4">
                  <div className="rounded-lg bg-slate-900 aspect-video flex items-center justify-center">
                    <video
                      src={project.output_url}
                      controls
                      className="w-full h-full rounded-lg"
                    />
                  </div>
                  <a
                    href={project.output_url}
                    download
                    className="block w-full rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 px-4 py-2 text-center text-white font-medium hover:from-blue-600 hover:to-purple-600 transition-all"
                  >
                    Download Film
                  </a>
                </div>
              ) : (
                // No film yet
                <div className="rounded-lg border border-slate-700 border-dashed px-4 py-12 text-center">
                  <div className="h-32 bg-gradient-to-br from-slate-700 to-slate-900 rounded-lg mb-4" />
                  <p className="text-slate-400">Film preview will appear here</p>
                  <p className="text-sm text-slate-500 mt-2">Generate all shots to create the final film</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
