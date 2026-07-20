# 阶段 6：数据格式修订建议

## 建议 1：实体内容从 world state 中拆出

当前地点和 NPC 仍直接写在 `world_state.json` 的 `entities` 中。

建议后续支持：

```text
content/
  entities/
    locations/*.json
    actors/*.json
  scenes/*.json
```

运行时新开局时由内容包生成初始 world state，存档只保存运行时变化。

## 建议 2：规则参数支持命名参数

当前规则参数全部是位置数组：

```json
{
  "rule": "actor.is_present",
  "args": ["actor.elda"]
}
```

当规则复杂后，可考虑支持：

```json
{
  "rule": "actor.is_present",
  "args": {
    "actor": "actor.elda",
    "location": "actor.player.location"
  }
}
```

## 建议 3：场景重复策略落地到状态

当前 `repeat_policy` 和 `cooldown` 是内容字段，但没有正式驱动逻辑。

建议后续在 `history` 或 `cooldowns` 中记录：

1. 已出现的 scene id。
2. 最近出现 tick。
3. repeat policy 的判断结果。

## 建议 4：新增关系与任务数据结构

阶段 6 中的“答应送面包”和“与守卫交谈”已经暴露出关系与任务阶段需求。

建议后续为 `social` 与 `quest` 模块提供正式 schema，而不是长期使用旗标替代。
