# 更新日志

本文件按每次更新独立记录，不把后续提交合并进已有条目。
## 2026-07-24 - 完成阶段 10.5 实体引用联动与校验

### 新增

- 新增实体草稿即时校验接口，支持精确定位地点、物品和实体结构问题。
- 保存实体后自动刷新引用选择器，保证新角色、地点和物品无需刷新页面即可使用。
- 关系图新增角色、地点、物品节点，以及当前地点、背包物品和地点连接关系。
- 删除保护改为只分析 Registry 声明的真实引用参数，减少误报。

### 验证

- Python 测试 43 项通过。
- React 组件测试 2 项通过。
- TypeScript/Vite 生产构建和 Python 编译检查通过。

## 2026-07-24 - 完成阶段 10.3 至 10.4 世界实体编辑器

### 新增

- 新增“世界实体”编辑视图，支持按类型、名称、ID和标签筛选角色、地点、物品。
- 新增三类实体创建向导，支持模板预览、命名空间、稳定 ID、标签和初始地点/连接。
- 新增角色、地点、物品的结构化表单和 JSON 高级模式。
- 新增实体草稿撤销、保存、引用影响面板和有引用时的删除保护提示。
- 新建物品或地点后，引用选择器会刷新并立即提供新实体。

### 验证

- Python 测试 43 项通过。
- React 组件测试 2 项通过。
- TypeScript/Vite 生产构建通过。

## 2026-07-24 - 完成阶段 10.0 至 10.2 实体服务与 API 基础

### 新增

- 新增角色、地点、物品三类实体模板、实体类型元数据、列表筛选和详情接口。
- 新增实体创建预览、创建、更新、删除保护、引用使用分析和 world state 校验 API。
- 新增 revision 冲突保护、`.bak` 备份和 world state 原子保存流程。
- 新增实体引用缺失、ID 格式、类型、地点连接和背包物品引用诊断。

### 验证

- Python 测试 43 项通过。
- 真实中世纪小镇副本完成角色、地点、物品创建、引用索引、更新和删除保护端到端验证。
- 保持 `actor.player`、`location.west_gate` 等既有单段 ID 兼容。

## 2026-07-23 - 制定阶段 10 世界实体编辑器方案

### 新增

- 新增阶段 10 世界实体编辑器方案，规划角色、地点和物品的创建、编辑、校验、引用联动、删除保护和试玩验证。
- 明确实体浏览器、创建向导、类型化表单、JSON 高级模式和安全保存流程。
- 明确阶段 10.0 至 10.6 的实施步骤、接口方向、测试场景、兼容性要求和完成定义。

## 2026-07-23 - 修复启动试玩按钮

### 修复

- 创建试玩会话时直接返回真实引擎生成的操作列表，避免按钮连续请求时出现会话已创建但界面没有进入试玩状态的问题。
- 启动按钮增加启动中状态，防止重复点击创建多个会话。
- 试玩接口失败时在控制台显示明确错误，并提示重启 Python API。

### 验证

- Python 测试 41 项通过。
- React 组件测试 2 项通过。
- TypeScript/Vite 生产构建和 Python 编译检查通过。

## 2026-07-22 - 完成阶段 9.6 稳定性与发布文档

### 新增

- 新增真实中世纪小镇内容包的低代码端到端测试，覆盖模板、结构化配置、保存、校验、按钮试玩和状态变化。
- 新增 Vitest 与 React Testing Library 测试基础设施，覆盖引用选择器的标签、缺失引用保留和稳定 ID 回写。
- 新增阶段 9 低代码编辑器使用说明和完成报告。
- 更新 README 与通用使用说明，切换到阶段 9 使用路径。

### 验证

- Python 测试 41 项通过。
- React 组件测试 2 项通过。
- 通过 Python 编译检查和 TypeScript/Vite 生产构建。
- Tauri Windows 桌面构建已由 GitHub Actions 通过，并上传 `text-sandbox-editor-windows` Artifact。

## 2026-07-22 - 完成阶段 9.5 可视化试玩控制台

### 新增

- 新增运行会话操作列表接口，返回当前角色、地点、时间、可前往地点和可见场景选项。
- 新增试玩会话重置接口，保证预览状态可回到源 world state。
- 执行结果增加中文业务摘要和状态变化说明。
- 编辑器将按钮操作作为默认试玩入口，原始命令、Trace、场景候选、State Diff 和 Changed By 收入高级详情。

### 验证

- Python 测试 40 项通过。
- 通过 Python 编译检查和 TypeScript/Vite 生产构建。

## 2026-07-22 - 完成阶段 9.4 即时诊断与字段定位

### 新增

- 增强单文档校验，定位地点、规则和效果参数的精确 JSON path。
- 增加丢失引用诊断、稳定错误码和中文修复建议。
- 编辑器对草稿执行防抖校验，错误文档禁止保存。
- 点击底部诊断信息可切换到结构化表单并高亮对应条件、显示条件或效果。

