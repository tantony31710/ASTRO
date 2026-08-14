const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ---- types ----

export interface DiskUsage {
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent_used: number;
  low_space_warning: boolean;
}

export interface ZoneSize {
  zone: string;
  path: string;
  exists: boolean;
  size_gb: number;
  file_count: number;
}

export interface TreeNode {
  name: string;
  type: "file" | "folder";
  size_bytes: number;
  children?: TreeNode[];
}

export interface CleanupResult {
  cleared_count: number;
  freed_bytes: number;
  errors: string[];
}

export interface RawVideo {
  name: string;
  size_mb: number;
  proxy_exists: boolean;
}

export interface Proxy {
  name: string;
  size_mb: number;
}

export interface TranscodeJob {
  id: string;
  type: string;
  status: "running" | "done" | "error";
  progress: number;
  total: number;
  current_item: string | null;
  result: { processed: number; total: number; failures: string[] } | null;
  error: string | null;
}

export interface WeightSummary {
  name: string;
  extension: string;
  size_mb: number;
  inspectable: boolean;
  tensor_count: number | null;
  dtype_breakdown: Record<string, number> | null;
}

export interface WeightDetail extends WeightSummary {
  metadata: Record<string, string>;
  tensors: { name: string; dtype: string; shape: number[] }[];
}

// ---- storage ----

export const getDiskUsage = () => request<DiskUsage>("/storage/disk");
export const getZoneSizes = () => request<ZoneSize[]>("/storage/zones");
export const getDirTree = (path = ".", depth = 2) =>
  request<TreeNode>(`/storage/tree?path=${encodeURIComponent(path)}&depth=${depth}`);
export const cleanupScratch = () =>
  request<CleanupResult>("/storage/cleanup", { method: "POST" });

// ---- media ----

export const getRawVideos = () => request<RawVideo[]>("/media/raw");
export const getProxies = () => request<Proxy[]>("/media/proxies");
export const startTranscode = () =>
  request<{ job_id: string }>("/media/transcode/start", { method: "POST" });
export const getJobStatus = (jobId: string) =>
  request<TranscodeJob>(`/media/jobs/${jobId}`);

// ---- models ----

export const getWeights = () => request<WeightSummary[]>("/models/weights");
export const getWeightDetail = (filename: string) =>
  request<WeightDetail>(`/models/weights/${encodeURIComponent(filename)}`);

// ---- assistant ----

export interface ChatReply {
  reply: string;
  matched_tool: string | null;
}

export const sendChat = (message: string) =>
  request<ChatReply>("/chat", { method: "POST", body: JSON.stringify({ message }) });
