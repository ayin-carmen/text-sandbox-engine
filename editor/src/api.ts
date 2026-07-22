export type SceneRecord = {
  id: string;
  path: string;
  revision: string;
  document: Record<string, unknown>;
};

export type Diagnostic = {
  severity: string;
  code: string;
  message: string;
  file?: string | null;
  json_path: string;
  scene_id?: string;
};

export type GraphData = {
  nodes: Array<{ id: string; type: string; label: string; path?: string }>;
  edges: Array<{ id: string; source: string; target: string; relation: string; json_path: string; path: string }>;
};

export type RegistryItem = {
  kind: "command" | "rule" | "effect";
  type_id: string;
  label: string;
  category: string;
  description: string;
  module: string;
  module_version: string;
  reads?: string[];
  writes?: string[];
  parameters: Array<{
    name: string;
    label: string;
    data_type: string;
    widget: "boolean" | "integer" | "number" | "text" | "reference_select" | string;
    reference_type?: "actor" | "location" | "item" | "quest" | "scene" | "flag";
    required: boolean;
    default: unknown;
    description: string;
    enum?: string[];
  }>;
};

export type ReferenceItem = {
  id: string;
  type: "actor" | "location" | "item" | "quest" | "scene" | "flag";
  label: string;
  source: string;
  valid: boolean;
};

const base = import.meta.env.DEV ? "" : "http://127.0.0.1:8765";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? body?.detail ?? `请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  open: (root: string) => request<{ root: string; content_root: string; state_path: string; scene_count: number }>("/api/workspaces/open", { method: "POST", body: JSON.stringify({ root }) }),
  tree: () => request<{ entries: Array<{ path: string; kind: string; revision: string }> }>("/api/workspaces/tree"),
  sourceState: () => request<{ state: Record<string, unknown>; path: string; revision: string }>("/api/workspaces/state"),
  scenes: () => request<{ scenes: SceneRecord[] }>("/api/content/scenes"),
  saveScene: (sceneId: string, document: Record<string, unknown>, revision: string) => request<SceneRecord>(`/api/content/scenes/${encodeURIComponent(sceneId)}`, { method: "PUT", body: JSON.stringify({ document, revision }) }),
  createScene: (document: Record<string, unknown>) => request<SceneRecord>("/api/content/scenes", { method: "POST", body: JSON.stringify({ document }) }),
  duplicateScene: (sceneId: string, newSceneId: string, revision: string) => request<SceneRecord>(`/api/content/scenes/${encodeURIComponent(sceneId)}/duplicate`, { method: "POST", body: JSON.stringify({ new_scene_id: newSceneId, revision }) }),
  renameScene: (sceneId: string, newSceneId: string, revision: string) => request<SceneRecord>(`/api/content/scenes/${encodeURIComponent(sceneId)}/rename`, { method: "POST", body: JSON.stringify({ new_scene_id: newSceneId, revision }) }),
  deleteScene: (sceneId: string, revision: string) => request<{ deleted: string }>(`/api/content/scenes/${encodeURIComponent(sceneId)}?revision=${encodeURIComponent(revision)}`, { method: "DELETE" }),
  validate: () => request<{ passed: boolean; issues: Diagnostic[]; scene_count: number }>("/api/validation/content", { method: "POST" }),
  graph: () => request<GraphData>("/api/graph/content"),
  registry: () => request<{ items: RegistryItem[] }>("/api/metadata/registry"),
  references: (type?: ReferenceItem["type"]) => request<{ references: ReferenceItem[] }>(`/api/metadata/references${type ? `?type=${encodeURIComponent(type)}` : ""}`),
  createSession: () => request<{ session_id: string; state: Record<string, unknown>; traces: unknown[] }>("/api/runtime/sessions", { method: "POST" }),
  command: (sessionId: string, command: Record<string, unknown>) => request<{ status: string; trace: Record<string, unknown>; state: Record<string, unknown>; traces: unknown[] }>(`/api/runtime/sessions/${sessionId}/commands`, { method: "POST", body: JSON.stringify({ command }) }),
  candidates: (sessionId?: string) => request<Record<string, unknown>>("/api/diagnostics/scene-candidates", { method: "POST", body: JSON.stringify({ session_id: sessionId ?? null }) }),
  stateDiff: (before: Record<string, unknown>, after: Record<string, unknown>) => request<{ changes: Array<Record<string, unknown>> }>("/api/diagnostics/state-diff", { method: "POST", body: JSON.stringify({ before, after }) }),
  changedBy: (trace: Record<string, unknown>, path: string) => request<{ matches: Array<Record<string, unknown>> }>("/api/diagnostics/changed-by", { method: "POST", body: JSON.stringify({ trace, path }) }),
};
