import { useEffect, useMemo, useState } from "react";
import Editor from "@monaco-editor/react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import { ArrowDown, ArrowUp, Braces, CheckCircle2, CircleAlert, Copy, FileJson, FolderOpen, GitBranch, Play, RotateCcw, Save, Sparkles, Trash2 } from "lucide-react";
import { api, Diagnostic, GraphData, ReferenceItem, RegistryItem, RuntimeActions, RuntimeSummary, SceneRecord, SceneTemplate } from "./api";
import { ReferenceSelect } from "./LowCodeWidgets";
import { EntityWorkspace } from "./EntityWorkspace";

type Tab = "form" | "json" | "graph" | "runtime" | "state" | "entities";

function App() {
  const [root, setRoot] = useState("examples/medieval_town");
  const [workspace, setWorkspace] = useState<{ root: string; state_path: string; scene_count: number } | null>(null);
  const [scenes, setScenes] = useState<SceneRecord[]>([]);
  const [selected, setSelected] = useState<SceneRecord | null>(null);
  const [rawJson, setRawJson] = useState("");
  const [tab, setTab] = useState<Tab>("form");
  const [issues, setIssues] = useState<Diagnostic[]>([]);
  const [message, setMessage] = useState("等待打开工作区");
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [graphTypeFilter, setGraphTypeFilter] = useState("all");
  const [graphRelationFilter, setGraphRelationFilter] = useState("all");
  const [registryItems, setRegistryItems] = useState<RegistryItem[]>([]);
  const [references, setReferences] = useState<ReferenceItem[]>([]);
  const [sceneTemplates, setSceneTemplates] = useState<SceneTemplate[]>([]);
  const [entityRecords, setEntityRecords] = useState<import("./api").EntityRecord[]>([]);
  const [entityTemplates, setEntityTemplates] = useState<import("./api").EntityTemplate[]>([]);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [focusedPath, setFocusedPath] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<Record<string, unknown> | null>(null);
  const [stateDiff, setStateDiff] = useState<Record<string, unknown> | null>(null);
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null);
  const [candidates, setCandidates] = useState<Record<string, unknown> | null>(null);
  const [runtimeActions, setRuntimeActions] = useState<RuntimeActions | null>(null);
  const [runtimeSummary, setRuntimeSummary] = useState<RuntimeSummary | null>(null);
  const [runtimeBusy, setRuntimeBusy] = useState(false);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [changedByMatches, setChangedByMatches] = useState<Record<string, unknown>[]>([]);
  const [changedByPath, setChangedByPath] = useState("entities.actor.player.components.location.current");
  const [commandText, setCommandText] = useState(JSON.stringify({ type: "space.travel_to", actor: "actor.player", target: "location.market_square", args: {} }, null, 2));
  const isDirty = Boolean(selected && rawJson !== JSON.stringify(selected.document, null, 2));

  const refreshEntities = async () => {
    setEntityRecords((await api.entities()).entities);
  };

  useEffect(() => {
    if (!isDirty) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [isDirty]);

  const canDiscardDraft = () => !isDirty || window.confirm("当前场景有未保存修改，确定放弃并切换吗？");
  const selectScene = (scene: SceneRecord) => {
    if (!canDiscardDraft()) return;
    setSelected(scene);
    setTab("form");
  };

  const openWorkspace = async () => {
    if (!canDiscardDraft()) return;
    try {
      const result = await api.open(root);
      const sceneResult = await api.scenes();
      setWorkspace(result);
      setScenes(sceneResult.scenes);
      setSelected(sceneResult.scenes[0] ?? null);
      setGraph(await api.graph());
      setRegistryItems((await api.registry()).items);
      setReferences((await api.references()).references);
      setSceneTemplates((await api.sceneTemplates()).templates);
      await refreshEntities();
      setEntityTemplates((await api.entityTemplates()).templates);
      setState((await api.sourceState()).state);
      setSessionId(null);
      setRuntimeActions(null);
      setRuntimeSummary(null);
      setRuntimeError(null);
      setMessage(`已打开 ${result.root}`);
      setIssues([]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "打开工作区失败");
    }
  };

  useEffect(() => {
    if (selected) setRawJson(JSON.stringify(selected.document, null, 2));
  }, [selected]);

  useEffect(() => {
    if (!selected || !rawJson) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const document = JSON.parse(rawJson) as Record<string, unknown>;
        const result = await api.validateDocument(document);
        if (!cancelled) setIssues(result.issues);
      } catch (error) {
        if (!cancelled) setIssues([{ severity: "error", code: "content.invalid_json", message: error instanceof Error ? error.message : "JSON 语法无效", file: null, json_path: "$" }]);
      }
    }, 350);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [rawJson, selected?.id]);

  const validate = async () => {
    try {
      const result = await api.validate();
      setIssues(result.issues);
      setMessage(result.passed ? `校验通过：${result.scene_count} 个场景` : `发现 ${result.issues.length} 个问题`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "校验失败");
    }
  };

  const save = async () => {
    if (!selected) return;
    try {
      const document = JSON.parse(rawJson) as Record<string, unknown>;
      const validation = await api.validateDocument(document);
      setIssues(validation.issues);
      if (!validation.passed) {
        setMessage("当前文档存在错误，修复后才能保存");
        return;
      }
      const next = await api.saveScene(selected.id, document, selected.revision);
      setSelected(next);
      setScenes((items) => items.map((item) => item.id === next.id ? next : item));
      setGraph(await api.graph());
      setMessage("场景已安全保存，旧版本已备份");
      setIssues([]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败");
    }
  };

  const focusDiagnostic = (issue: Diagnostic) => {
    const path = issue.json_path.replace(/\.rule$|\.effect$|\.args\[\d+\]$/, "");
    setFocusedPath(path || "$");
    setTab("form");
  };

  const discardDraft = () => {
    if (!selected || !window.confirm("确定放弃当前场景的未保存修改吗？")) return;
    setRawJson(JSON.stringify(selected.document, null, 2));
    setMessage("已放弃未保存修改");
  };

  const create = async () => {
    if (!canDiscardDraft()) return;
    setWizardOpen(true);
  };

  const createFromTemplate = async (payload: { name: string; namespace: string; slug: string; location: string; template: string; repeat_policy: string; priority: number }) => {
    try {
      const result = await api.sceneFromTemplate({ ...payload, preview: false });
      if (!result.scene) throw new Error("场景创建结果缺少记录");
      setScenes((items) => [...items, result.scene!]);
      setSelected(result.scene);
      setGraph(await api.graph());
      setWizardOpen(false);
      setMessage(`已创建 ${result.id}`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "创建失败"); }
  };

  const duplicate = async () => {
    if (!selected) return;
    if (!canDiscardDraft()) return;
    const newId = window.prompt("新场景 ID", `${selected.id}_copy`);
    if (!newId) return;
    try {
      const next = await api.duplicateScene(selected.id, newId, selected.revision);
      setScenes((items) => [...items, next]);
      setSelected(next);
      setGraph(await api.graph());
      setMessage("已复制场景");
    } catch (error) { setMessage(error instanceof Error ? error.message : "复制失败"); }
  };

  const rename = async () => {
    if (!selected) return;
    if (!canDiscardDraft()) return;
    const newId = window.prompt("新的场景 ID", selected.id);
    if (!newId || newId === selected.id) return;
    try {
      const next = await api.renameScene(selected.id, newId, selected.revision);
      setScenes((items) => items.map((item) => item.id === selected.id ? next : item));
      setSelected(next);
      setGraph(await api.graph());
      setMessage("已重命名场景");
    } catch (error) { setMessage(error instanceof Error ? error.message : "重命名失败"); }
  };

  const remove = async () => {
    if (!selected || !window.confirm(`确认删除 ${selected.id}？`)) return;
    if (!canDiscardDraft()) return;
    try {
      await api.deleteScene(selected.id, selected.revision);
      const nextScenes = scenes.filter((item) => item.id !== selected.id);
      setScenes(nextScenes); setSelected(nextScenes[0] ?? null); setGraph(await api.graph()); setMessage("已删除场景");
    } catch (error) { setMessage(error instanceof Error ? error.message : "删除失败"); }
  };

  const startSession = async () => {
    if (runtimeBusy) return;
    setRuntimeBusy(true);
    setRuntimeError(null);
    try {
      const created = await api.createSession();
      setSessionId(created.session_id);
      setState(created.state);
      setTrace(null);
      setStateDiff(null);
      setCandidates(null);
      setRuntimeSummary(null);
      setRuntimeActions(created.actions ?? await api.sessionActions(created.session_id));
      setMessage("试玩会话已启动，操作列表来自真实引擎");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "未知错误";
      const message = `启动试玩失败：${detail}。请重启 Python API 后重试。`;
      setRuntimeError(message);
      setMessage(message);
    } finally {
      setRuntimeBusy(false);
    }
  };

  const resetSession = async () => {
    if (!sessionId) return;
    try {
      const result = await api.resetSession(sessionId);
      setState(result.state);
      setTrace(null);
      setStateDiff(null);
      setCandidates(null);
      setRuntimeSummary(null);
      setRuntimeActions(await api.sessionActions(sessionId));
      setMessage("试玩会话已重置");
    } catch (error) { setMessage(error instanceof Error ? error.message : "重置试玩失败"); }
  };

  const runCommand = async (commandOverride?: Record<string, unknown>) => {
    try {
      const command = commandOverride ?? JSON.parse(commandText) as Record<string, unknown>;
      let activeSessionId = sessionId;
      let beforeState = state;
      if (!activeSessionId) {
        const created = await api.createSession();
        activeSessionId = created.session_id;
        beforeState = created.state;
        setSessionId(activeSessionId);
        setState(created.state);
      }
      const result = await api.command(activeSessionId, command);
      setStateDiff(await api.stateDiff(beforeState ?? {}, result.state));
      setState(result.state);
      setTrace(result.trace);
      setCandidates(await api.candidates(activeSessionId));
      setRuntimeSummary(result.summary);
      setRuntimeActions(await api.sessionActions(activeSessionId));
      setMessage(result.status === "succeeded" ? "命令执行成功，源 world state 未被修改" : "命令执行失败，详情见 trace");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "回放失败");
    }
  };

  const inspectChangedBy = async () => {
    if (!trace) return;
    try {
      setChangedByMatches((await api.changedBy(trace, changedByPath)).matches);
      setMessage(`已查询字段来源：${changedByPath}`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Changed By 查询失败"); }
  };

  const formDocument = useMemo(() => {
    try { return JSON.parse(rawJson) as Record<string, any>; } catch { return {}; }
  }, [rawJson]);

  const updateField = (path: string, value: unknown) => {
    const next = structuredClone(formDocument);
    const parts = path.split(".");
    let cursor = next;
    parts.slice(0, -1).forEach((part) => { cursor[part] ??= {}; cursor = cursor[part]; });
    cursor[parts.at(-1)!] = value;
    setRawJson(JSON.stringify(next, null, 2));
  };

  const graphElements = graph ? [
    ...graph.nodes.filter((node) => graphTypeFilter === "all" || node.type === graphTypeFilter).map((node) => ({ data: node })),
    ...graph.edges.filter((edge) => graphRelationFilter === "all" || edge.relation === graphRelationFilter).map((edge) => ({ data: edge })),
  ] : [];
  const graphNodeTypes = [...new Set(graph?.nodes.map((node) => node.type) ?? [])];
  const graphRelations = [...new Set(graph?.edges.map((edge) => edge.relation) ?? [])];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><Sparkles size={18} /> Text Sandbox Editor <span className="version">阶段 8</span></div>
        <div className="workspace-open">
          <input aria-label="工作区路径" value={root} onChange={(event) => setRoot(event.target.value)} />
          <button className="primary" onClick={openWorkspace}><FolderOpen size={16} />打开</button>
        </div>
        <div className="top-actions">
          <button onClick={validate}><CheckCircle2 size={16} />校验</button>
          <button onClick={discardDraft} disabled={!isDirty}><RotateCcw size={16} />撤销草稿</button><button className="primary" onClick={save} disabled={!selected || !isDirty || issues.some((issue) => issue.severity === "error")}><Save size={16} />保存</button>
        </div>
      </header>
      <div className="statusbar"><span className={issues.length ? "status-error" : "status-ok"}>{issues.length ? <CircleAlert size={14} /> : <CheckCircle2 size={14} />}{message}</span>{workspace && <span>{workspace.scene_count} 个场景 · {workspace.state_path}</span>}</div>
      <main className="workspace-grid">
        <aside className="sidebar">
          <div className="panel-title">内容树</div>
          <div className="tree-group"><FolderOpen size={14} /> {workspace?.root ?? "未打开工作区"}</div>
          <div className="tree-label">scenes</div>
          {scenes.map((scene) => <button key={scene.id} className={`tree-item ${selected?.id === scene.id ? "selected" : ""}`} onClick={() => selectScene(scene)}><FileJson size={14} />{scene.id}</button>)}
          <div className="tree-label">运行文件</div>
          <div className="tree-file"><FileJson size={14} /> world_state.json</div>
          <div className="tree-file"><FileJson size={14} /> commands/vertical_slice.json</div>
          <button className="new-scene" onClick={create}>+ 新建场景</button>
        </aside>
        <section className="editor-column">
          <nav className="tabs" aria-label="编辑视图">
            <button className={tab === "form" ? "active" : ""} onClick={() => setTab("form")}>结构化表单</button>
            <button className={tab === "json" ? "active" : ""} onClick={() => setTab("json")}><Braces size={15} />JSON 源码</button>
            <button className={tab === "graph" ? "active" : ""} onClick={() => setTab("graph")}><GitBranch size={15} />关系图</button>
            <button className={tab === "runtime" ? "active" : ""} onClick={() => setTab("runtime")}><Play size={15} />运行预览</button>
            <button className={tab === "state" ? "active" : ""} onClick={() => setTab("state")}>World State</button>
            <button className={tab === "entities" ? "active" : ""} onClick={() => setTab("entities")}>世界实体</button>
          </nav>
          {!selected && <div className="empty">打开一个真实内容包开始编辑。</div>}
          {selected && tab === "form" && <SceneForm document={formDocument} updateField={updateField} registryItems={registryItems} references={references} focusedPath={focusedPath} />}
          {selected && tab === "json" && <div className="monaco-wrap"><Editor height="560px" language="json" theme="vs-dark" value={rawJson} onChange={(value) => setRawJson(value ?? "")} options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: "on" }} /></div>}
          {tab === "graph" && <div className="graph-view"><div className="viz-controls"><label>节点类型<select value={graphTypeFilter} onChange={(event) => setGraphTypeFilter(event.target.value)}><option value="all">全部</option>{graphNodeTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label><label>引用关系<select value={graphRelationFilter} onChange={(event) => setGraphRelationFilter(event.target.value)}><option value="all">全部</option>{graphRelations.map((relation) => <option key={relation} value={relation}>{relation}</option>)}</select></label></div><div className="graph-wrap"><CytoscapeComponent elements={graphElements} stylesheet={graphStyle} layout={{ name: "cose", animate: false }} style={{ width: "100%", height: "620px" }} cy={(instance: any) => instance.on("tap", "node", (event: any) => setMessage(`节点：${event.target.data("label")} · 类型：${event.target.data("type")}`))} /></div></div>}
          {tab === "runtime" && <RuntimePanel commandText={commandText} setCommandText={setCommandText} runCommand={runCommand} startSession={startSession} resetSession={resetSession} actions={runtimeActions} summary={runtimeSummary} trace={trace} candidates={candidates} stateDiff={stateDiff} changedByPath={changedByPath} setChangedByPath={setChangedByPath} inspectChangedBy={inspectChangedBy} changedByMatches={changedByMatches} busy={runtimeBusy} error={runtimeError} />}
          {tab === "state" && <div className="state-view"><pre>{JSON.stringify(state ?? {}, null, 2)}</pre></div>}
          {tab === "entities" && <EntityWorkspace entities={entityRecords} templates={entityTemplates} references={references} onRefresh={refreshEntities} onMessage={setMessage} />}
        </section>
        <aside className="inspector">
          <div className="panel-title">检查器</div>
          {selected ? <>
            <div className="inspector-section"><label>场景 ID</label><code>{selected.id}</code></div>
            <div className="inspector-section"><label>来源文件</label><span>{selected.path}</span></div>
            <div className="inspector-section"><label>修订标识</label><code>{selected.revision.slice(0, 12)}…</code></div>
            <div className="inspector-section"><label>JSON 路径</label><code>$.choices[0].effects</code></div>
            <div className="inspector-section"><label>关系</label><span>{graph?.edges.filter((edge) => edge.source === selected.id).length ?? 0} 条引用</span></div>
            {isDirty && <div className="draft-status">有未保存修改</div>}
            <div className="inspector-actions"><button onClick={duplicate}>复制</button><button onClick={rename}>重命名</button><button onClick={remove}>删除</button></div>
          </> : <span className="muted">选择一个场景</span>}
        </aside>
      </main>
      <section className="diagnostics">
        <div className="panel-title">问题与 Trace</div>
        {issues.length ? issues.map((issue, index) => <div className="diagnostic" role="button" tabIndex={0} key={`${issue.code}-${index}`} onClick={() => focusDiagnostic(issue)} onKeyDown={(event) => { if (event.key === "Enter") focusDiagnostic(issue); }}><CircleAlert size={14} /><code>{issue.code}</code><span>{issue.message}</span><span className="muted">{issue.file ?? "当前文档"} {issue.json_path}</span>{issue.suggestion && <span className="muted">建议：{issue.suggestion}</span>}</div>) : <div className="diagnostic-empty">暂无校验问题。运行预览结果会显示在“运行预览”视图中。</div>}
      </section>
      <SceneWizard open={wizardOpen} templates={sceneTemplates} references={references} onClose={() => setWizardOpen(false)} onCreate={createFromTemplate} />
    </div>
  );
}