### 验证

- Python 测试 39 项通过。
- 通过 Python 编译检查和 TypeScript/Vite 生产构建。

## 2026-07-22 - 完成阶段 9.3 场景创建向导

### 新增

- 新增空白场景、普通叙事、NPC 对话、接取任务、交付物品和到达地点事件模板。
- 新增场景模板预览与创建 API，支持命名空间、英文短标识、地点、重复策略和优先级。
- 新建场景前执行地点和文档校验；场景 ID 冲突时自动生成不重复候选 ID。
- 编辑器新增场景向导，创建前可查看模板校验结果和最终场景 ID。

### 验证

- Python 测试 38 项通过。
- 通过 TypeScript/Vite 生产构建。

## 2026-07-22 - 完成阶段 9.2 场景编辑闭环

### 新增

- 为场景条件、选项显示条件、选项和效果增加复制、删除、上移和下移操作。
- 保留至少一个场景选项，避免结构化编辑器生成不可用文档。
- 增加未保存草稿状态提示、撤销草稿按钮，以及切换场景、刷新和关闭窗口前的保护。

### 验证

- Python 测试 37 项通过。
- 通过 Python 编译检查和 TypeScript/Vite 生产构建。

## 2026-07-22 - 开始阶段 9 低代码参数与引用选择

### 新增

- 扩展 Registry 编辑器元数据，增加中文名称、分类、模块版本、控件类型、引用类型和参数说明。
- 新增 `GET /api/metadata/references`，从真实 world state 和场景内容生成角色、地点、物品、任务、场景及 Flag 引用索引，并标记缺失引用。
- 将场景条件、选项显示条件和效果参数从 JSON 数组输入接入 Registry 驱动的结构化控件。
- 新增阶段 9 低代码协议说明文档。

### 兼容性

- 运行时继续使用原有 `type_id` 和参数数组，JSON 场景格式不变，JSON 高级模式继续可用。

### 验证

- Python 测试 37 项通过。
- 通过 Python 编译检查和 TypeScript/Vite 生产构建。

## 2026-07-22 - 修正首次回放的状态差异基线

### 修复

- 修正编辑器第一次执行命令时的 State Diff 计算，改用隔离运行会话创建时的真实初始状态作为比较基线。

### 验证

- 通过 TypeScript 类型检查与 Vite 生产构建。

## 2026-07-22 - 补充 Tauri 应用图标

### 新增

- 新增 `src-tauri/icons/icon.ico` 和 `scripts/create_tauri_icon.py`，补齐 Windows Tauri 资源编译所需的应用图标。

### 验证

- 重新触发 GitHub Actions Windows 桌面构建，继续验证 NSIS 安装包生成。

## 2026-07-22 - 修复 Windows Tauri 构建工作流

### 修复

- 修正 GitHub Actions 中 Tauri 的启动目录，使 CLI 从仓库根目录读取 `src-tauri/tauri.conf.json`，避免在 `editor/` 子目录中找不到 Tauri 项目。

### 验证

- GitHub Actions 已确认 Python、PyInstaller、Node 和 Rust 环境步骤通过；修复后重新执行 Windows NSIS 构建。

## 2026-07-22 - 完成阶段 8 编辑器可视化与桌面工具链

### 新增

- 新增 `src/text_sandbox_editor_api/` 本地 FastAPI 适配层，提供工作区、场景内容、元数据、校验、关系图、运行会话和诊断接口。
- 新增 Registry 编辑器元数据，描述命令、规则和效果的参数、读取路径、写入路径和模块版本。
- 新增稳定诊断字段：严重级别、错误码、消息、文件路径、JSON path 和场景 ID。
- 新增内容索引和关系图数据，支持从真实场景追踪地点、角色、规则、效果、任务、物品和状态引用。
- 新增内存运行会话，支持真实引擎命令执行、trace、场景候选分析和 state diff，预览不会修改源 world state。
- 新增原子 JSON 保存、同目录备份、修订标识和外部修改冲突检测。
- 新增 `editor/` React + TypeScript + Vite 编辑器，包含内容树、结构化场景表单、Monaco JSON 源码视图、Cytoscape 关系图、运行预览和问题面板。
- 新增 `src-tauri/` Tauri 2 最小桌面壳配置，负责窗口和本地 Python API 进程生命周期。
- 新增 `scripts/package_editor.ps1` 和 `.github/workflows/phase8-desktop.yml`，支持将 FastAPI 打包成单文件并构建 Windows NSIS 安装包。
- 新增 `docs/phase_8_editor_usage.md` 阶段 8 编辑器和桌面构建使用说明。

### 变更

