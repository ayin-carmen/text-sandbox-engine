# 阶段 6：模块缺口清单

本清单来自 `examples/medieval_town/` 垂直切片制作过程。

## 高优先级

1. `inventory`
   阶段 7 已用 `inventory.add_item`、`inventory.remove_item` 和 `inventory.has_item` 覆盖基础物品持有与转移。

2. `social`
   阶段 7 已用 `social.adjust_trust` 和 `social.trust_at_least` 覆盖基础信任变化与判断。

3. `access`
   阶段 7 已在 `space.location_accessible` 中支持 `required_flag` 动态准入。

4. `history`
   阶段 7 已用 `narrative.mark_scene_seen` 和 `repeat_policy: once` 覆盖一次性场景历史。

## 中优先级

1. `quest`
   阶段 7 已用 `quest.set_stage`、`quest.complete` 和 `quest.stage_is` 覆盖基础任务阶段。

2. `schedule`
   NPC 位置当前是静态状态，后续需要按时间段移动。

3. `content_entities`
   地点和 NPC 目前仍写在 world state 中，后续应支持从内容包加载实体初始定义。

## 暂不需要

1. `economy`
   当前切片没有交易和价格。

2. `law`
   当前只有守卫询问，没有犯罪、通缉或处罚。

3. `clothing`
   当前切片没有衣着判断需求。
