const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "syauai_dev_key_12345"; // Default for dev

/**
 * Auth error handler - can be used globally
 */
export class AuthError extends Error {
  constructor(message: string, public statusCode: number = 403) {
    super(message);
    this.name = "AuthError";
  }
}

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

export interface Character {
  id: string;
  project_id: string;
  name: string;
  description: string;
  reference_url: string | null;
  created_at: string;
}

export interface Shot {
  id: string;
  scene_id: string;
  project_id: string;
  order_index: number;
  shot_type: "t2v" | "i2v";
  status: "pending" | "running" | "done" | "failed";
  prompt: string;
  negative_prompt: string;
  duration_frames: number;
  width: number;
  height: number;
  seed: number | null;
  character_ids: string[];
  output_url: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface Scene {
  id: string;
  project_id: string;
  order_index: number;
  title: string;
  description: string;
  shots: Shot[];
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  description: string;
  status: "draft" | "processing" | "done" | "failed";
  total_shots: number;
  output_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail {
  id: string;
  title: string;
  description: string;
  status: "draft" | "processing" | "done" | "failed";
  script: string;
  total_shots: number;
  output_url: string | null;
  characters: Character[];
  scenes: Scene[];
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});

  // Add default headers
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  // Add authorization header with API key
  if (!headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${API_KEY}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    const body = await res.text();

    // Handle auth errors specifically
    if (res.status === 403) {
      throw new AuthError(`API Authentication Failed: ${body}`, 403);
    }

    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json();
}

export const api = {
  // --- Jobs API ---
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
    fetch(`${API_BASE}/jobs/${id}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${API_KEY}` },
    }),

  getModels: () => request<ModelsResponse>("/models"),

  // --- Projects API ---
  createProject: (data: { title: string; description: string; script: string }) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listProjects: (params?: { page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return request<ProjectListResponse>(`/projects?${qs}`);
  },

  getProject: (id: string) => request<ProjectDetail>(`/projects/${id}`),

  updateProject: (id: string, data: { title?: string; description?: string; script?: string }) =>
    request<Project>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  updateShot: (projectId: string, shotId: string, data: { prompt?: string; negative_prompt?: string }) => {
    const qs = new URLSearchParams();
    if (data.prompt !== undefined) qs.set("prompt", data.prompt);
    if (data.negative_prompt !== undefined) qs.set("negative_prompt", data.negative_prompt);
    return request<Shot>(`/projects/${projectId}/shots/${shotId}?${qs.toString()}`, {
      method: "PATCH",
    });
  },

  deleteProject: (id: string) =>
    fetch(`${API_BASE}/projects/${id}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${API_KEY}` },
    }),

  analyzeScript: (projectId: string) =>
    request<{ scenes: any[] }>(`/projects/${projectId}/script`, {
      method: "POST",
    }),

  generateProject: (projectId: string) =>
    request<{ status: string; project_id: string; shot_count: number; message: string }>(`/projects/${projectId}/generate`, {
      method: "POST",
    }),

  deleteShot: (projectId: string, shotId: string) =>
    fetch(`/api/projects/${projectId}/shots/${shotId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${API_KEY}` },
    }),

  uploadReferenceImage: (projectId: string, sceneId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`/api/projects/${projectId}/scenes/${sceneId}/reference-image`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${API_KEY}` },
      body: formData,
    });
  },
};
