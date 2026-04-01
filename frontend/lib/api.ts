const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface JobParams {
  width?: number;
  height?: number;
  steps?: number;
  cfg_scale?: number;
  seed?: number | null;
  num_frames?: number;
  input_image_base64?: string | null;
  input_image_name?: string | null;
}

export interface JobCreate {
  type: "image" | "video" | "chat";
  model: string;
  prompt: string;
  negative_prompt?: string;
  params?: JobParams;
}

export interface Job {
  id: string;
  status: "pending" | "running" | "done" | "failed" | "cancelled";
  type: string;
  model: string;
  prompt: string;
  negative_prompt: string;
  params: JobParams;
  output_keys: string[] | null;
  output_urls: string[] | null;
  output_text?: string | null;
  seed_used: number | null;
  duration_seconds: number | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ModelInfo {
  id: string;
  name: string;
  display_name: string;
  type: string;
  is_enabled: boolean;
  max_width: number | null;
  max_height: number | null;
}

export interface ModelsResponse {
  models: Record<string, ModelInfo[]>;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  createJob: (data: JobCreate) =>
    request<{ job_id: string; status: string }>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getJob: (id: string) => request<Job>(`/jobs/${id}`),

  listJobs: (params?: { page?: number; page_size?: number; type?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    if (params?.type) qs.set("type", params.type);
    if (params?.status) qs.set("status", params.status);
    return request<JobListResponse>(`/jobs?${qs}`);
  },

  cancelJob: (id: string) =>
    fetch(`${API_BASE}/jobs/${id}`, { method: "DELETE" }),

  getModels: () => request<ModelsResponse>("/models"),
};
