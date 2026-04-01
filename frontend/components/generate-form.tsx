"use client";
import { useState, useEffect, useCallback } from "react";
import { api, type ModelInfo, type Job } from "@/lib/api";
import { useJobSocket, type JobUpdate } from "@/lib/useJobSocket";
import { cn } from "@/lib/utils";

interface Props {
  onJobStarted?: (job: Job) => void;
}

type PresetKey = "draft" | "balanced" | "quality";

type ImagePreset = {
  key: PresetKey;
  label: string;
  description: string;
  width: number;
  height: number;
  steps: number;
  cfgScale: number;
};

const PRESETS: ImagePreset[] = [
  { key: "draft", label: "Draft", description: "Fastest preview for prompt testing.", width: 512, height: 512, steps: 12, cfgScale: 5 },
  { key: "balanced", label: "Balanced", description: "Good default for most generations.", width: 768, height: 768, steps: 20, cfgScale: 7 },
  { key: "quality", label: "Quality", description: "Sharper results, but noticeably slower.", width: 1024, height: 1024, steps: 28, cfgScale: 7.5 },
];

export function GenerateForm({ onJobStarted }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [showNegative, setShowNegative] = useState(false);
  const [width, setWidth] = useState(768);
  const [height, setHeight] = useState(768);
  const [steps, setSteps] = useState(20);
  const [cfgScale, setCfgScale] = useState(7);
  const [preset, setPreset] = useState<PresetKey>("balanced");
  const [sourceImageBase64, setSourceImageBase64] = useState<string | null>(null);
  const [sourceImageName, setSourceImageName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getModels().then((res) => {
      const imageModels = res.models.image ?? [];
      setModels(imageModels);
      if (imageModels.length > 0) {
        setSelectedModel(imageModels[0].name);
      }
    });
  }, []);

  const isEditModel = selectedModel === "qwen-image-edit";

  useEffect(() => {
    if (isEditModel) {
      setPreset("balanced");
      setCfgScale((current) => (current === 7 ? 4 : current));
    }
  }, [isEditModel]);

  const handleJobUpdate = useCallback((update: JobUpdate) => {
    if (update.progress !== undefined) setProgress(update.progress);
    if (update.message) setStatusMessage(update.message);
    if (update.status === "done" || update.status === "failed" || update.status === "cancelled") {
      setLoading(false);
      setProgress(null);
      if (update.job_id || activeJobId) {
        api.getJob(update.job_id ?? activeJobId!).then((job) => {
          setActiveJob(job);
          onJobStarted?.(job);
        });
      }
    }
  }, [activeJobId, onJobStarted]);

  useJobSocket(activeJobId, handleJobUpdate);

  const currentModel = models.find((m) => m.name === selectedModel);
  const maxW = currentModel?.max_width ?? 2512;
  const maxH = currentModel?.max_height ?? 2512;

  function applyPreset(nextPreset: ImagePreset) {
    setPreset(nextPreset.key);
    setWidth(Math.min(nextPreset.width, maxW));
    setHeight(Math.min(nextPreset.height, maxH));
    setSteps(nextPreset.steps);
    setCfgScale(nextPreset.cfgScale);
  }

  function handleManualDimensionChange(setter: (v: number) => void, value: number) {
    setter(value);
    setPreset("balanced");
  }

  async function handleImageInput(file: File | null) {
    if (!file) {
      setSourceImageBase64(null);
      setSourceImageName(null);
      return;
    }
    const dataUrl = await readFileAsDataUrl(file);
    setSourceImageBase64(dataUrl);
    setSourceImageName(file.name);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim() || !selectedModel) return;
    if (isEditModel && !sourceImageBase64) {
      setError("Qwen Image Edit needs a source image.");
      return;
    }

    setError(null);
    setLoading(true);
    setActiveJob(null);
    setProgress(null);
    setStatusMessage("Queuing job...");

    try {
      const res = await api.createJob({
        type: "image",
        model: selectedModel,
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim(),
        params: {
          width,
          height,
          steps,
          cfg_scale: cfgScale,
          input_image_base64: sourceImageBase64,
          input_image_name: sourceImageName,
        },
      });
      setActiveJobId(res.job_id);
      setStatusMessage(isEditModel ? "Edit job queued — uploading source image to the worker..." : "Job queued — waiting for worker...");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit job");
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
          {models.map((m) => (
            <option key={m.name} value={m.name}>
              {m.display_name}
            </option>
          ))}
        </select>
      </div>

      {!isEditModel && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-foreground">Speed preset</label>
            <span className="text-xs text-muted-foreground">Draft is best while testing the server</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {PRESETS.map((option) => (
              <button
                key={option.key}
                type="button"
                onClick={() => applyPreset(option)}
                className={cn(
                  "rounded-md border px-3 py-2 text-left transition-colors",
                  preset === option.key
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                )}
              >
                <div className="text-sm font-medium">{option.label}</div>
                <div className="mt-1 text-[11px] leading-4">{option.description}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={isEditModel ? "Describe how the image should change..." : "Describe what you want to generate..."}
          rows={4}
          maxLength={2000}
          required
          className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
        />
        <span className="text-xs text-muted-foreground text-right">{prompt.length}/2000</span>
      </div>

      {isEditModel && (
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-foreground">Source image</label>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(e) => void handleImageInput(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-2 file:text-primary-foreground"
          />
          {sourceImageBase64 && (
            <div className="overflow-hidden rounded-lg border border-border bg-card/50 p-2">
              <img src={sourceImageBase64} alt="Source preview" className="max-h-56 w-full rounded object-contain" />
              {sourceImageName && <div className="mt-2 text-xs text-muted-foreground">{sourceImageName}</div>}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <button
          type="button"
          onClick={() => setShowNegative((v) => !v)}
          className="text-sm text-muted-foreground hover:text-foreground text-left flex items-center gap-1"
        >
          <span>{showNegative ? "▾" : "▸"}</span> Negative prompt
        </button>
        {showNegative && (
          <textarea
            value={negativePrompt}
            onChange={(e) => setNegativePrompt(e.target.value)}
            placeholder="Things to avoid in the output..."
            rows={2}
            maxLength={2000}
            className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
          />
        )}
      </div>

      <div className="rounded-lg border border-border bg-card/50 p-3 text-xs text-muted-foreground">
        {isEditModel
          ? "Qwen Image Edit keeps the source composition and applies your prompt as an edit instruction. Smaller images and fewer steps are better for quick iterations."
          : "Remote Qwen Image runs fastest after the first request. Keep the GPU API running, and use Draft for quick idea checks before bumping size and steps."}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <SliderField label={`Width: ${width}px`} value={width} min={64} max={maxW} step={64}
          onChange={(value) => handleManualDimensionChange(setWidth, value)} />
        <SliderField label={`Height: ${height}px`} value={height} min={64} max={maxH} step={64}
          onChange={(value) => handleManualDimensionChange(setHeight, value)} />
        <SliderField label={`Steps: ${steps}`} value={steps} min={1} max={100} step={1}
          onChange={(value) => { setSteps(value); setPreset("balanced"); }} />
        <SliderField label={`CFG Scale: ${cfgScale}`} value={cfgScale} min={1} max={30} step={0.5}
          onChange={(value) => { setCfgScale(value); setPreset("balanced"); }} />
      </div>

      {activeJob?.duration_seconds ? (
        <div className="text-xs text-muted-foreground">
          Last completed job took about {activeJob.duration_seconds.toFixed(1)}s.
        </div>
      ) : null}

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
        disabled={loading || !prompt.trim() || !selectedModel || (isEditModel && !sourceImageBase64)}
        className={cn(
          "bg-primary text-primary-foreground font-medium rounded-md py-2.5 text-sm transition-opacity",
          "disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
        )}
      >
        {loading ? (isEditModel ? "Editing..." : "Generating...") : (isEditModel ? "Edit Image" : "Generate")}
      </button>
    </form>
  );
}

function SliderField({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-primary"
      />
    </div>
  );
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Failed to read image file"));
    reader.readAsDataURL(file);
  });
}
