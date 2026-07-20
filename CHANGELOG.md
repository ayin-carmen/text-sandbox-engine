# 更新日志

本文件按每次更新独立记录，不把后续提交合并进已有条目。

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