- 扩展 `Registry`，在保持原有执行 API 不变的情况下增加编辑器元数据出口。
- 更新 README 和使用说明，将项目状态推进到阶段 8。
- 更新 `.gitignore`，忽略前端依赖、构建产物、Tauri target 和编辑器备份文件。

### 验证

- 通过 `python -m compileall -q src tests`。
- 通过 `python -m unittest discover -s tests`，共 34 个测试。
- 通过 FastAPI TestClient 打开 `examples/medieval_town`，读取 5 个真实场景、生成 45 条关系边、启动隔离会话并成功执行移动命令。
- 通过 `npm run build`，TypeScript 检查和 Vite 生产构建成功。
- 通过 PyInstaller 生成 `build/editor-runtime/text-sandbox-editor-api.exe`，启动后成功打开真实中世纪小镇内容包并返回 5 个场景。
- 当前环境的 Rust 安装源未完成，因此 Tauri 安装包由新增 GitHub Actions Windows 构建流程负责验证。

## 2026-07-21 - 新增使用说明

### 新增

- 新增 `docs/usage_guide.md` 使用说明，覆盖环境准备、快速验证、中世纪小镇示例、CLI 命令、Python API、命令格式、世界状态结构、场景内容结构、内置规则效果、扩展流程和调试建议。

### 变更

- 更新 README 文档列表，增加使用说明入口。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 30 个测试。

## 2026-07-21 - 阶段 7 正式玩法模块扩展

### 新增

- 新增 `inventory` 模块，提供 `inventory.has_item`、`inventory.add_item`、`inventory.remove_item`。
- 新增 `social` 模块，提供 `social.trust_at_least`、`social.adjust_trust`。
- 新增 `quest` 模块，提供 `quest.stage_is`、`quest.set_stage`、`quest.complete`。
- 新增 `narrative.mark_scene_seen` 与 `narrative.scene_not_seen`，使 `repeat_policy: once` 真正落地到状态。
- 新增 `docs/phase_7_formal_gameplay_modules_report.md` 阶段 7 模块扩展报告。
- 新增阶段 7 测试，覆盖物品、信任、任务、一次性场景和动态准入。

### 变更

- 扩展 `space.location_accessible`，支持 `required_flag` 动态准入。
- 增强事务写入，允许效果创建新状态路径并读取默认值。
- 将中世纪小镇切片升级为正式模块表达：面包篮、送货任务、信任变化和任务完成后的感谢场景。
- 更新阶段 6 模块缺口清单，标记已由阶段 7 覆盖的缺口。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 30 个测试。
- 通过 `examples/medieval_town/` 全部 JSON 文件解析。
- 通过中世纪内容包 `content-validate` 和 `replay` CLI 验证。

## 2026-07-21 - 阶段 6 中世纪沙盒内容验证

### 新增

- 新增 `examples/medieval_town/` 中世纪小镇垂直切片内容包。
- 新增四个地点：西门、集市广场、小教堂院、领主塔楼。
- 新增两个 NPC：守卫奥斯里克、面包师艾尔达。
- 新增四个场景：西门守卫、集市告示、面包师送货请求、小教堂送货。
- 新增垂直切片命令回放样例 `examples/medieval_town/commands/vertical_slice.json`。
- 新增阶段 6 验证报告、模块缺口清单和数据格式修订建议。
- 新增测试，覆盖中世纪内容校验、垂直切片回放、准入失败不改状态和阶段 6 文档存在性。

### 变更

- 更新 README，标记项目进入阶段 6。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 27 个测试。
- 通过 `examples/medieval_town/` 全部 JSON 文件解析。
- 通过中世纪内容包 `content-validate` 和 `replay` CLI 验证。

## 2026-07-21 - 阶段 5 调试工具与开发者体验

### 新增

- 新增 `diagnostics.state_diff`，支持比较两个状态快照并输出字段级差异。
- 新增 `diagnostics.changed_by`，支持从命令 trace 中定位某个状态字段由哪个命令修改。
- 新增 `debug.py`，提供内容校验、命令回放、场景候选分析和状态差异报告能力。
- 新增 `cli.py`，提供 `content-validate`、`replay`、`scene-report`、`state-diff`、`changed-by` 五个诊断命令。
- 新增 `examples/commands/playable_loop.json` 命令回放样例。
- 新增测试，覆盖命令回放、状态字段修改来源、场景过滤原因、状态差异和 CLI JSON 输出。
- 新增 UTF-8 BOM JSON 读取测试，覆盖 Windows 工具写出的 JSON 文件。

### 变更

- 在 `pyproject.toml` 中注册 `text-sandbox-engine` 命令行入口。
- 内容与存档读取改为兼容 UTF-8 BOM。
- 更新 README，补充阶段 5 状态和常用诊断命令。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 22 个测试。
- 通过 `content-validate`、`scene-report`、`replay`、`state-diff`、`changed-by` 五个 CLI 命令的本地源码运行验证。

