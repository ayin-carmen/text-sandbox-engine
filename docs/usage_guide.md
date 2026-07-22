# 使用说明

这份说明面向想把当前原型跑起来、调试内容包、或继续扩展玩法模块的人。当前项目已进入阶段 9，在命令驱动运行时、内容场景加载、诊断 CLI、存档迁移和正式玩法模块之外，还提供低代码场景向导、结构化参数编辑、引用选择器、即时诊断、按钮试玩和 Tauri 桌面壳工程。

## 环境要求

- Python 3.11 或更高版本。
- Windows PowerShell、Git Bash、Linux shell 均可运行。
- 引擎和测试本身不需要额外第三方依赖；编辑器开发需要 Node.js、npm，以及 Python 的 `fastapi` 和 `uvicorn`。

如果没有安装为包，建议在仓库根目录运行命令，并让 Python 能找到 `src`：

PowerShell：

```powershell
$env:PYTHONPATH = "src"
```

bash：

```bash
export PYTHONPATH=src
```

也可以安装为可编辑包：

```bash
python -m pip install -e .
```

安装后可以直接使用 `text-sandbox-engine` 命令；未安装时使用 `python -m text_sandbox_engine.cli`。

## 快速验证

在仓库根目录运行：

```bash
python -m unittest discover -s tests
python -m compileall src tests
```

当前应通过 41 个 Python 测试；前端组件测试使用 `npm test` 执行。

## 启动阶段 9 低代码编辑器

编辑器由两个本地进程组成：Python API 负责调用真实引擎，React 前端负责可视化和编辑。API 只监听 `127.0.0.1`，不会默认暴露公网。

PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m pip install -e ".[editor]"
python -m text_sandbox_editor_api
```

另开一个终端启动前端：

```powershell
cd editor
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，在顶部输入 `examples/medieval_town` 并打开。编辑器支持场景向导、模板预览、Registry 参数控件、引用选择器、内容树、结构化场景表单、JSON 源码、关系图、按钮试玩、world state 和诊断面板。保存前会重新校验 JSON 和引擎注册表，保存时生成同目录 `.bak` 备份，并用临时文件原子替换目标文件。

运行预览创建内存中的 `Runtime` 副本。点击“启动试玩”后，地点和场景选项按钮由真实引擎操作列表生成；预览、trace、场景候选分析和 state diff 不会写入源 `world_state.json`。完整低代码操作见 `docs/phase_9_low_code_editor_usage.md`。

## 构建桌面版本

仓库中的 `src-tauri/` 是 Tauri 2 最小桌面壳。目标机器需要 Rust、Node.js 和 Python 运行环境；安装 Rust 后在仓库根目录执行：

```powershell
cd editor
npm install
cd ..
npx tauri build --config src-tauri/tauri.conf.json
```

生产壳启动时会在本机启动 `text_sandbox_editor_api`，退出时结束该进程。构建产物位于 Tauri 的 `src-tauri/target/release/bundle/` 目录。

## 运行中世纪小镇示例

中世纪小镇示例位于 `examples/medieval_town/`，包含世界状态、场景内容和一段垂直切片命令回放。

PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m text_sandbox_engine.cli content-validate --content examples/medieval_town/content
python -m text_sandbox_engine.cli replay --state examples/medieval_town/world_state.json --content examples/medieval_town/content --commands examples/medieval_town/commands/vertical_slice.json
```

bash：

```bash
PYTHONPATH=src python -m text_sandbox_engine.cli content-validate --content examples/medieval_town/content
PYTHONPATH=src python -m text_sandbox_engine.cli replay --state examples/medieval_town/world_state.json --content examples/medieval_town/content --commands examples/medieval_town/commands/vertical_slice.json
```

回放成功时，报告中的关键结果应包括：

- `status` 为 `succeeded`。
- `command_count` 为 `8`。
- 玩家最终在 `location.market_square`。
- `quest.bread_delivery` 阶段为 `completed`。
- 玩家获得 `item.warm_bread`。
- `actor.elda` 的信任值变为 `3`。

## CLI 命令

所有 CLI 命令都输出 JSON，适合人工查看，也适合接入自动化脚本。

### 校验内容包

```bash
PYTHONPATH=src python -m text_sandbox_engine.cli content-validate --content examples/medieval_town/content
```

用途：

- 读取 `content/scenes/*.json`。
- 检查场景必填字段。
- 检查重复场景 ID。
- 检查规则和效果名称是否已注册。

成功示例：

```json
{
  "passed": true,
  "issues": [],
  "scene_count": 5
}
```

### 回放命令序列

```bash
PYTHONPATH=src python -m text_sandbox_engine.cli replay --state examples/medieval_town/world_state.json --content examples/medieval_town/content --commands examples/medieval_town/commands/vertical_slice.json
```

用途：

- 从指定世界状态启动运行时。
- 顺序执行 commands JSON 中的命令。
- 输出每条命令的规则判断、效果应用、状态变更和场景候选报告。
- 输出回放前后的状态差异。

### 查看当前可触发场景

```bash
PYTHONPATH=src python -m text_sandbox_engine.cli scene-report --state examples/medieval_town/world_state.json --content examples/medieval_town/content
```

可选指定角色：

```bash
PYTHONPATH=src python -m text_sandbox_engine.cli scene-report --state examples/medieval_town/world_state.json --content examples/medieval_town/content --actor actor.player
```

用途：

- 查看当前状态下哪个场景会被选中。
- 查看被过滤场景的原因，例如地点不匹配、条件不满足、一次性场景已经看过。

### 比较两个状态文件

```bash
PYTHONPATH=src python -m text_sandbox_engine.cli state-diff --before before.json --after after.json
```

用途：

- 对比两个世界状态快照。
- 输出字段级新增、删除和变化。

### 追踪字段由哪条命令修改

```bash
PYTHONPATH=src python -m text_sandbox_engine.cli changed-by --trace trace.json --path flags.met_market
```

用途：

- 输入单条命令 trace。
- 查询某个状态路径是否由这条命令修改。

## Python API 基本用法

直接在 Python 中加载状态、内容并执行命令：

```python
from text_sandbox_engine.runtime import Runtime

runtime = Runtime.from_file(
    "examples/medieval_town/world_state.json",
    content_path="examples/medieval_town/content",
)

result = runtime.execute(
    {
        "type": "space.travel_to",
        "actor": "actor.player",
        "target": "location.market_square",
        "args": {},
    }
)

print(result.status)
print(result.trace.failure_reason)
print(runtime.snapshot()["entities"]["actor.player"]["components"]["location"]["current"])
```

保存当前游戏：

```python
report = runtime.save_game("save.json")
print(report.metadata)
```

读取版本化存档：

```python
runtime = Runtime.load_game("save.json")
print(runtime.last_load_report)
```

## 命令格式

命令是运行时的唯一行为入口。最小结构如下：

```json
{
  "type": "space.travel_to",
  "actor": "actor.player",
  "target": "location.market_square",
  "args": {}
}
```

字段说明：

- `type`：命令类型，例如 `space.travel_to` 或 `narrative.choose`。
- `actor`：执行命令的实体 ID，通常是 `actor.player`。
- `target`：命令目标，例如地点 ID 或场景 ID。
- `args`：命令参数。
- `source`：可选，默认是 `player`。
- `metadata`：可选，保留给调试和扩展使用。
- `id`：可选，外部系统可传入稳定命令 ID。

当前主要命令：

| 命令 | 用途 | 常用参数 |
| --- | --- | --- |
| `space.travel_to` | 移动角色到目标地点 | `actor`、`target` |
| `narrative.choose` | 执行场景中的选项 | `target` 为场景 ID，`args.choice_index` 为选项序号 |

## 世界状态结构

世界状态是一个 JSON 对象，核心字段如下：

```json
{
  "schema_version": 1,
  "runtime_version": "0.0.0-phase6",
  "seed": 240721,
  "entities": {},
  "globals": {},
  "flags": {},
  "history": [],
  "cooldowns": {},
  "indexes": {},
  "diagnostics_state": {}
}
```

常用约定：

- `entities` 保存角色、地点和其他实体。
- `globals.clock` 保存时间信息，如 `day`、`period`、`tick`。
- `globals.narrative.seen_scenes` 保存已经看过的一次性场景。
- `globals.quests` 保存任务阶段和完成状态。
- `flags` 保存布尔开关，例如 `met_guard`、`has_keep_pass`。
- `diagnostics_state.command_index` 用于命令回放编号。

角色示例：

```json
{
  "id": "actor.player",
  "type": "actor",
  "tags": ["player"],
  "components": {
    "location": {
      "current": "location.west_gate"
    },
    "inventory": {
      "items": []
    }
  }
}
```

地点示例：

```json
{
  "id": "location.lord_keep",
  "type": "location",
  "tags": ["keep", "restricted"],
  "components": {
    "map_node": {
      "connections": ["location.market_square"]
    },
    "access": {
      "blocked": false,
      "required_flag": "has_keep_pass"
    }
  }
}
```

## 场景内容结构

内容包通常采用以下目录结构：

```text
content/
  scenes/
    scene_id.json
```

场景最小结构：

```json
{
  "id": "scene.greybrook.market_baker",
  "scope": {
    "location": "location.market_square"
  },
  "priority": 15,
  "conditions": [
    {
      "rule": "actor.is_present",
      "args": ["actor.elda"]
    }
  ],
  "content_tags": ["npc", "market"],
  "text": "面包师请你把一篮面包送到小教堂院。",
  "choices": [
    {
      "text": "答应帮忙",
      "effects": [
        {
          "effect": "inventory.add_item",
          "args": ["actor.player", "item.bread_basket"]
        },
        {
          "effect": "quest.set_stage",
          "args": ["quest.bread_delivery", "accepted"]
        }
      ]
    }
  ],
  "cooldown": {},
  "repeat_policy": "once"
}
```

字段说明：

- `id`：场景唯一 ID。
- `scope.location`：场景发生地点。当前场景编排会按玩家当前位置筛选。
- `priority`：优先级，数值越高越先被选中。
- `conditions`：场景级规则，全部通过才可触发。
- `choices`：玩家可执行的选项。
- `choices[].visible_if`：选项级规则，执行该选项前检查。
- `choices[].effects`：选项执行后应用的效果。
- `repeat_policy: once`：场景只允许执行一次，执行后写入 `globals.narrative.seen_scenes`。

## 当前内置规则

| 规则 | 参数 | 用途 |
| --- | --- | --- |
| `flag.is_false` | `flag_name` | 检查某个 flag 是否为 false 或不存在 |
| `time.period_in` | `period...` | 检查当前时间段是否在允许列表中 |
| `space.location_connected` | `actor_id`, `target_location_id` | 检查目标地点是否与当前地点相连 |
| `space.location_accessible` | `target_location_id` | 检查地点是否未阻塞且满足 `required_flag` |
| `actor.is_present` | `npc_id` | 检查 NPC 是否和命令 actor 位于同一地点 |
| `inventory.has_item` | `actor_id`, `item_id` | 检查角色是否持有物品 |
| `social.trust_at_least` | `actor_id`, `minimum` | 检查角色信任值是否达到阈值 |
| `quest.stage_is` | `quest_id`, `stage` | 检查任务阶段 |
| `narrative.scene_not_seen` | `scene_id` | 检查一次性场景是否尚未执行 |

## 当前内置效果

| 效果 | 参数 | 用途 |
| --- | --- | --- |
| `flag.set` | `flag_name`, `value` | 设置布尔 flag |
| `time.advance` | `amount` | 增加 `globals.clock.tick` |
| `space.move_entity` | `actor_id`, `target_location_id` | 修改实体当前位置 |
| `inventory.add_item` | `actor_id`, `item_id` | 向角色物品栏添加物品 |
| `inventory.remove_item` | `actor_id`, `item_id` | 从角色物品栏移除物品 |
| `social.adjust_trust` | `actor_id`, `amount` | 调整角色信任值 |
| `quest.set_stage` | `quest_id`, `stage` | 设置任务阶段 |
| `quest.complete` | `quest_id` | 将任务阶段设为 `completed` 并标记完成 |
| `narrative.mark_scene_seen` | `scene_id` | 把场景写入已见历史 |

## 添加新场景

推荐流程：

1. 在 `examples/medieval_town/content/scenes/` 下新增一个 JSON 文件。
2. 给场景设置唯一 `id`。
3. 设置 `scope.location` 和 `priority`。
4. 用 `conditions` 描述触发条件。
5. 在 `choices[].effects` 中描述状态变化。
6. 运行 `content-validate`。
7. 编写或更新 commands JSON，运行 `replay` 验证完整链路。
8. 必要时新增单元测试。

常见错误：

- 场景 ID 重复。
- 使用了未注册的规则或效果。
- `args` 不是数组。
- `choices` 为空。
- 场景地点和玩家当前位置不匹配。
- `repeat_policy: once` 场景已经被执行过。

## 添加新玩法模块

当前模块位于 `src/text_sandbox_engine/modules/`。一个模块通常包含三类内容：

- `register_xxx_module(registry)`：把命令、规则、效果注册进运行时。
- 规则函数：读取 state，返回 `RuleResult`，不修改状态。
- 效果函数：通过 `Transaction` 修改状态，返回 `EffectResult`。

新增模块后，需要在 `src/text_sandbox_engine/modules/__init__.py` 中注册，并加入 `DEFAULT_MODULE_VERSIONS`。如果模块影响存档兼容性，也要考虑迁移逻辑和测试。

规则函数原则：

- 只读状态。
- 返回明确的 `reason`。
- 在 `observed` 中记录调试需要的关键值。

效果函数原则：

- 只通过 `Transaction` 写状态。
- 使用清晰稳定的状态路径。
- 返回 `transaction.changes_since_last_effect()`，保证 trace 可追踪。

## 调试建议

- 内容无法加载时，先运行 `content-validate`。
- 场景没有出现时，运行 `scene-report` 查看过滤原因。
- 命令执行失败时，查看 trace 中的 `rule_results` 和 `failure_reason`。
- 状态变化不符合预期时，用 `replay` 的 `state_diff` 定位变化字段。
- 想知道某个字段由哪条命令改动时，用 `changed-by`。

## 当前边界

当前项目仍是原型，不是完整游戏产品：

- 没有交互式前端。
- 没有正式打包发布流程。
- 没有复杂 AI 叙事生成。
- 没有进入阶段 8 的工具链与生产化工作。

现阶段最适合做三件事：

- 验证核心引擎边界是否合理。
- 编写和回放结构化内容包。
- 继续扩展小而清晰的玩法模块。
