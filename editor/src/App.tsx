import { useEffect, useMemo, useState } from "react";
import Editor from "@monaco-editor/react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import { Braces, CheckCircle2, CircleAlert, FileJson, FolderOpen, GitBranch, Play, Save, Sparkles } from "lucide-react";
import { api, Diagnostic, GraphData, RegistryItem, SceneRecord } from "./api";

type Tab = "form" | "json" | "graph" | "runtime" | "state";

const blankScene = {
  id: "scene.greybrook.new_scene",
  scope: { location: "location.market_square" },
  priority: 0,
  conditions: [],
  text: "在这里写下场景正文。",
  choices: [{ text: "继续", effects: [] }],
  repeat_policy: "always",
};

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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<Record<string, unknown> | null>(null);
  const [stateDiff, setStateDiff] = useState<Record<string, unknown> | null>(null);
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null);
  const [candidates, setCandidates] = useState<Record<string, unknown> | null>(null);
  const [changedByMatches, setChangedByMatches] = useState<Record<string, unknown>[]>([]);
  const [changedByPath, setChangedByPath] = useState("entities.actor.player.components.location.current");
  const [commandText, setCommandText] = useState(JSON.stringify({ type: "space.travel_to", actor: "actor.player", target: "location.market_square", args: {} }, null, 2));

  const openWorkspace = async () => {
    try {
      const result = await api.open(root);
      const sceneResult = await api.scenes();
      setWorkspace(result);
      setScenes(sceneResult.scenes);
      setSelected(sceneResult.scenes[0] ?? null);
      setGraph(await api.graph());
      setRegistryItems((await api.registry()).items);
      setState((await api.sourceState()).state);
      setMessage(`已打开 ${result.root}`);
      setIssues([]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "打开工作区失败");
    }
  };

  useEffect(() => {
    if (selected) setRawJson(JSON.stringify(selected.document, null, 2));
  }, [selected]);

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

  const create = async () => {
    try {
      const next = await api.createScene(blankScene);
      setScenes((items) => [...items, next]);
      setSelected(next);
      setGraph(await api.graph());
      setMessage("已创建新场景");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "创建失败");
    }
  };

  const duplicate = async () => {
    if (!selected) return;
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
    try {
      await api.deleteScene(selected.id, selected.revision);
      const nextScenes = scenes.filter((item) => item.id !== selected.id);
      setScenes(nextScenes); setSelected(nextScenes[0] ?? null); setGraph(await api.graph()); setMessage("已删除场景");
    } catch (error) { setMessage(error instanceof Error ? error.message : "删除失败"); }
  };

  const runCommand = async () => {
    try {
      const command = JSON.parse(commandText) as Record<string, unknown>;
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
          <button className="primary" onClick={save} disabled={!selected}><Save size={16} />保存</button>
        </div>
      </header>
      <div className="statusbar"><span className={issues.length ? "status-error" : "status-ok"}>{issues.length ? <CircleAlert size={14} /> : <CheckCircle2 size={14} />}{message}</span>{workspace && <span>{workspace.scene_count} 个场景 · {workspace.state_path}</span>}</div>
      <main className="workspace-grid">
        <aside className="sidebar">
          <div className="panel-title">内容树</div>
          <div className="tree-group"><FolderOpen size={14} /> {workspace?.root ?? "未打开工作区"}</div>
          <div className="tree-label">scenes</div>
          {scenes.map((scene) => <button key={scene.id} className={`tree-item ${selected?.id === scene.id ? "selected" : ""}`} onClick={() => { setSelected(scene); setTab("form"); }}><FileJson size={14} />{scene.id}</button>)}
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
          </nav>
          {!selected && <div className="empty">打开一个真实内容包开始编辑。</div>}
          {selected && tab === "form" && <SceneForm document={formDocument} updateField={updateField} registryItems={registryItems} />}
          {selected && tab === "json" && <div className="monaco-wrap"><Editor height="560px" language="json" theme="vs-dark" value={rawJson} onChange={(value) => setRawJson(value ?? "")} options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: "on" }} /></div>}
          {tab === "graph" && <div className="graph-view"><div className="viz-controls"><label>节点类型<select value={graphTypeFilter} onChange={(event) => setGraphTypeFilter(event.target.value)}><option value="all">全部</option>{graphNodeTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label><label>引用关系<select value={graphRelationFilter} onChange={(event) => setGraphRelationFilter(event.target.value)}><option value="all">全部</option>{graphRelations.map((relation) => <option key={relation} value={relation}>{relation}</option>)}</select></label></div><div className="graph-wrap"><CytoscapeComponent elements={graphElements} stylesheet={graphStyle} layout={{ name: "cose", animate: false }} style={{ width: "100%", height: "620px" }} cy={(instance: any) => instance.on("tap", "node", (event: any) => setMessage(`节点：${event.target.data("label")} · 类型：${event.target.data("type")}`))} /></div></div>}
          {tab === "runtime" && <RuntimePanel commandText={commandText} setCommandText={setCommandText} runCommand={runCommand} trace={trace} candidates={candidates} stateDiff={stateDiff} changedByPath={changedByPath} setChangedByPath={setChangedByPath} inspectChangedBy={inspectChangedBy} changedByMatches={changedByMatches} />}
          {tab === "state" && <div className="state-view"><pre>{JSON.stringify(state ?? {}, null, 2)}</pre></div>}
        </section>
        <aside className="inspector">
          <div className="panel-title">检查器</div>
          {selected ? <>
            <div className="inspector-section"><label>场景 ID</label><code>{selected.id}</code></div>
            <div className="inspector-section"><label>来源文件</label><span>{selected.path}</span></div>
            <div className="inspector-section"><label>修订标识</label><code>{selected.revision.slice(0, 12)}…</code></div>
            <div className="inspector-section"><label>JSON 路径</label><code>$.choices[0].effects</code></div>
            <div className="inspector-section"><label>关系</label><span>{graph?.edges.filter((edge) => edge.source === selected.id).length ?? 0} 条引用</span></div>
            <div className="inspector-actions"><button onClick={duplicate}>复制</button><button onClick={rename}>重命名</button><button onClick={remove}>删除</button></div>
          </> : <span className="muted">选择一个场景</span>}
        </aside>
      </main>
      <section className="diagnostics">
        <div className="panel-title">问题与 Trace</div>
        {issues.length ? issues.map((issue, index) => <div className="diagnostic" key={`${issue.code}-${index}`}><CircleAlert size={14} /><code>{issue.code}</code><span>{issue.message}</span><span className="muted">{issue.file ?? "当前文档"} {issue.json_path}</span></div>) : <div className="diagnostic-empty">暂无校验问题。运行预览结果会显示在“运行预览”视图中。</div>}
      </section>
    </div>
  );
}

