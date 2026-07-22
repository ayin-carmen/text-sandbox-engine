# 阶段 8：编辑器可视化与桌面工具链扩展方案

阶段 8 从“通过 JSON、CLI 和测试开发内容”推进到“通过桌面可视化编辑器制作、验证和调试内容”。

本阶段的主要产品是面向开发者和内容设计者的编辑器，不是玩家游戏客户端。编辑器建立在现有 Python 引擎、内容 schema 和诊断能力之上，不在前端复制规则、效果或场景判定逻辑。

## 1. 阶段目标

阶段 8 需要实现以下闭环：

1. 打开一个本地内容包和世界状态。
2. 以内容树和结构化表单查看、创建和修改场景。
3. 可视化场景、规则、效果、任务、地点和角色之间的引用关系。
4. 调用真实引擎完成内容校验、场景候选分析和命令回放。
5. 查看规则判断、效果执行、状态差异和字段修改来源。
6. 在校验通过后安全写回 JSON 文件。
7. 将编辑器打包为可离线运行的桌面程序。

完成阶段 8 后，制作一个新场景的日常流程不应再要求手工运行多个 CLI 命令或直接维护大段 JSON。

## 2. 本阶段范围

### 2.1 必须实现

1. 工作区与内容包管理。
2. 场景内容树。
3. 场景结构化编辑器。
4. JSON 源码查看与高级编辑模式。
5. schema 和引擎语义校验。
6. 场景关系图。
7. 场景候选分析器。
8. 命令运行与 trace 查看器。
9. world state 查看器和 state diff。
10. 本地保存、外部修改检测和恢复机制。
11. Tauri 桌面打包的最小可运行版本。

### 2.2 可以延后

1. 实体、任务和物品的完整结构化编辑器。
2. 多文件批量重构和引用自动改名。
3. 可拖拽的复杂流程编排。
4. 编辑器插件系统。
5. 多人协作编辑和版本审批。
6. 玩家游戏客户端。
7. Android 和 iOS 客户端。

### 2.3 明确不做

1. 不在 React 中重新实现规则引擎。
2. 不允许编辑器绕过 Transaction 直接执行游戏效果。
3. 不把 FastAPI 暴露为默认公网服务。
4. 不在本阶段建设账号、云存档或在线多人系统。
5. 不为了关系图而修改现有内容语义。

## 3. 技术选型

### 3.1 桌面壳与界面

- `Tauri`：桌面程序外壳、窗口、文件选择和最终安装包。
- `React + TypeScript`：编辑器界面与状态管理。
- `Vite`：前端开发和构建。
- `Monaco Editor`：JSON 源码模式、语法提示和错误定位。
- `Cytoscape.js`：场景、规则、效果、实体和任务的引用关系图。
- `ECharts`：仅用于确有价值的执行时间线或统计图，不承担关系图编辑。

### 3.2 本地服务与引擎

- `FastAPI`：编辑器与 Python 引擎之间的本地 API 层。
- 现有 `text_sandbox_engine`：运行时、内容仓库、场景编排、命令管线和诊断逻辑。
- JSON Schema：即时结构校验和表单字段约束。
- 本地文件系统：内容包、世界状态、命令样例和编辑器工作区配置。

Tauri 启动时负责启动绑定在 `127.0.0.1` 的本地 Python 服务，并在退出编辑器时结束该进程。开发阶段可以分别启动前端和 FastAPI，发布阶段再统一打包。

## 4. 总体架构

```text
Tauri 桌面程序
├── React 编辑器
│   ├── 工作区与内容树
│   ├── 结构化场景编辑器
│   ├── Monaco JSON 编辑器
│   ├── Cytoscape 关系图
│   └── Trace / Diff / 诊断面板
├── 本地 FastAPI
│   ├── workspace API
│   ├── content API
│   ├── validation API
│   ├── runtime API
│   └── diagnostics API
└── Python 引擎
    ├── ContentRepository
    ├── SceneOrchestrator
    ├── CommandPipeline
    ├── StateStore
    └── diagnostics
```

编辑器前端只消费稳定的 JSON 数据传输对象。Python 的 dataclass、内部对象和异常不直接泄漏到前端。

## 5. 编辑器信息架构

编辑器采用“左侧导航、中间主编辑区、右侧检查器、底部诊断”的桌面布局。

