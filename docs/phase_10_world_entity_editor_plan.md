# 阶段 10：世界实体编辑器方案

## 1. 阶段定位

阶段 9 已经完成场景的低代码创建、逻辑配置、校验和试玩。阶段 10 解决内容制作中的另一个断点：用户可以引用角色、地点和物品，但不能在编辑器中创建或维护这些对象。

本阶段将编辑器从“场景制作器”扩展为“世界内容制作器”，第一批支持以下实体类型：

1. 角色（`actor`）
2. 地点（`location`）
3. 物品（`item`）

实体仍然保存于现有 `world_state.json.entities`，不新建第二套运行时数据格式。React 只负责表单和交互，实体校验、引用分析、保存和索引由 Python API 与真实引擎数据模型负责。

## 2. 阶段目标

完成后，内容作者应当能够：

1. 在编辑器中浏览和筛选角色、地点、物品。
2. 通过向导创建新的角色、地点和物品。
3. 通过类型化表单编辑常用字段。
4. 通过 JSON 高级模式处理暂未覆盖的组件字段。
5. 看到新实体立即出现在场景引用选择器中。
6. 在删除或修改实体前看到引用它的场景、实体和字段。
7. 在保存前发现 ID、类型、地点连接和引用完整性问题。
8. 安全保存 `world_state.json`，保留备份并检测外部修改。
9. 使用新增地点和实体创建场景并启动试玩验证。

## 3. 设计原则

### 3.1 保持运行时格式

- 继续使用 `world_state.json.entities`。
- 不把角色、地点或物品拆成新的独立运行时文件。
- 不在前端重新实现移动、物品效果、角色规则等运行时语义。
- 表单元数据只服务编辑器，不成为运行时依赖。

### 3.2 稳定 ID 优先

- 新实体创建后，ID 默认不可直接修改。
- 第一版不提供静默重命名；需要重命名时使用“复制为新 ID + 引用迁移预览”。
- ID 必须符合现有实体规则，例如 `actor.mara`、`location.market_square`、`item.bread_basket`。
- 禁止跨类型复用相同稳定 ID。

### 3.3 保存可恢复

- 继续使用 revision 冲突检查、临时文件原子替换和 `.bak` 备份。
- 实体编辑和场景编辑共享未保存草稿保护。
- 校验失败时禁止保存。
- 保存后重新构建引用索引，让场景选择器立即更新。

## 4. 用户界面方案

### 4.1 内容树

在现有内容树中增加实体分组：

```text
内容树
├── scenes
├── actors
├── locations
├── items
└── 运行文件
    └── world_state.json
```

每个分组支持：

- 按显示名称和稳定 ID 搜索。
- 按标签筛选。
- 显示实体类型和来源。
- 显示未保存标记和诊断数量。
- 点击“新建”打开对应类型的创建向导。

### 4.2 实体编辑区

实体编辑区与场景编辑区保持一致的操作习惯：

1. 类型化表单。
2. JSON 高级模式。
3. 引用影响面板。
4. 即时校验和精确 JSON path。
5. 保存、撤销草稿和删除/复制操作。

页面顶部显示稳定 ID、类型和 revision；稳定 ID 作为只读字段展示。

### 4.3 创建向导

创建向导字段：

1. 实体类型。
2. 显示名称。
3. 英文稳定短标识。
4. 命名空间。
5. 标签。
6. 类型模板。
7. 初始位置或初始连接（按类型显示）。

向导先生成预览文档并校验，确认后才写入 `world_state.json`。ID 冲突时显示冲突来源，不自动覆盖已有实体。

## 5. 第一版类型表单

### 5.1 角色 Actor

基础字段：

- 显示名称：`components.profile.name`
- 标签：`tags`
- 当前地点：`components.location.current`
- 背包：`components.inventory.items`
- 关系值：`components.relationship`

创建模板默认生成：

```json
{
  "id": "actor.new_actor",
  "type": "actor",
  "tags": [],
  "components": {
    "profile": { "name": "新角色" },
    "location": { "current": "location.west_gate" },
    "inventory": { "items": [] }
  },
  "metadata": {}
}
```