function SceneForm({ document, updateField, registryItems }: { document: Record<string, any>; updateField: (path: string, value: unknown) => void; registryItems: RegistryItem[] }) {
  const rules = registryItems.filter((item) => item.kind === "rule");
  const effects = registryItems.filter((item) => item.kind === "effect");
  const conditions = Array.isArray(document.conditions) ? document.conditions : [];
  const choices = Array.isArray(document.choices) ? document.choices : [];
  const updateCondition = (index: number, value: Record<string, unknown>) => updateField("conditions", conditions.map((item, itemIndex) => itemIndex === index ? value : item));
  const updateChoice = (index: number, value: Record<string, unknown>) => updateField("choices", choices.map((item, itemIndex) => itemIndex === index ? value : item));
  const parseArgs = (value: string) => { try { return JSON.parse(value); } catch { return []; } };
  return <div className="form-view">
    <div className="form-header"><div><p className="eyebrow">SCENE</p><h1>{document.id ?? "未命名场景"}</h1></div><span className="badge">{document.repeat_policy ?? "always"}</span></div>
    <div className="form-grid">
      <label>场景 ID<input value={document.id ?? ""} onChange={(event) => updateField("id", event.target.value)} /></label>
      <label>优先级<input type="number" value={document.priority ?? 0} onChange={(event) => updateField("priority", Number(event.target.value))} /></label>
      <label>地点<input value={document.scope?.location ?? ""} onChange={(event) => updateField("scope.location", event.target.value)} /></label>
      <label>重复策略<select value={document.repeat_policy ?? "always"} onChange={(event) => updateField("repeat_policy", event.target.value)}><option value="always">always</option><option value="once">once</option><option value="cooldown">cooldown</option></select></label>
    </div>
    <label className="wide-field">场景正文<textarea rows={6} value={document.text ?? ""} onChange={(event) => updateField("text", event.target.value)} /></label>
    <div className="subsection"><div className="subsection-title">条件规则 <span>{conditions.length}</span></div>
      {conditions.map((condition: any, index: number) => <div className="rule-row" key={index}><select value={condition.rule ?? ""} onChange={(event) => updateCondition(index, { ...condition, rule: event.target.value })}>{rules.map((rule) => <option key={rule.type_id} value={rule.type_id}>{rule.type_id}</option>)}</select><input value={JSON.stringify(condition.args ?? [])} onChange={(event) => updateCondition(index, { ...condition, args: parseArgs(event.target.value) })} aria-label={`规则 ${index + 1} 参数`} /></div>)}
      <button onClick={() => updateField("conditions", [...conditions, { rule: rules[0]?.type_id ?? "flag.is_false", args: [] }])}>+ 添加规则</button>
    </div>
    <div className="subsection"><div className="subsection-title">选项与效果 <span>{choices.length}</span></div>
      {choices.map((choice: any, choiceIndex: number) => <div className="choice-editor" key={choiceIndex}><label>选项文本<input value={choice.text ?? ""} onChange={(event) => updateChoice(choiceIndex, { ...choice, text: event.target.value })} /></label>{(choice.effects ?? []).map((effect: any, effectIndex: number) => <div className="rule-row" key={effectIndex}><select value={effect.effect ?? ""} onChange={(event) => { const next = [...choice.effects]; next[effectIndex] = { ...effect, effect: event.target.value }; updateChoice(choiceIndex, { ...choice, effects: next }); }}>{effects.map((item) => <option key={item.type_id} value={item.type_id}>{item.type_id}</option>)}</select><input value={JSON.stringify(effect.args ?? [])} onChange={(event) => { const next = [...choice.effects]; next[effectIndex] = { ...effect, args: parseArgs(event.target.value) }; updateChoice(choiceIndex, { ...choice, effects: next }); }} aria-label={`选项 ${choiceIndex + 1} 效果 ${effectIndex + 1} 参数`} /></div>)}<button onClick={() => updateChoice(choiceIndex, { ...choice, effects: [...(choice.effects ?? []), { effect: effects[0]?.type_id ?? "flag.set", args: [] }] })}>+ 添加效果</button></div>)}
      <button onClick={() => updateField("choices", [...choices, { text: "新选项", effects: [] }])}>+ 添加选项</button>
    </div>
  </div>;
}

