# 更新日志

本文件按每次更新独立记录，不把后续提交合并进已有条目。

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
