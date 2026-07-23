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
  suggestion?: string;
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

export type SceneTemplate = {
  id: string;
  label: string;
  description: string;
  document: Record<string, unknown>;
};

export type RuntimeAction = {
  id: string;
  kind: "travel" | "choice" | string;
  label: string;
  description?: string;
  enabled: boolean;
  reason?: string;
  command: Record<string, unknown>;
};

export type RuntimeActions = {
  actor: { id: string; label: string };
  location: { id: string | null; label: string | null };
  time: { day?: number; period?: string; tick?: number };
  scene: { id: string; text: string; choices: Array<{ index: number; text: string; visible: boolean; reason: string }> } | null;
  available_locations: Array<{ id: string; label: string; action_id: string }>;
  actions: RuntimeAction[];
};

export type RuntimeSummary = {
  headline: string;
  lines: string[];
  changes: Array<{ path: string; before: unknown; after: unknown; label: string }>;
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
  validateDocument: (document: Record<string, unknown>) => request<{ passed: boolean; issues: Diagnostic[] }>("/api/validation/document", { method: "POST", body: JSON.stringify({ document }) }),
  graph: () => request<GraphData>("/api/graph/content"),
  registry: () => request<{ items: RegistryItem[] }>("/api/metadata/registry"),
  references: (type?: ReferenceItem["type"]) => request<{ references: ReferenceItem[] }>(`/api/metadata/references${type ? `?type=${encodeURIComponent(type)}` : ""}`),
  sceneTemplates: () => request<{ templates: SceneTemplate[] }>("/api/metadata/scene-templates"),
  sceneFromTemplate: (payload: { name: string; namespace: string; slug: string; location: string; template: string; repeat_policy: string; priority: number; preview: boolean }) => request<{ id: string; requested_id: string; template: string; document: Record<string, unknown>; issues: Diagnostic[]; passed: boolean; conflict_resolved: boolean; scene?: SceneRecord }>("/api/content/scenes/from-template", { method: "POST", body: JSON.stringify(payload) }),
  createSession: () => request<{ session_id: string; state: Record<string, unknown>; traces: unknown[]; actions?: RuntimeActions }>("/api/runtime/sessions", { method: "POST" }),
  command: (sessionId: string, command: Record<string, unknown>) => request<{ status: string; trace: Record<string, unknown>; state: Record<string, unknown>; traces: unknown[]; summary: RuntimeSummary }>(`/api/runtime/sessions/${sessionId}/commands`, { method: "POST", body: JSON.stringify({ command }) }),
  sessionActions: (sessionId: string) => request<RuntimeActions>(`/api/runtime/sessions/${sessionId}/actions`),
  resetSession: (sessionId: string) => request<{ session_id: string; state: Record<string, unknown>; traces: unknown[] }>(`/api/runtime/sessions/${sessionId}/reset`, { method: "POST" }),
  candidates: (sessionId?: string) => request<Record<string, unknown>>("/api/diagnostics/scene-candidates", { method: "POST", body: JSON.stringify({ session_id: sessionId ?? null }) }),
  stateDiff: (before: Record<string, unknown>, after: Record<string, unknown>) => request<{ changes: Array<Record<string, unknown>> }>("/api/diagnostics/state-diff", { method: "POST", body: JSON.stringify({ before, after }) }),
  changedBy: (trace: Record<string, unknown>, path: string) => request<{ matches: Array<Record<string, unknown>> }>("/api/diagnostics/changed-by", { method: "POST", body: JSON.stringify({ trace, path }) }),
};