```text
┌──────────────┬──────────────────────────────┬──────────────────┐
│ 工作区/内容树 │ 主编辑区                     │ 属性/引用检查器   │
│              │ 表单 / JSON / 关系图 / 预览  │                  │
├──────────────┴──────────────────────────────┴──────────────────┤
│ 问题 / Trace / State Diff / 场景候选分析                       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 内容树

第一版至少展示：

- 内容包。
- `scenes` 目录及场景文件。
- 世界状态文件。
- 命令回放文件。
- schema 文件。

内容树支持打开、创建、复制、重命名和删除场景。删除和重命名前必须检查引用并二次确认。

### 5.2 场景结构化编辑器

第一版围绕当前 scene schema 提供：

- 场景 ID、标题、正文和优先级。
- scope 和触发上下文。
- repeat policy。
- rules 列表及参数。
- choices 列表。
- choice rules。
- choice effects。
- presentation 字段。

规则和效果类型来自后端 Registry 元数据，不在前端维护硬编码枚举。选择类型后，编辑器根据元数据生成参数表单，并保留切换到 JSON 源码模式的能力。

### 5.3 关系图

关系图第一版只读，不提供任意拖拽连线写回内容。节点类型包括：

- 场景。
- 规则。
- 效果。
- 地点。
- 角色。
- 任务。
- 物品。
- flag 或稳定状态路径。

边表示“引用”“读取”“修改”“前往”“要求”或“推进”。点击节点后，在检查器中展示来源文件、引用位置和相关诊断；双击内容节点打开对应编辑器。

### 5.4 运行预览与诊断

编辑器必须复用现有能力：

- `content-validate`：内容包校验。
- `scene-report`：显示场景通过或被过滤的原因。
- `replay`：执行命令序列并产生 trace。
- `state-diff`：比较命令前后或两个存档的状态。
- `changed-by`：定位字段修改来源。

诊断项统一包含严重级别、稳定错误码、消息、文件路径、JSON path，以及可选的场景 ID、命令 ID 和修复建议。点击诊断应定位到表单字段或 Monaco 中的对应位置。

## 6. 本地 API 边界

第一版建议提供以下 API；路径可以在实现时调整，但职责不可混合。

### 6.1 工作区

```text
POST /api/workspaces/open
GET  /api/workspaces/current
GET  /api/workspaces/tree
POST /api/workspaces/refresh
```

### 6.2 内容读写

```text
GET    /api/content/scenes
GET    /api/content/scenes/{scene_id}
POST   /api/content/scenes
PUT    /api/content/scenes/{scene_id}
DELETE /api/content/scenes/{scene_id}
```

写接口必须携带客户端读取时获得的修订标识。若文件在编辑期间被外部修改，服务返回冲突，不得静默覆盖。

### 6.3 元数据与校验

```text
GET  /api/metadata/registry
GET  /api/metadata/schemas
POST /api/validation/content
POST /api/validation/document
GET  /api/graph/content
```

### 6.4 运行和诊断

```text
POST /api/runtime/sessions
POST /api/runtime/sessions/{session_id}/commands
GET  /api/runtime/sessions/{session_id}/state
POST /api/diagnostics/scene-candidates
POST /api/diagnostics/state-diff
POST /api/diagnostics/changed-by
```

运行会话使用内存中的状态副本。除非用户明确执行“保存为存档”，编辑器中的预览和回放不得修改源 world state 文件。

## 7. 引擎侧扩展要求

阶段 8 应优先增加适配层，而不是改变核心执行语义。

### 7.1 Registry 元数据

当前 Registry 除了保存可调用函数，还需要能够向编辑器提供：

- 类型 ID。
- 分类和简短说明。
- 参数名称、数据类型、必填性和默认值。
- 参数可引用的实体类别。
- 规则读取的典型状态路径。
- 效果可能修改的典型状态路径。
- 所属模块和模块版本。

### 7.2 稳定诊断协议

CLI 文本不是编辑器 API。需要在现有 diagnostics 之上形成稳定的结构化诊断 DTO，并为常见问题分配错误码，例如：

- `content.invalid_json`
- `content.schema_violation`
- `content.duplicate_id`
- `registry.unknown_rule`
- `registry.unknown_effect`
- `reference.missing_target`
- `scene.filtered_by_scope`
- `scene.filtered_by_rule`

### 7.3 内容索引

增加只读内容索引，统一收集场景 ID、实体引用、规则引用、效果引用和稳定状态路径。关系图、引用查找、重命名检查和自动补全均读取该索引。

### 7.4 安全文件写入

保存流程应满足：

1. 写入前执行 JSON 和 schema 校验。
2. 写入同目录临时文件。
3. 成功后原子替换目标文件。
4. 保留可恢复的最近版本或编辑器备份。
5. 不格式化或改写未被用户编辑的其他文件。

## 8. 实施分段

### 8.0：技术验证

- 建立 React、TypeScript、Vite 和 FastAPI 最小工程。
- 前端读取中世纪小镇内容包并显示场景列表。
- 通过 API 执行一次 `content-validate` 和 `scene-report`。
- 验证 Tauri 能启动和关闭本地 Python 服务。

退出条件：桌面窗口可以打开真实内容包并显示真实诊断结果。

### 8.1：只读编辑器骨架

- 工作区打开和最近项目。
- 内容树。
- 场景详情只读视图。
- JSON 源码只读视图。
- 问题面板。
- world state 查看器。

退出条件：不使用命令行即可浏览内容包并定位所有校验问题。

### 8.2：场景编辑与安全保存

- 场景结构化表单。
- Monaco JSON 高级模式。
- 新建、复制、重命名和删除。
- 即时校验。
- 未保存状态提示、外部修改冲突和恢复。

退出条件：可完整创建一个合法场景，保存后现有测试和内容校验继续通过。

### 8.3：关系图与引用导航

- 内容索引。
- Cytoscape 关系图。
- 按节点类型和引用类型筛选。
- 从节点跳转到源文件和字段。
- 缺失引用和孤立内容高亮。

退出条件：可以从任一场景追踪其规则、效果、任务、物品和状态路径依赖。

### 8.4：运行预览与深度诊断

- 内存运行会话。
- 命令输入和命令序列回放。
- Trace 时间线。
- 规则结果和失败原因。
- State Diff。
- Changed By 查询。
- 场景候选分析。

退出条件：可以在编辑器内复现一次完整中世纪小镇垂直切片，并解释每次状态变化的来源。

### 8.5：桌面交付

- Tauri 集成。
- Python 运行环境和服务打包。
- 日志目录、崩溃诊断和版本信息。
- Windows 安装包。
- 打包后离线验证。

退出条件：在未配置开发环境的目标机器上能够安装、打开内容包、编辑、校验和回放。

## 9. 测试策略

### 9.1 Python

- API DTO 单元测试。
- Registry 元数据测试。
- 内容索引和引用提取测试。
- 文件冲突与原子保存测试。
- 运行会话隔离测试。
- 现有引擎回归测试。

### 9.2 前端

- 表单与 JSON 双向转换测试。
- 未保存状态和冲突处理测试。
- 诊断定位测试。
- 关系图数据转换测试。
- API 错误状态测试。

### 9.3 端到端

至少覆盖：

1. 打开 `examples/medieval_town`。
2. 创建一个新场景。
3. 添加规则、选项和效果。
4. 修复一个故意制造的无效引用。
5. 保存并重新加载。
6. 运行垂直切片。
7. 查看 trace 和 state diff。
8. 确认预览没有修改原始 world state。

## 10. 验收标准

阶段 8 完成需要同时满足：

1. 编辑器能处理仓库中的真实示例，而不是专用演示数据。
2. 核心规则只由 Python 引擎执行。
3. 所有保存内容都能通过现有 schema 和内容校验。
4. 所有诊断都能定位到文件和 JSON path。
5. 关系图中的边可以追溯到真实内容引用。
6. 运行预览是隔离的，不会意外修改源文件。
7. 外部文件冲突不会导致静默覆盖。
8. 现有自动化测试保持通过。
9. 桌面安装包可以离线运行。
10. 一个新场景可以只通过编辑器完成创建、验证和回放。

## 11. 建议目录结构

```text
text-sandbox-engine/
├── src/text_sandbox_engine/       # 现有核心引擎
├── src/text_sandbox_editor_api/   # FastAPI 与编辑器适配层
├── editor/                        # React + TypeScript 前端
│   ├── src/api/
│   ├── src/features/content/
│   ├── src/features/graph/
│   ├── src/features/runtime/
│   └── src/features/diagnostics/
├── src-tauri/                     # Tauri 桌面配置与启动逻辑
├── schemas/
├── examples/
└── tests/
```

是否将编辑器 API 保留在同一 Python 包中，可以在 8.0 技术验证后决定；无论物理目录如何组织，API 适配层都不得反向污染核心引擎。

## 12. 面向未来玩家端和手机端的预留

阶段 8 不实现玩家端，但 API 设计应避免只适用于编辑器：

1. 编辑器专用 API 与运行时 API 分组。
2. 运行时命令和结果使用稳定 JSON 协议。
3. 不把本地绝对路径放入玩家运行时 DTO。
4. 不让玩家视图获得未触发场景、隐藏规则或 NPC 内部状态。
5. 桌面玩家端未来可以继续访问本地 FastAPI。
6. 手机玩家端未来可以使用 Capacitor 封装响应式 React 界面，并访问部署在服务器上的同一套 FastAPI 运行时接口。

因此，阶段 8 的价值不只是增加可视化界面，还要建立“核心引擎—稳定 API—多种客户端”的正式边界。当前只交付编辑器和本地桌面工具链，未来扩展玩家桌面端或手机端时无需重写引擎。