## 2026-07-21 - 阶段 4 持久化与迁移体系

### 新增

- 新增版本化存档 envelope，将 `save_metadata` 与 `world_state` 分离保存。
- 新增 `SaveMetadata`、`SaveReport` 和 `LoadedSave` 存档报告模型。
- 新增 `MigrationRegistry` 与 `MigrationReport`，支持基础存档 schema 迁移。
- 新增模块版本记录和组件 schema version 收集。
- 新增旧版裸 world state 存档兼容读取和迁移报告。
- 新增缺失模块、模块版本不兼容的读档校验。
- 新增测试，覆盖存档元数据、旧格式迁移、缺失模块报错、模块版本不兼容和读档后继续执行命令。

### 变更

- `Runtime.save_game` 现在返回 `SaveReport`。
- `Runtime.load_game` 会记录最近一次迁移报告到 `last_load_report`。
- 更新 README，标记项目进入阶段 4。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 12 个测试。

## 2026-07-21 - 阶段 3 最小玩法模块

### 新增

- 新增 `time`、`space`、`narrative`、`actor` 四个最小玩法模块，并通过默认模块注册入口接入运行时。
- 新增 `narrative.choose` 命令，用于执行场景选项并产生可追踪效果。
- 新增 `actor.is_present` 规则，用于判断 NPC 是否与玩家处于同一地点。
- 新增市场 NPC `actor.mara` 和 `scene.market_vendor` 场景样例。
- 新增最小可玩循环测试，覆盖移动、时间推进、场景触发、选项效果、NPC 在场判断和存档读档一致性。

### 变更

- 将原先集中在 `builtins.py` 的移动和时间能力拆分到独立玩法模块。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 7 个测试。
- 通过最小世界状态、市场 intro 场景和市场 NPC 场景 JSON 解析。

## 2026-07-20 - 阶段 2 内容仓库与场景编排

### 新增

- 新增 `ContentRepository`，支持从内容目录加载 JSON 场景并执行基础校验。
- 新增 `ContentRepository` 包级公开导出。
- 新增场景候选筛选逻辑，支持地点 scope、场景条件规则、优先级排序和候选报告。
- 新增 `examples/content/scenes/market_intro.json` 场景样例。
- 新增 `time.period_in` 内置规则，用于场景条件判断。
- 新增测试，覆盖移动到市场后从内容仓库选中 `scene.market_intro`，以及未知规则的内容校验失败。

### 变更

- 将 `SceneOrchestrator` 从阶段 1 占位实现升级为真实场景选择边界。
- 更新 `Runtime.from_file`，支持可选传入 `content_path`。
- 更新 README，标记项目进入阶段 2。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 6 个测试。

## 2026-07-20 - 更新日志改为逐次记录

### 新增

- 明确更新日志维护规则：每次修改都新增独立条目，保留历史更新的边界。

### 变更

- 将已有更新日志从单一日期合并记录，拆分为按提交对应的多条记录。

## 2026-07-20 - 阶段 1 核心运行时原型

提交：`fb1855f Add phase 1 runtime prototype`

### 新增

- 新增阶段 1 核心运行时 Python 原型，包含 `Runtime`、`StateStore`、`Registry`、`CommandPipeline`、`RuleEngine`、`EffectEngine`、`Transaction`、`SceneOrchestrator` 和 JSON 存档读写。
- 新增内置 `space.travel_to` 命令，以及地点连接、地点准入、旗标判断、移动实体、推进时间、设置旗标等基础规则和效果。
- 新增单元测试，覆盖成功命令执行、规则失败不改状态、存档读档 roundtrip 和样例 JSON 解析。
- 新增 `.gitignore`，忽略本地工具目录、Python 缓存和构建产物。

### 变更

- 更新 README，补充阶段 1 原型状态、项目结构和测试运行方式。

### 验证

- 通过 `python -m compileall src tests`。
- 通过 `python -m unittest discover -s tests`，共 4 个测试。

## 2026-07-20 - 更新日志中文化

提交：`0d216a0 Translate changelog to Chinese`

### 变更

- 将更新日志标题、分类和说明文本从英文改为中文。

## 2026-07-20 - 阶段 0 技术验证包

提交：`2cdd7fc Add phase 0 validation artifacts`

### 新增

- 新增文字沙盒引擎阶段 0 技术验证包。
- 新增核心接口草案，用于在 Python 原型实现前冻结第一版运行时边界。
- 新增世界状态、实体内容和场景内容的 JSON Schema 草案。
- 新增初始世界状态和命令执行 trace 的最小样例数据。

### 变更

- 更新 README，补充当前阶段 0 状态和仓库结构说明。

### 验证

- 通过最小世界状态样例 JSON 解析。
- 通过命令执行 trace 样例 JSON 解析。
- 通过全部草案 schema JSON 解析。
