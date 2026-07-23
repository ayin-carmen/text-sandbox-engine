import { useEffect, useMemo, useState } from "react";
import { Braces, CheckCircle2, Copy, MapPin, Plus, Save, Search, Trash2, UserRound, Package, X } from "lucide-react";
import { api, Diagnostic, EntityRecord, EntityTemplate, EntityUsage, ReferenceItem } from "./api";
import { ReferenceSelect } from "./LowCodeWidgets";

type EntityWorkspaceProps = {
  entities: EntityRecord[];
  templates: EntityTemplate[];
  references: ReferenceItem[];
  onRefresh: () => Promise<void>;
  onMessage: (message: string) => void;
};

type EntityType = EntityRecord["type"];

const entityLabels: Record<EntityType, string> = { actor: "角色", location: "地点", item: "物品" };

export function EntityWorkspace({ entities, templates, references, onRefresh, onMessage }: EntityWorkspaceProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<EntityRecord | null>(null);
  const [rawJson, setRawJson] = useState("");
  const [mode, setMode] = useState<"form" | "json">("form");
  const [filter, setFilter] = useState<"all" | EntityType>("all");
  const [query, setQuery] = useState("");
  const [usages, setUsages] = useState<EntityUsage[]>([]);
  const [issues, setIssues] = useState<Diagnostic[]>([]);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [availableReferences, setAvailableReferences] = useState(references);

  const dirty = Boolean(selected && rawJson !== JSON.stringify(selected.document, null, 2));
  useEffect(() => setAvailableReferences(references), [references]);
  const filteredEntities = useMemo(() => entities.filter((entity) => {
    const typeMatch = filter === "all" || entity.type === filter;
    const text = `${entity.id} ${entity.label} ${entity.tags.join(" ")}`.toLowerCase();
    return typeMatch && (!query.trim() || text.includes(query.trim().toLowerCase()));
  }), [entities, filter, query]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      setRawJson("");
      setUsages([]);
      return;
    }
    let cancelled = false;
    void api.entity(selectedId).then(async (record) => {
      if (cancelled) return;
      setSelected(record);
      setRawJson(JSON.stringify(record.document ?? {}, null, 2));
      setUsages((await api.entityUsages(record.id)).usages);
      setIssues([]);
    }).catch((error) => onMessage(error instanceof Error ? error.message : "读取实体失败"));
    return () => { cancelled = true; };
  }, [selectedId, onMessage]);

  const selectEntity = (entity: EntityRecord) => {
    if (dirty && !window.confirm("当前实体有未保存修改，确定放弃并切换吗？")) return;
    setSelectedId(entity.id);
  };

  const updateDocument = (document: Record<string, unknown>) => {
    setRawJson(JSON.stringify(document, null, 2));
  };

  const save = async () => {
    if (!selected) return;
    try {
      const document = JSON.parse(rawJson) as Record<string, unknown>;
      const next = await api.saveEntity(selected.id, document, selected.revision);
      setSelected(next);
      setRawJson(JSON.stringify(next.document ?? {}, null, 2));
      setIssues([]);
      await onRefresh();
      setAvailableReferences((await api.references()).references);
      setUsages((await api.entityUsages(next.id)).usages);
      onMessage(`已保存${entityLabels[next.type]}：${next.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "实体保存失败";
      setIssues([{ severity: "error", code: "world.save_failed", message, file: null, json_path: "$" }]);
      onMessage(message);
    }
  };

  const discard = () => {
    if (!selected || !window.confirm("确定放弃当前实体的未保存修改吗？")) return;
    setRawJson(JSON.stringify(selected.document ?? {}, null, 2));
    setIssues([]);
    onMessage("已放弃实体草稿");
  };

  const remove = async () => {
    if (!selected || usages.length || !window.confirm(`确认删除 ${selected.id}？`)) return;
    try {
      await api.deleteEntity(selected.id, selected.revision);
      setSelectedId(null);
      await onRefresh();
      onMessage(`已删除实体：${selected.id}`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "实体删除失败");
    }
  };

  const created = async (record: EntityRecord) => {
    await onRefresh();
    setAvailableReferences((await api.references()).references);
    setSelectedId(record.id);
    setWizardOpen(false);
    onMessage(`已创建${entityLabels[record.type]}：${record.id}`);
  };

  return <div className="entity-layout">
    <aside className="entity-browser">
      <div className="entity-browser-header"><div><p className="eyebrow">WORLD ENTITIES</p><h1>世界实体</h1></div><button className="primary" title="新建实体" aria-label="新建实体" onClick={() => setWizardOpen(true)}><Plus size={16} /></button></div>
      <div className="entity-search"><Search size={14} /><input aria-label="搜索实体" placeholder="搜索名称、ID或标签" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
      <div className="entity-filters"><button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>全部 {entities.length}</button>{(["actor", "location", "item"] as EntityType[]).map((type) => <button className={filter === type ? "active" : ""} key={type} onClick={() => setFilter(type)}>{entityLabels[type]} {entities.filter((item) => item.type === type).length}</button>)}</div>
      <div className="entity-list">{filteredEntities.map((entity) => <button className={`entity-list-item ${selectedId === entity.id ? "selected" : ""}`} key={entity.id} onClick={() => selectEntity(entity)}><EntityIcon type={entity.type} /><span><strong>{entity.label}</strong><code>{entity.id}</code><small>{entity.tags.join(" · ") || "无标签"}</small></span>{entity.diagnostic_count > 0 && <em>{entity.diagnostic_count}</em>}</button>)}{!filteredEntities.length && <div className="entity-empty">没有匹配的实体。</div>}</div>
    </aside>
    <section className="entity-editor">{selected ? <>
      <div className="entity-editor-header"><div><p className="eyebrow">{entityLabels[selected.type]}</p><h1>{selected.id}</h1><span className="field-help">{selected.path} · revision {selected.revision.slice(0, 12)}</span></div><div className="entity-actions"><button onClick={discard} disabled={!dirty}>撤销草稿</button><button className="primary" onClick={save} disabled={!dirty || issues.some((issue) => issue.severity === "error")}><Save size={15} />保存</button></div></div>
      {dirty && <div className="draft-status">当前实体有未保存修改。未保存内容不会进入试玩会话。</div>}
      <div className="entity-tabs"><button className={mode === "form" ? "active" : ""} onClick={() => setMode("form")}>结构化表单</button><button className={mode === "json" ? "active" : ""} onClick={() => setMode("json")}><Braces size={14} />JSON 高级模式</button></div>
      {mode === "form" ? <EntityForm document={selected.document ?? {}} references={availableReferences} onChange={updateDocument} /> : <textarea className="entity-json-editor" aria-label="实体 JSON 源码" value={rawJson} onChange={(event) => { setRawJson(event.target.value); try { JSON.parse(event.target.value); setIssues([]); } catch { setIssues([{ severity: "error", code: "world.invalid_json", message: "JSON 语法无效", file: null, json_path: "$" }]); } }} />}
      {issues.length > 0 && <div className="entity-diagnostics">{issues.map((issue, index) => <div key={`${issue.code}-${index}`}><strong>{issue.code}</strong><span>{issue.message}</span><code>{issue.json_path}</code></div>)}</div>}
      <section className="entity-usages"><div className="subsection-title">引用影响 <span>{usages.length}</span></div>{usages.length ? usages.map((usage, index) => <div className="usage-row" key={`${usage.source}-${usage.json_path}-${index}`}><code>{usage.json_path}</code><span>{usage.description}</span><small>{usage.source}</small></div>) : <div className="field-help">当前没有发现其他实体或场景引用，可以删除。</div>}<button className="danger-button" disabled={usages.length > 0} onClick={remove}><Trash2 size={14} />{usages.length ? "存在引用，暂不可删除" : "删除实体"}</button></section>
    </> : <div className="entity-empty-large"><EntityIcon type="location" /><h1>选择一个实体</h1><p>从左侧选择角色、地点或物品，或创建一个新的实体。</p><button className="primary" onClick={() => setWizardOpen(true)}><Plus size={15} />新建实体</button></div>}</section>
    {wizardOpen && <EntityWizard templates={templates} references={availableReferences} onClose={() => setWizardOpen(false)} onCreated={created} onMessage={onMessage} />}
  </div>;
}

function EntityIcon({ type }: { type: EntityType }) {
  return type === "actor" ? <UserRound size={15} /> : type === "location" ? <MapPin size={15} /> : <Package size={15} />;
}

function EntityForm({ document, references, onChange }: { document: Record<string, unknown>; references: ReferenceItem[]; onChange: (document: Record<string, unknown>) => void }) {
  const type = document.type as EntityType;
  const components = (document.components as Record<string, any>) ?? {};
  const update = (path: string, value: unknown) => {
    const next = structuredClone(document);
    const parts = path.split(".");
    let cursor = next as Record<string, any>;
    parts.slice(0, -1).forEach((part) => { cursor[part] ??= {}; cursor = cursor[part]; });
    cursor[parts.at(-1)!] = value;
    onChange(next);
  };
  const tags = Array.isArray(document.tags) ? document.tags : [];
  const locations = references.filter((reference) => reference.type === "location");
  const items = references.filter((reference) => reference.type === "item");
  const flags = references.filter((reference) => reference.type === "flag");
  const inventory = Array.isArray(components.inventory?.items) ? components.inventory.items : [];
  const connections = Array.isArray(components.map_node?.connections) ? components.map_node.connections : [];
  return <div className="entity-form">
    <div className="form-grid"><label>稳定 ID<input value={String(document.id ?? "")} readOnly /></label><label>实体类型<input value={entityLabels[type]} readOnly /></label></div>
    <label className="wide-field">标签（用逗号分隔）<input value={tags.join(", ")} onChange={(event) => update("tags", event.target.value.split(",").map((tag: string) => tag.trim()).filter(Boolean))} /></label>
    {type === "actor" && <>
      <label className="wide-field">显示名称<input value={String(components.profile?.name ?? "")} onChange={(event) => update("components.profile.name", event.target.value)} /></label>
      <label className="wide-field">当前地点<ReferenceSelect value={String(components.location?.current ?? "")} options={locations} onChange={(value) => update("components.location.current", value)} /></label>
      <div className="entity-subsection"><div className="subsection-title">初始背包 <span>{inventory.length}</span></div>{inventory.map((item: string, index: number) => <div className="entity-array-row" key={`${item}-${index}`}><ReferenceSelect value={item} options={items} onChange={(value) => { const next = [...inventory]; next[index] = value; update("components.inventory.items", next); }} /><button title="移除物品" aria-label="移除物品" onClick={() => update("components.inventory.items", inventory.filter((_: unknown, itemIndex: number) => itemIndex !== index))}><X size={14} /></button></div>)}<button onClick={() => update("components.inventory.items", [...inventory, items[0]?.id ?? ""])}><Plus size={14} />添加物品</button></div>
    </>}
    {type === "location" && <>
      <label className="wide-field">地点名称<input value={String(components.description?.name ?? "")} onChange={(event) => update("components.description.name", event.target.value)} /></label>
      <label className="wide-field">描述<textarea rows={4} value={String(components.description?.text ?? "")} onChange={(event) => update("components.description.text", event.target.value)} /></label>
      <label className="wide-field">区域<input value={String(components.map_node?.region ?? "")} onChange={(event) => update("components.map_node.region", event.target.value)} /></label>
      <div className="entity-subsection"><div className="subsection-title">相邻地点 <span>{connections.length}</span></div>{connections.map((connection: string, index: number) => <div className="entity-array-row" key={`${connection}-${index}`}><ReferenceSelect value={connection} options={locations.filter((item) => item.id !== document.id)} onChange={(value) => { const next = [...connections]; next[index] = value; update("components.map_node.connections", next); }} /><button title="移除连接" aria-label="移除连接" onClick={() => update("components.map_node.connections", connections.filter((_: unknown, itemIndex: number) => itemIndex !== index))}><X size={14} /></button></div>)}<button onClick={() => update("components.map_node.connections", [...connections, locations.find((item) => item.id !== document.id)?.id ?? ""])}><Plus size={14} />添加连接</button></div>
      <div className="form-grid"><label>阻塞<input type="checkbox" checked={Boolean(components.access?.blocked)} onChange={(event) => update("components.access.blocked", event.target.checked)} /></label><label>所需 Flag<ReferenceSelect value={String(components.access?.required_flag ?? "")} options={flags} onChange={(value) => update("components.access.required_flag", value)} /></label></div>
    </>}
    {type === "item" && <>
      <label className="wide-field">物品名称<input value={String(components.description?.name ?? components.profile?.name ?? "")} onChange={(event) => update("components.description.name", event.target.value)} /></label>
      <label className="wide-field">描述<textarea rows={4} value={String(components.description?.text ?? "")} onChange={(event) => update("components.description.text", event.target.value)} /></label>
      <div className="form-grid"><label>物品类别<input value={String(components.item?.kind ?? "misc")} onChange={(event) => update("components.item.kind", event.target.value)} /></label><label>最大堆叠<input type="number" min="1" value={Number(components.item?.max_stack ?? 1)} onChange={(event) => update("components.item.max_stack", Number(event.target.value))} /></label></div>
      <label className="checkbox-field">允许堆叠<input type="checkbox" checked={Boolean(components.item?.stackable)} onChange={(event) => update("components.item.stackable", event.target.checked)} /></label>
    </>}
    <p className="field-help">未知组件字段请切换到 JSON 高级模式编辑。保存前会由 Python API 校验引用和实体结构。</p>
  </div>;
}

function EntityWizard({ templates, references, onClose, onCreated, onMessage }: { templates: EntityTemplate[]; references: ReferenceItem[]; onClose: () => void; onCreated: (record: EntityRecord) => Promise<void>; onMessage: (message: string) => void }) {
  const [type, setType] = useState<EntityType>("actor");
  const [name, setName] = useState("");
  const [namespace, setNamespace] = useState("greybrook");
  const [slug, setSlug] = useState("new_entity");
  const [tags, setTags] = useState("");
  const [location, setLocation] = useState("");
  const [preview, setPreview] = useState<{ id: string; document: Record<string, unknown>; issues: Diagnostic[]; passed: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const typeTemplates = templates.filter((template) => template.type === type);
  const locationOptions = references.filter((reference) => reference.type === "location");
  const payload = { type, namespace, slug, name, tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean), ...(type !== "item" && location ? { location } : {}), template: typeTemplates[0]?.id ?? "basic" };
  const previewEntity = async () => {
    try { setBusy(true); setPreview(await api.entityFromTemplate({ ...payload, preview: true })); } catch (error) { onMessage(error instanceof Error ? error.message : "实体预览失败"); } finally { setBusy(false); }
  };
  const create = async () => {
    try {
      setBusy(true);
      const result = await api.entityFromTemplate({ ...payload, preview: false });
      if (!result.entity) throw new Error("实体创建结果缺少记录");
      await onCreated(result.entity);
    } catch (error) { onMessage(error instanceof Error ? error.message : "实体创建失败"); } finally { setBusy(false); }
  };
  return <div className="modal-backdrop"><section className="wizard-dialog" role="dialog" aria-modal="true" aria-labelledby="entity-wizard-title"><div className="wizard-header"><div><p className="eyebrow">ENTITY WIZARD</p><h2 id="entity-wizard-title">新建世界实体</h2></div><button onClick={onClose} aria-label="关闭向导">×</button></div><div className="wizard-grid"><label>实体类型<select value={type} onChange={(event) => { setType(event.target.value as EntityType); setPreview(null); }}><option value="actor">角色</option><option value="location">地点</option><option value="item">物品</option></select></label><label>名称<input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：摆渡人" /></label><label>命名空间<input value={namespace} onChange={(event) => setNamespace(event.target.value)} /></label><label>英文短标识<input value={slug} onChange={(event) => setSlug(event.target.value)} /></label><label>标签<input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="npc, public" /></label>{type !== "item" && <label>{type === "actor" ? "初始地点" : "初始连接"}<ReferenceSelect value={location} options={locationOptions} onChange={setLocation} /> </label>}</div><div className="id-preview"><span>最终 ID</span><code>{type}.{namespace}.{slug}</code></div>{preview && <div className={`wizard-preview ${preview.passed ? "passed" : "failed"}`}><strong>{preview.passed ? "预览校验通过" : "预览发现问题"}</strong>{preview.issues.map((issue, index) => <span key={`${issue.code}-${index}`}>{issue.code}：{issue.message}</span>)}</div>}<div className="wizard-actions"><button onClick={onClose}>取消</button><button onClick={previewEntity} disabled={busy}>预览并校验</button><button className="primary" disabled={busy || !preview?.passed} onClick={create}><CheckCircle2 size={15} />确认创建</button></div></section></div>;
}
