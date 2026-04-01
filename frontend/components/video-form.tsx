"use client";
import { useEffect, useCallback, useState } from "react";
import { api, type Job, type ModelInfo } from "@/lib/api";
import { useJobSocket, type JobUpdate } from "@/lib/useJobSocket";
import { cn } from "@/lib/utils";

interface Props {
  onJobStarted?: (job: Job) => void;
}

export function VideoForm({ onJobStarted }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [videoMode, setVideoMode] = useState<"t2v" | "i2v">("t2v");
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [width, setWidth] = useState(640);
  const [height, setHeight] = useState(640);
  const [numFrames, setNumFrames] = useState(81);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getModels().then((res) => {
      const videoModels = res.models.video ?? [];
      setModels(videoModels);
      if (videoModels.length > 0) {
        setSelectedModel(videoModels[0].name);
      }
    });
  }, []);

  const isWan = selectedModel === "wan-2.2";

  const handleImageChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onload = (event) => {
        setImagePreview(event.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
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

    if (videoMode === "i2v" && !imageFile) {
      setError("Please select an image for I2V mode");
      return;
    }

    setError(null);
    setLoading(true);
    setProgress(null);
    const modeLabel = videoMode === "t2v" ? "T2V" : "I2V";
    setStatusMessage(`Queueing ${modeLabel} video job...`);

    try {
      const params: any = { width, height, num_frames: numFrames };

      if (videoMode === "i2v" && imageFile) {
        const reader = new FileReader();
        reader.onload = async (event) => {
          const base64 = (event.target?.result as string).split(",")[1];
          params.input_image_base64 = base64;
          params.input_image_name = imageFile.name;

          try {
            const res = await api.createJob({
              type: "video",
              model: selectedModel,
              prompt: prompt.trim(),
              negative_prompt: negativePrompt.trim(),
              params,
            });
            setActiveJobId(res.job_id);
            setStatusMessage("I2V video job queued...");
          } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to submit job");
            setLoading(false);
          }
        };
        reader.readAsDataURL(imageFile);
      } else {
        const res = await api.createJob({
          type: "video",
          model: selectedModel,
          prompt: prompt.trim(),
          negative_prompt: negativePrompt.trim(),
          params,
        });
        setActiveJobId(res.job_id);
        setStatusMessage("T2V video job queued...");
      }
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
          {models.map((model) => (
            <option key={model.name} value={model.name}>
              {model.display_name}
            </option>
          ))}
        </select>
      </div>

      {isWan && (
        <div className="flex gap-3 border-b border-border pb-3">
          <button
            type="button"
            onClick={() => {
              setVideoMode("t2v");
              setImageFile(null);
              setImagePreview(null);
            }}
            className={cn(
              "px-4 py-2 rounded-md text-sm font-medium transition-colors",
              videoMode === "t2v"
                ? "bg-primary text-primary-foreground"
                : "bg-card border border-border text-foreground hover:bg-card/80"
            )}
          >
            Text-to-Video
          </button>
          <button
            type="button"
            onClick={() => setVideoMode("i2v")}
            className={cn(
              "px-4 py-2 rounded-md text-sm font-medium transition-colors",
              videoMode === "i2v"
                ? "bg-primary text-primary-foreground"
                : "bg-card border border-border text-foreground hover:bg-card/80"
            )}
          >
            Image-to-Video
          </button>
        </div>
      )}

      <div className="rounded-lg border border-border bg-card/50 p-3 text-xs text-muted-foreground">
        {isWan
          ? videoMode === "t2v"
            ? "Wan 2.2 Text-to-Video: Generate realistic videos from natural language descriptions."
            : "Wan 2.2 Image-to-Video: Transform static images into dynamic videos with motion."
          : "Video generation model selected."}
      </div>

      {videoMode === "i2v" && (
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-foreground">Input Image</label>
          <div className="flex flex-col gap-2">
            {imagePreview && (
              <img
                src={imagePreview}
                alt="Preview"
                className="w-full h-48 object-cover rounded-md border border-border"
              />
            )}
            <input
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground file:bg-primary file:text-primary-foreground file:border-0 file:rounded file:px-2 file:py-1 file:cursor-pointer"
            />
          </div>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={videoMode === "t2v" ? "Describe the scene, motion, and atmosphere..." : "Describe how the scene should evolve..."}
          rows={5}
          maxLength={2000}
          required
          className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Negative Prompt</label>
        <textarea
          value={negativePrompt}
          onChange={(e) => setNegativePrompt(e.target.value)}
          placeholder="Optional issues to avoid (blurry, distorted, etc)..."
          rows={2}
          maxLength={2000}
          className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4">
        <SliderField label={`Width: ${width}px`} value={width} min={512} max={1024} step={64} onChange={setWidth} />
        <SliderField label={`Height: ${height}px`} value={height} min={512} max={1024} step={64} onChange={setHeight} />
        <SliderField label={`Frames: ${numFrames}`} value={numFrames} min={9} max={161} step={8} onChange={setNumFrames} />
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
        disabled={loading || !prompt.trim() || !selectedModel || (videoMode === "i2v" && !imageFile)}
        className={cn(
          "bg-primary text-primary-foreground font-medium rounded-md py-2.5 text-sm transition-opacity",
          "disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
        )}
      >
        {loading ? "Rendering..." : videoMode === "t2v" ? "Generate Video" : "Generate from Image"}
      </button>
    </form>
  );
}

function SliderField({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void; }) {
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