### 5.2 地点 Location

基础字段：

- 显示名称：`components.description.name`
- 描述文本：`components.description.text`
- 区域：`components.map_node.region`
- 相邻地点：`components.map_node.connections`
- 访问限制：`components.access`
- 标签：`tags`

地点连接使用多选引用控件，只允许选择已有地点；创建新地点时可以先创建空连接，再回到表单补充连接。

### 5.3 物品 Item

基础字段：

- 显示名称：`components.description.name` 或 `components.profile.name`
- 描述文本：`components.description.text`
- 标签：`tags`
- 物品类别：`components.item.kind`
- 可堆叠数量：`components.item.stackable`、`components.item.max_stack`

物品模板不强行定义运行时未支持的效果。未知组件继续通过 JSON 高级模式编辑，避免编辑器替用户发明新的玩法语义。

## 6. 后端 API 方案

### 6.1 元数据和列表

```text
GET  /api/metadata/entity-types
GET  /api/world/entities?type=actor
GET  /api/world/entities/{entity_id}
GET  /api/world/entities/{entity_id}/usages
```

实体列表 DTO 至少包含：

```json
{
  "id": "actor.elda",
  "type": "actor",
  "label": "艾尔达",
  "tags": ["npc", "baker"],
  "path": "world_state.json#/entities/actor.elda",
  "revision": "...",
  "diagnostic_count": 0
}
```

### 6.2 创建、更新和删除

```text
POST   /api/world/entities
PUT    /api/world/entities/{entity_id}
DELETE /api/world/entities/{entity_id}?revision=...
```

要求：

1. POST 支持模板预览和正式创建两种模式。
2. PUT 使用 revision，拒绝覆盖外部修改。
3. DELETE 默认只允许删除没有引用的实体。
4. 有引用时返回引用清单和精确路径，不执行删除。
5. 第一版不做级联删除。
6. 删除前生成 `.bak`，并在成功后刷新所有引用索引。

### 6.3 校验和引用影响

```text
POST /api/validation/world-state
GET  /api/world/references?target=actor.elda
POST /api/world/references/rename-preview
```

校验范围：

- 根级实体 ID 与实体 `id` 一致。
- ID 格式和类型前缀一致。
- 实体类型在允许的类型表中。
- 当前地点存在且类型为 `location`。
- 地点连接都指向已存在的地点。
- 背包物品引用都指向 `item`。
- 场景地点、条件和效果引用仍然有效。
- 不允许重复 ID 或重复连接。
- 表单字段类型与组件结构一致。

## 7. 引用一致性策略

### 7.1 新建后的即时可用

实体保存成功后：

1. 更新 world state revision。
2. 重建实体引用索引。
3. 更新场景引用选择器。
4. 更新关系图中的实体节点和边。
5. 保留当前场景草稿，不强制切换页面。

### 7.2 删除保护

删除按钮先打开引用影响面板，列出：

- 哪些场景引用该实体。
- 哪些角色当前位于该地点。
- 哪些地点连接到该地点。
- 哪些角色背包包含该物品。
- 具体 JSON path 和来源文件。

只要存在硬引用，第一版就阻止删除。用户可以先修复引用，或使用复制/迁移流程生成新实体。

### 7.3 重命名预览

重命名不是简单修改 key。预览必须列出将被修改的所有路径：

```text
actor.elda
├── content/scenes/market_baker.json $.conditions[0].args[0]
└── world_state.json $.entities.actor.elda
```

只有用户确认迁移范围后，才允许以一次原子操作更新实体 key 和全部引用。该能力可以在阶段 10 后半段实现；若时间不足，先保留“复制为新 ID”。

## 8. 与阶段 9 编辑器的集成

1. 阶段 9 的引用选择器改为读取实体 API 的实时索引。
2. 新建实体后，场景表单无需刷新页面即可选择新对象。
3. 场景校验和 world state 校验共用稳定错误码和 JSON path 结构。
4. 试玩会话继续从保存后的 world state 创建内存副本。
5. 未保存实体草稿不能被试玩会话读取，避免试玩未保存内容造成误解。
6. JSON 高级模式继续保留，并与实体类型表单双向同步。