function SceneWizard({ open, templates, references, onClose, onCreate }: { open: boolean; templates: SceneTemplate[]; references: ReferenceItem[]; onClose: () => void; onCreate: (payload: { name: string; namespace: string; slug: string; location: string; template: string; repeat_policy: string; priority: number }) => Promise<void> }) {
  const validLocations = references.filter((reference) => reference.type === "location" && reference.valid);
  const [name, setName] = useState("新的场景");
  const [namespace, setNamespace] = useState("greybrook");
  const [slug, setSlug] = useState("new_scene");
  const [location, setLocation] = useState("");
  const [template, setTemplate] = useState("blank");
  const [repeatPolicy, setRepeatPolicy] = useState("always");
  const [priority, setPriority] = useState(0);
  const [preview, setPreview] = useState<{ id: string; passed: boolean; issues: Diagnostic[]; conflict_resolved: boolean } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setName("新的场景");
    setNamespace("greybrook");
    setSlug("new_scene");
    setLocation(validLocations[0]?.id ?? "");
    setTemplate(templates[0]?.id ?? "blank");
    setRepeatPolicy("always");
    setPriority(0);
    setPreview(null);
    setError("");
  }, [open]);

  if (!open) return null;
  const payload = { name, namespace, slug, location, template, repeat_policy: repeatPolicy, priority };
  const previewTemplate = async () => {
    try {
      setError("");
      const result = await api.sceneFromTemplate({ ...payload, preview: true });
      setPreview(result);
    } catch (cause) {
      setPreview(null);
      setError(cause instanceof Error ? cause.message : "模板预览失败");
    }
  };
  const selectedTemplate = templates.find((item) => item.id === template);
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><div className="wizard-dialog" role="dialog" aria-modal="true" aria-labelledby="scene-wizard-title" onMouseDown={(event) => event.stopPropagation()}>
    <div className="wizard-header"><div><p className="eyebrow">SCENE WIZARD</p><h2 id="scene-wizard-title">新建场景</h2></div><button onClick={onClose} aria-label="关闭向导">×</button></div>
    <div className="wizard-grid">
      <label>场景名称<input value={name} onChange={(event) => { setName(event.target.value); setPreview(null); }} /></label>
      <label>命名空间<input value={namespace} onChange={(event) => { setNamespace(event.target.value); setPreview(null); }} placeholder="greybrook" /></label>
      <label>英文短标识<input value={slug} onChange={(event) => { setSlug(event.target.value); setPreview(null); }} placeholder="tavern_keeper_request" /></label>
      <label>所属地点<select value={location} onChange={(event) => { setLocation(event.target.value); setPreview(null); }}>{validLocations.map((item) => <option key={item.id} value={item.id}>{item.label} · {item.id}</option>)}</select></label>
      <label>场景模板<select value={template} onChange={(event) => { setTemplate(event.target.value); setPreview(null); }}>{templates.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select><small className="field-help">{selectedTemplate?.description ?? ""}</small></label>
      <label>重复策略<select value={repeatPolicy} onChange={(event) => { setRepeatPolicy(event.target.value); setPreview(null); }}><option value="always">always：可重复</option><option value="once">once：只触发一次</option><option value="cooldown">cooldown：冷却后可重复</option></select></label>
      <label>初始优先级<input type="number" value={priority} onChange={(event) => { setPriority(Number(event.target.value)); setPreview(null); }} /></label>
    </div>
    <div className="id-preview"><span>预览 ID</span><code>scene.{namespace || "namespace"}.{slug || "scene"}</code></div>
    {error && <div className="wizard-error">{error}</div>}
    {preview && <div className={`wizard-preview ${preview.passed ? "passed" : "failed"}`}><strong>{preview.passed ? "模板校验通过" : "模板校验失败"}</strong><span>将创建：{preview.id}{preview.conflict_resolved ? "（已避开重复 ID）" : ""}</span>{preview.issues.map((issue, index) => <span className="field-help" key={`${issue.code}-${index}`}>{issue.code}：{issue.message}</span>)}</div>}
    <div className="wizard-actions"><button onClick={onClose}>取消</button><button onClick={previewTemplate}>预览并校验</button><button className="primary" disabled={!preview?.passed} onClick={() => onCreate(payload)}>确认创建</button></div>
  </div></div>;
}

