# 阶段 9 低代码协议

## 目的

阶段 9 的低代码层只负责把结构化编辑结果转换为现有场景 JSON，不实现第二套规则或效果引擎。运行时仍由 Python 引擎执行，JSON 高级模式继续保留。

## Registry 参数元数据

`GET /api/metadata/registry` 返回的每个规则和效果包含：

- `kind`：`rule`、`effect` 或 `command`
- `type_id`：运行时稳定类型 ID
- `label`：中文显示名称
- `category`：功能分类
- `description`：功能说明
- `module`、`module_version`：来源模块信息
- `reads` 或 `writes`：典型状态路径
- `parameters`：按运行时参数顺序排列的参数描述

每个参数包含：

```json
{
  "name": "item",
  "label": "物品",
  "data_type": "entity",
  "widget": "reference_select",
  "reference_type": "item",
  "required": true,
  "default": "item.bread_basket",
  "description": "引用的物品"
}
```

`widget` 当前支持 `boolean`、`integer`、`number`、`text` 和 `reference_select`。未知控件必须回退为普通文本输入，不能阻止 JSON 高级模式使用。

## 引用 DTO

`GET /api/metadata/references` 返回当前工作区的引用索引；使用 `?type=actor` 可以按类型过滤。

```json
{
  "id": "actor.elda",
  "type": "actor",
  "label": "艾尔达",
  "source": "world_state.json",
  "valid": true
}
```

第一版索引 `actor`、`location`、`item`、`quest`、`scene` 和 `flag`。角色和地点名称来自 world state，场景名称来自场景文档；暂时没有独立物品目录时，已有内容中的物品引用作为可选项保留。无法解析的角色、地点、任务或场景引用标记为 `valid: false`，前端必须保留其原始 ID 并提示问题。

## 表单与 JSON 映射

结构化表单使用同一份 JSON 草稿：

- 规则参数按 Registry `parameters` 顺序写入 `conditions[*].args` 或 `choices[*].visible_if[*].args`。
- 效果参数按 Registry `parameters` 顺序写入 `choices[*].effects[*].args`。
- 引用选择器只改变参数值，不改变规则、效果和场景文件格式。
- 不认识的类型或额外参数继续交给 JSON 高级模式处理。

## 交互边界

参数选择器不隐式创建角色、地点、物品、任务或场景。保存前仍调用真实内容校验；前端不能根据元数据自行执行规则或推断运行结果。