## 9. 分阶段实施

### 10.0 协议冻结与实体模板

- 冻结实体列表 DTO、创建/更新请求和错误码。
- 明确 actor、location、item 三种模板的最小字段。
- 增加实体类型元数据和稳定 ID 规则。

### 10.1 实体索引与安全服务层

- 增加实体列表、详情、引用使用分析。
- 复用 revision、备份和原子保存能力。
- 完成 world state 诊断和引用完整性检查。

### 10.2 CRUD API

- 实现创建预览、正式创建、更新和删除保护。
- 为冲突、重复 ID、类型错误和硬引用删除提供稳定错误码。
- 增加 API 测试和临时工作区测试。

### 10.3 实体浏览器与创建向导

- 增加 actors、locations、items 内容树。
- 增加搜索、筛选、类型模板和创建预览。
- 增加未保存草稿保护。

### 10.4 三类实体结构化表单

- 完成角色、地点、物品的常用字段表单。
- 增加标签编辑、地点连接编辑和物品背包引用选择。
- 保留 JSON 高级模式和未知组件降级。

### 10.5 引用联动、删除保护与试玩验证

- 实现引用影响面板和删除阻止。
- 新实体保存后实时更新场景选择器和关系图。
- 用真实中世纪小镇内容包创建新地点、角色和物品，并通过按钮试玩验证。

### 10.6 测试、文档和桌面交付

- 完成服务层、API、React 组件和端到端测试。
- 更新编辑器使用说明和完成报告。
- 运行 Python 测试、React 测试、TypeScript/Vite 构建、Python 编译检查。
- 通过 GitHub Actions 验证 Tauri Windows 构建。
- 更新中文 CHANGELOG，并单独提交每次变更。

## 10. 测试与验收场景

### 10.1 角色创建

1. 打开中世纪小镇内容包。
2. 创建角色 `actor.ferryman`。
3. 选择初始地点“西门”，添加 `npc` 标签。
4. 保存并重新读取，字段保持一致。
5. 在场景条件引用选择器中看到“渡船人”。

### 10.2 地点创建

1. 创建地点 `location.riverside`。
2. 设置名称、描述、区域和与“西门”的连接。
3. 创建或编辑角色，使其初始位置为新地点。
4. 启动试玩，确认移动操作和地点标签使用新地点。

### 10.3 物品创建

1. 创建物品 `item.river_token`。
2. 将其加入玩家初始背包或场景效果。
3. 在场景效果表单中选择该物品。
4. 试玩执行获得物品效果，确认状态中的稳定 ID 正确。

### 10.4 防护测试

- 重复 ID 创建被拒绝。
- 非法 ID 被精确定位。
- 缺失地点、物品和角色引用被阻止保存。
- 有场景或实体引用时删除被阻止。
- revision 冲突不会覆盖外部修改。
- 保存失败不会破坏原始 `world_state.json`。
- 试玩只读取已保存状态，不读取未保存草稿。

## 11. 明确不做

本阶段不实现：

1. 通用组件可视化设计器。
2. 任意运行时模块的自动生成。
3. 物品商店、装备系统或背包 UI 的完整玩法实现。
4. 多人协作、云端同步和权限系统。
5. 自动删除级联引用。
6. 不经用户确认的大规模 ID 重命名。
7. 将 world state 拆分为多个新的运行时文件。

## 12. 完成定义

阶段 10 完成必须满足：

1. 用户无需手写 JSON，即可创建并保存角色、地点和物品。
2. 新实体可以立即被场景条件和效果选择器引用。
3. 实体保存具备 revision 冲突保护、备份和原子替换。
4. 删除保护能展示引用来源并阻止破坏性删除。
5. 真实内容包完成三类实体的创建、保存、引用和试玩端到端验证。
6. JSON 高级模式、旧 world state 格式和阶段 9 场景编辑能力保持兼容。
7. 所有新增 API 和核心表单行为有测试覆盖。
8. 使用说明、完成报告和中文更新日志齐全。
9. 前端构建、Python 测试、编译检查和 Tauri Windows 构建全部通过。