function SceneForm({ document, updateField, registryItems, references, focusedPath }: { document: Record<string, any>; updateField: (path: string, value: unknown) => void; registryItems: RegistryItem[]; references: ReferenceItem[]; focusedPath: string | null }) {
  const rules = registryItems.filter((item) => item.kind === "rule");
  const effects = registryItems.filter((item) => item.kind === "effect");
  const conditions = Array.isArray(document.conditions) ? document.conditions : [];
  const choices = Array.isArray(document.choices) ? document.choices : [];
  const updateCondition = (index: number, value: Record<string, unknown>) => updateField("conditions", conditions.map((item, itemIndex) => itemIndex === index ? value : item));
  const updateChoice = (index: number, value: Record<string, unknown>) => updateField("choices", choices.map((item, itemIndex) => itemIndex === index ? value : item));
  const defaultArgs = (item: RegistryItem | undefined) => item?.parameters.map((parameter) => parameter.default ?? "") ?? [];
  const findRule = (typeId: string) => rules.find((item) => item.type_id === typeId);
  const findEffect = (typeId: string) => effects.find((item) => item.type_id === typeId);
  const replaceConditionType = (index: number, typeId: string) => updateCondition(index, { ...conditions[index], rule: typeId, args: defaultArgs(findRule(typeId)) });
  const replaceVisibleConditionType = (choiceIndex: number, conditionIndex: number, typeId: string) => {
    const choice = choices[choiceIndex];
    const visibleIf = Array.isArray(choice.visible_if) ? choice.visible_if : [];
    updateChoice(choiceIndex, { ...choice, visible_if: visibleIf.map((item: any, index: number) => index === conditionIndex ? { ...item, rule: typeId, args: defaultArgs(findRule(typeId)) } : item) });
  };
  const replaceEffectType = (choiceIndex: number, effectIndex: number, typeId: string) => {
    const choice = choices[choiceIndex];
    const choiceEffects = Array.isArray(choice.effects) ? choice.effects : [];
    updateChoice(choiceIndex, { ...choice, effects: choiceEffects.map((item: any, index: number) => index === effectIndex ? { ...item, effect: typeId, args: defaultArgs(findEffect(typeId)) } : item) });
  };
  const shift = <T,>(items: T[], index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= items.length) return items;
    const next = [...items];
    [next[index], next[target]] = [next[target], next[index]];
    return next;
  };
  const updateConditions = (next: unknown[]) => updateField("conditions", next);
  const updateChoiceList = (next: unknown[]) => updateField("choices", next);
  const removeChoice = (index: number) => { if (choices.length > 1) updateChoiceList(choices.filter((_, itemIndex) => itemIndex !== index)); };
  useEffect(() => {
    if (!focusedPath) return;
    const target = globalThis.document.querySelector(`[data-json-path="${CSS.escape(focusedPath)}"]`);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("field-focused");
    const timer = window.setTimeout(() => target.classList.remove("field-focused"), 1600);
    return () => window.clearTimeout(timer);
  }, [focusedPath]);
  return <div className="form-view">
    <div className="form-header"><div><p className="eyebrow">SCENE</p><h1>{document.id ?? "未命名场景"}</h1></div><span className="badge">{document.repeat_policy ?? "always"}</span></div>
    {focusedPath && <div className="field-focus">已定位到：<code>{focusedPath}</code></div>}
    <div className="form-grid">
      <label>场景 ID<input value={document.id ?? ""} onChange={(event) => updateField("id", event.target.value)} /></label>
      <label>优先级<input type="number" value={document.priority ?? 0} onChange={(event) => updateField("priority", Number(event.target.value))} /></label>
      <label>地点<input value={document.scope?.location ?? ""} onChange={(event) => updateField("scope.location", event.target.value)} /></label>
      <label>重复策略<select value={document.repeat_policy ?? "always"} onChange={(event) => updateField("repeat_policy", event.target.value)}><option value="always">always</option><option value="once">once</option><option value="cooldown">cooldown</option></select></label>
    </div>
    <label className="wide-field">场景正文<textarea rows={6} value={document.text ?? ""} onChange={(event) => updateField("text", event.target.value)} /></label>
    <div className="subsection"><div className="subsection-title">条件规则 <span>{conditions.length}</span></div>
      {conditions.map((condition: any, index: number) => <div className="rule-row" data-json-path={`$.conditions[${index}]`} key={index}>
        <div className="rule-selector"><select value={condition.rule ?? ""} onChange={(event) => replaceConditionType(index, event.target.value)}>{condition.rule && !findRule(condition.rule) && <option value={condition.rule}>{condition.rule}（未知）</option>}{rules.map((rule) => <option key={rule.type_id} value={rule.type_id}>{rule.label} · {rule.type_id}</option>)}</select><span className="field-help">{findRule(condition.rule)?.description ?? "请在 JSON 高级模式中检查该规则。"}</span><div className="row-actions"><button title="复制条件" aria-label="复制条件" onClick={() => updateConditions([...conditions.slice(0, index + 1), structuredClone(condition), ...conditions.slice(index + 1)])}><Copy size={13} /></button><button title="上移条件" aria-label="上移条件" disabled={index === 0} onClick={() => updateConditions(shift(conditions, index, -1))}><ArrowUp size={13} /></button><button title="下移条件" aria-label="下移条件" disabled={index === conditions.length - 1} onClick={() => updateConditions(shift(conditions, index, 1))}><ArrowDown size={13} /></button><button title="删除条件" aria-label="删除条件" onClick={() => updateConditions(conditions.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={13} /></button></div></div>
        <ArgumentFields item={findRule(condition.rule)} args={condition.args ?? []} references={references} onChange={(args) => updateCondition(index, { ...condition, args })} />
      </div>)}
      <button onClick={() => updateField("conditions", [...conditions, { rule: rules[0]?.type_id ?? "flag.is_false", args: defaultArgs(rules[0]) }])}>+ 添加规则</button>
    </div>
    <div className="subsection"><div className="subsection-title">选项与效果 <span>{choices.length}</span></div>
      {choices.map((choice: any, choiceIndex: number) => <div className="choice-editor" key={choiceIndex}>
        <div className="choice-heading"><strong>选项 {choiceIndex + 1}</strong><div className="row-actions"><button title="复制选项" aria-label="复制选项" onClick={() => updateChoiceList([...choices.slice(0, choiceIndex + 1), structuredClone(choice), ...choices.slice(choiceIndex + 1)])}><Copy size={13} /></button><button title="上移选项" aria-label="上移选项" disabled={choiceIndex === 0} onClick={() => updateChoiceList(shift(choices, choiceIndex, -1))}><ArrowUp size={13} /></button><button title="下移选项" aria-label="下移选项" disabled={choiceIndex === choices.length - 1} onClick={() => updateChoiceList(shift(choices, choiceIndex, 1))}><ArrowDown size={13} /></button><button title="删除选项" aria-label="删除选项" disabled={choices.length <= 1} onClick={() => removeChoice(choiceIndex)}><Trash2 size={13} /></button></div></div>
        <label>选项文本<input value={choice.text ?? ""} onChange={(event) => updateChoice(choiceIndex, { ...choice, text: event.target.value })} /></label>
        <div className="choice-conditions"><div className="subsection-title">显示条件 <span>{choice.visible_if?.length ?? 0}</span></div>
          {(choice.visible_if ?? []).map((condition: any, conditionIndex: number) => <div className="rule-row" data-json-path={`$.choices[${choiceIndex}].visible_if[${conditionIndex}]`} key={conditionIndex}>
            <div className="rule-selector"><select value={condition.rule ?? ""} onChange={(event) => replaceVisibleConditionType(choiceIndex, conditionIndex, event.target.value)}>{condition.rule && !findRule(condition.rule) && <option value={condition.rule}>{condition.rule}（未知）</option>}{rules.map((rule) => <option key={rule.type_id} value={rule.type_id}>{rule.label} · {rule.type_id}</option>)}</select><span className="field-help">{findRule(condition.rule)?.description ?? "请在 JSON 高级模式中检查该规则。"}</span><div className="row-actions"><button title="复制显示条件" aria-label="复制显示条件" onClick={() => { const visibleIf = [...choice.visible_if.slice(0, conditionIndex + 1), structuredClone(condition), ...choice.visible_if.slice(conditionIndex + 1)]; updateChoice(choiceIndex, { ...choice, visible_if: visibleIf }); }}><Copy size={13} /></button><button title="上移显示条件" aria-label="上移显示条件" disabled={conditionIndex === 0} onClick={() => updateChoice(choiceIndex, { ...choice, visible_if: shift(choice.visible_if, conditionIndex, -1) })}><ArrowUp size={13} /></button><button title="下移显示条件" aria-label="下移显示条件" disabled={conditionIndex === choice.visible_if.length - 1} onClick={() => updateChoice(choiceIndex, { ...choice, visible_if: shift(choice.visible_if, conditionIndex, 1) })}><ArrowDown size={13} /></button><button title="删除显示条件" aria-label="删除显示条件" onClick={() => updateChoice(choiceIndex, { ...choice, visible_if: choice.visible_if.filter((_: unknown, itemIndex: number) => itemIndex !== conditionIndex) })}><Trash2 size={13} /></button></div></div>
            <ArgumentFields item={findRule(condition.rule)} args={condition.args ?? []} references={references} onChange={(args) => { const visibleIf = [...choice.visible_if]; visibleIf[conditionIndex] = { ...condition, args }; updateChoice(choiceIndex, { ...choice, visible_if: visibleIf }); }} />
          </div>)}
          <button onClick={() => updateChoice(choiceIndex, { ...choice, visible_if: [...(choice.visible_if ?? []), { rule: rules[0]?.type_id ?? "flag.is_false", args: defaultArgs(rules[0]) }] })}>+ 添加显示条件</button>
        </div>
        <div className="choice-effects"><div className="subsection-title">执行效果 <span>{choice.effects?.length ?? 0}</span></div>
          {(choice.effects ?? []).map((effect: any, effectIndex: number) => <div className="rule-row" data-json-path={`$.choices[${choiceIndex}].effects[${effectIndex}]`} key={effectIndex}>
            <div className="rule-selector"><select value={effect.effect ?? ""} onChange={(event) => replaceEffectType(choiceIndex, effectIndex, event.target.value)}>{effect.effect && !findEffect(effect.effect) && <option value={effect.effect}>{effect.effect}（未知）</option>}{effects.map((item) => <option key={item.type_id} value={item.type_id}>{item.label} · {item.type_id}</option>)}</select><span className="field-help">{findEffect(effect.effect)?.description ?? "请在 JSON 高级模式中检查该效果。"}</span><div className="row-actions"><button title="复制效果" aria-label="复制效果" onClick={() => { const next = [...choice.effects.slice(0, effectIndex + 1), structuredClone(effect), ...choice.effects.slice(effectIndex + 1)]; updateChoice(choiceIndex, { ...choice, effects: next }); }}><Copy size={13} /></button><button title="上移效果" aria-label="上移效果" disabled={effectIndex === 0} onClick={() => updateChoice(choiceIndex, { ...choice, effects: shift(choice.effects, effectIndex, -1) })}><ArrowUp size={13} /></button><button title="下移效果" aria-label="下移效果" disabled={effectIndex === choice.effects.length - 1} onClick={() => updateChoice(choiceIndex, { ...choice, effects: shift(choice.effects, effectIndex, 1) })}><ArrowDown size={13} /></button><button title="删除效果" aria-label="删除效果" onClick={() => updateChoice(choiceIndex, { ...choice, effects: choice.effects.filter((_: unknown, itemIndex: number) => itemIndex !== effectIndex) })}><Trash2 size={13} /></button></div></div>
            <ArgumentFields item={findEffect(effect.effect)} args={effect.args ?? []} references={references} onChange={(args) => { const next = [...choice.effects]; next[effectIndex] = { ...effect, args }; updateChoice(choiceIndex, { ...choice, effects: next }); }} />
          </div>)}
          <p className="field-help">效果按照从上到下的顺序执行。</p>
          <button onClick={() => updateChoice(choiceIndex, { ...choice, effects: [...(choice.effects ?? []), { effect: effects[0]?.type_id ?? "flag.set", args: defaultArgs(effects[0]) }] })}>+ 添加效果</button>
        </div>
      </div>)}
      <button onClick={() => updateField("choices", [...choices, { text: "新选项", effects: [] }])}>+ 添加选项</button>
    </div>
  </div>;
}

function ArgumentFields({ item, args, references, onChange }: { item?: RegistryItem; args: unknown[]; references: ReferenceItem[]; onChange: (args: unknown[]) => void }) {
  if (!item) return <div className="argument-fields"><span className="field-help">未知类型：请切换到 JSON 高级模式检查参数。</span></div>;
  return <div className="argument-fields">{item.parameters.map((parameter, index) => {
    const value = args[index] ?? parameter.default ?? "";
    const setValue = (next: unknown) => { const nextArgs = [...args]; nextArgs[index] = next; onChange(nextArgs); };
    const options = parameter.reference_type ? references.filter((reference) => reference.type === parameter.reference_type) : [];
    const current = String(value ?? "");
    return <label className="parameter-field" key={parameter.name}>
      <span>{parameter.label}{parameter.required ? " *" : ""}</span>
      {parameter.widget === "reference_select" ? <ReferenceSelect value={current} options={options} onChange={setValue} />
        : parameter.widget === "boolean" ? <input type="checkbox" checked={Boolean(value)} onChange={(event) => setValue(event.target.checked)} />
          : parameter.widget === "integer" || parameter.widget === "number" ? <input type="number" step={parameter.widget === "integer" ? 1 : "any"} value={value as number} onChange={(event) => setValue(event.target.value === "" ? "" : Number(event.target.value))} />
            : <input value={String(value)} onChange={(event) => setValue(event.target.value)} />}
      <small className="field-help">{parameter.description}{parameter.reference_type ? ` · 来源：${parameter.reference_type}` : ""}</small>
    </label>;
  })}</div>;
}

function RuntimePanel({ commandText, setCommandText, runCommand, startSession, resetSession, actions, summary, trace, candidates, stateDiff, changedByPath, setChangedByPath, inspectChangedBy, changedByMatches, busy, error }: { commandText: string; setCommandText: (value: string) => void; runCommand: (command?: Record<string, unknown>) => void; startSession: () => void; resetSession: () => void; actions: RuntimeActions | null; summary: RuntimeSummary | null; trace: Record<string, unknown> | null; candidates: Record<string, unknown> | null; stateDiff: Record<string, unknown> | null; changedByPath: string; setChangedByPath: (value: string) => void; inspectChangedBy: () => void; changedByMatches: Record<string, unknown>[]; busy: boolean; error: string | null }) {
  const travelActions = actions?.actions.filter((action) => action.kind === "travel") ?? [];
  const choiceActions = actions?.actions.filter((action) => action.kind === "choice") ?? [];
  return <div className="runtime-view">
    <div className="runtime-toolbar"><div><p className="eyebrow">ISOLATED SESSION</p><h1>试玩控制台</h1></div>{actions ? <button onClick={resetSession}><RotateCcw size={16} />重置会话</button> : <button className="primary" disabled={busy} onClick={startSession}><Play size={16} />{busy ? "启动中..." : "启动试玩"}</button>}</div>
    {error && <div className="play-error" role="alert">{error}</div>}
    {!actions && <div className="play-empty">启动后，操作按钮会由 Python 引擎根据当前世界状态生成。</div>}
    {actions && <>
      <div className="play-context"><span>角色：{actions.actor.label}</span><span>地点：{actions.location.label ?? actions.location.id}</span><span>时间：第 {actions.time.day ?? "-"} 天 · {actions.time.period ?? "-"} · 刻度 {actions.time.tick ?? "-"}</span></div>
      {actions.scene && <section className="play-scene"><p className="eyebrow">CURRENT SCENE</p><h2>{actions.scene.id}</h2><p className="scene-copy">{actions.scene.text}</p><div className="play-actions">{choiceActions.map((action) => <button className="play-action" key={action.id} disabled={!action.enabled} onClick={() => runCommand(action.command)}><Play size={14} />{action.label}</button>)}</div></section>}
      <section className="play-section"><div className="subsection-title">可前往地点 <span>{travelActions.length}</span></div><div className="play-actions">{travelActions.map((action) => <button className="play-action" key={action.id} disabled={!action.enabled} onClick={() => runCommand(action.command)}>{action.label}</button>)}</div>{!travelActions.length && <span className="field-help">当前地点没有可用移动操作。</span>}</section>
      {summary && <section className="play-summary"><h2>{summary.headline}</h2>{summary.lines.length ? <ul>{summary.lines.map((line, index) => <li key={`${line}-${index}`}>{line}</li>)}</ul> : <span className="field-help">没有状态字段变化。</span>}</section>}
      <details className="advanced-details"><summary>高级详情</summary><textarea className="command-editor" value={commandText} onChange={(event) => setCommandText(event.target.value)} aria-label="命令 JSON" /><button className="primary" onClick={() => runCommand()}><Play size={15} />执行 JSON 命令</button><div className="runtime-results"><div><h2>Trace</h2><pre>{JSON.stringify(trace ?? {}, null, 2)}</pre></div><div><h2>场景候选</h2><pre>{JSON.stringify(candidates ?? {}, null, 2)}</pre></div><div><h2>State Diff</h2><pre>{JSON.stringify(stateDiff ?? {}, null, 2)}</pre></div><div><h2>Changed By</h2><div className="changed-by-controls"><input value={changedByPath} onChange={(event) => setChangedByPath(event.target.value)} aria-label="状态字段路径" /><button onClick={inspectChangedBy}>查询</button></div><pre>{JSON.stringify(changedByMatches, null, 2)}</pre></div></div></details>
    </>}
  </div>;
}

const graphStyle: any[] = [
  { selector: "node", style: { label: "data(label)", "font-size": 10, "background-color": "#5b6b8c", color: "#f7f4ec", "text-valign": "center", "text-halign": "center", width: 34, height: 34, "border-width": 1, "border-color": "#c7d2e6" } },
  { selector: 'node[type="scene"]', style: { "background-color": "#b85c38", width: 46, height: 46 } },
  { selector: 'node[type="effect"]', style: { "background-color": "#357a72" } },
  { selector: 'node[type="rule"]', style: { "background-color": "#7a5c9e" } },
  { selector: "edge", style: { width: 1, "line-color": "#9aa5b5", "target-arrow-color": "#9aa5b5", "target-arrow-shape": "triangle", label: "data(relation)", "font-size": 8, color: "#697386", "curve-style": "bezier" } },
];

export default App;