function RuntimePanel({ commandText, setCommandText, runCommand, trace, candidates, stateDiff, changedByPath, setChangedByPath, inspectChangedBy, changedByMatches }: { commandText: string; setCommandText: (value: string) => void; runCommand: () => void; trace: Record<string, unknown> | null; candidates: Record<string, unknown> | null; stateDiff: Record<string, unknown> | null; changedByPath: string; setChangedByPath: (value: string) => void; inspectChangedBy: () => void; changedByMatches: Record<string, unknown>[] }) {
  return <div className="runtime-view"><div className="runtime-toolbar"><div><p className="eyebrow">ISOLATED SESSION</p><h1>运行预览</h1></div><button className="primary" onClick={runCommand}><Play size={16} />执行命令</button></div><textarea className="command-editor" value={commandText} onChange={(event) => setCommandText(event.target.value)} aria-label="命令 JSON" /><div className="runtime-results"><div><h2>Trace</h2><pre>{JSON.stringify(trace ?? {}, null, 2)}</pre></div><div><h2>场景候选</h2><pre>{JSON.stringify(candidates ?? {}, null, 2)}</pre></div><div><h2>State Diff</h2><pre>{JSON.stringify(stateDiff ?? {}, null, 2)}</pre></div><div><h2>Changed By</h2><div className="changed-by-controls"><input value={changedByPath} onChange={(event) => setChangedByPath(event.target.value)} aria-label="状态字段路径" /><button onClick={inspectChangedBy}>查询</button></div><pre>{JSON.stringify(changedByMatches, null, 2)}</pre></div></div></div>;
}

const graphStyle: any[] = [
  { selector: "node", style: { label: "data(label)", "font-size": 10, "background-color": "#5b6b8c", color: "#f7f4ec", "text-valign": "center", "text-halign": "center", width: 34, height: 34, "border-width": 1, "border-color": "#c7d2e6" } },
  { selector: 'node[type="scene"]', style: { "background-color": "#b85c38", width: 46, height: 46 } },
  { selector: 'node[type="effect"]', style: { "background-color": "#357a72" } },
  { selector: 'node[type="rule"]', style: { "background-color": "#7a5c9e" } },
  { selector: "edge", style: { width: 1, "line-color": "#9aa5b5", "target-arrow-color": "#9aa5b5", "target-arrow-shape": "triangle", label: "data(relation)", "font-size": 8, color: "#697386", "curve-style": "bezier" } },
];

export default App;
