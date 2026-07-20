# Text Sandbox Engine

面向高状态密度、高事件密度、高分支复杂度的文字沙盒游戏引擎设计。

当前仓库内容以架构规划为主，目标是先建立一个可演化、可扩展、可调试、可存档的 Python 引擎底座，再逐步接入具体玩法模块与内容包。

## Documents

- `docs/professional_text_sandbox_engine_architecture.txt`  
  专业化文字沙盒引擎架构方案，包含核心原则、运行时架构、数据模型、模块系统、内容系统、存档迁移、诊断测试与未来计划。

- `docs/evolvable_text_sandbox_engine_plan.txt`  
  可演化文字沙盒引擎方案，用更直观的方式描述薄核心、命令、规则、效果和扩展模块的关系。

- `docs/phase_0_core_interfaces.md`  
  阶段 0 核心接口草案，冻结第一版 Python 原型需要遵守的运行时、状态、命令、规则、效果、事务、内容、场景、存档和诊断边界。

- `docs/phase_0_content_schema_draft.md`  
  阶段 0 内容 schema 草案，说明实体、世界状态、场景、规则引用和效果引用的最小数据形状。

## Draft Schemas

- `schemas/state/world_state.schema.json`
- `schemas/content/entity.schema.json`
- `schemas/content/scene.schema.json`

## Examples

- `examples/minimal_world_state.json`
- `examples/traces/travel_to_market_trace.json`

## Python Prototype

Python 原型位于 `src/text_sandbox_engine/`。

当前已实现：

1. `Runtime` 运行时入口。
2. `StateStore` 世界状态仓库。
3. `Registry` 命令、规则、效果注册表。
4. `CommandPipeline` 命令执行管线。
5. `RuleEngine` 与 `EffectEngine`。
6. `Transaction` 与 `ChangeSet`。
7. `SceneOrchestrator` 场景选择边界。
8. JSON 存档读写。
9. 基础内置命令、规则和效果。
10. `ContentRepository` 内容仓库。
11. 基础场景加载、校验、筛选和候选报告。
12. `time`、`space`、`narrative`、`actor` 最小玩法模块。
13. `narrative.choose` 场景选项执行命令。
14. NPC 在场判断与最小可玩循环。

运行测试：

```bash
python -m unittest discover -s tests
```

## Current Status

项目处于阶段 3：最小玩法模块。

已完成：

1. 核心架构边界说明。
2. 核心接口草案。
3. 内容 schema 草案。
4. 最小世界状态样例。
5. 命令执行 trace 样例。
6. 最小 Python 运行时原型。
7. 命令执行、规则判断、效果应用、事务提交和存档读写测试。
8. JSON 场景内容加载、基础校验和场景候选报告。
9. 最小玩法模块：时间、空间、叙事、角色。
10. 最小可玩循环：移动到市场、触发场景、执行选项、显示 NPC 场景。

下一步是进入阶段 4：持久化与迁移体系。
