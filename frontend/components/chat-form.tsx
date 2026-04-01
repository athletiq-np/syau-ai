"use client";
import { useEffect, useCallback, useState } from "react";
import { api, type Job, type ModelInfo } from "@/lib/api";
import { useJobSocket, type JobUpdate } from "@/lib/useJobSocket";
import { cn } from "@/lib/utils";

interface Props {
  onJobStarted?: (job: Job) => void;
}

export function ChatForm({ onJobStarted }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getModels().then((res) => {
      const chatModels = res.models.chat ?? [];
      setModels(chatModels);
      if (chatModels.length > 0) {
        setSelectedModel(chatModels[0].name);
      }
    });
  }, []);

  const handleJobUpdate = useCallback((update: JobUpdate) => {
    if (update.progress !== undefined) {
      setProgress(update.progress);
    }
    if (update.message) {
      setStatusMessage(update.message);
    }
    if (update.status === "done" || update.status === "failed" || update.status === "cancelled") {
      setLoading(false);
      setProgress(null);
      if (update.job_id || activeJobId) {
        api.getJob(update.job_id ?? activeJobId!).then((job) => {
          onJobStarted?.(job);
        });
      }
    }
  }, [activeJobId, onJobStarted]);

  useJobSocket(activeJobId, handleJobUpdate);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim() || !selectedModel) {
      return;
    }

    setError(null);
    setLoading(true);
    setProgress(null);
    setStatusMessage("Queueing chat job...");

    try {
      const res = await api.createJob({
        type: "chat",
        model: selectedModel,
        prompt: prompt.trim(),
        params: { steps: 1 },
      });
      setActiveJobId(res.job_id);
      setStatusMessage("Generating response...");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit chat job");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Model</label>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          {models.map((model) => (
            <option key={model.name} value={model.name}>
              {model.display_name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask for a tagline, concept, caption, script, or creative direction..."
          rows={8}
          maxLength={2000}
          required
          className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
        />
        <span className="text-xs text-muted-foreground text-right">{prompt.length}/2000</span>
      </div>

      {error && (
        <div className="text-sm text-red-400 bg-red-950/30 border border-red-800 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {loading && statusMessage && (
        <div className="text-sm text-muted-foreground flex items-center gap-2">
          <span className="inline-block w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          {statusMessage}
          {progress !== null && <span className="ml-auto text-xs">{progress}%</span>}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !prompt.trim() || !selectedModel}
        className={cn(
          "bg-primary text-primary-foreground font-medium rounded-md py-2.5 text-sm transition-opacity",
          "disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
        )}
      >
        {loading ? "Thinking..." : "Generate Reply"}
      </button>
    </form>
  );
}
