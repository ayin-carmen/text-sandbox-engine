# Text Sandbox Editor

阶段 8 的 React + TypeScript + Vite 编辑器前端。它只消费本地编辑器 API 返回的 JSON DTO，规则判断和效果执行仍由 Python 引擎完成。

开发时先在仓库根目录启动 API：

```powershell
$env:PYTHONPATH = "src"
python -m text_sandbox_editor_api
```

再启动前端：

```powershell
cd editor
npm install
npm run dev
```

默认工作区是 `examples/medieval_town`，也可以在顶部输入其他本地内容包路径。
