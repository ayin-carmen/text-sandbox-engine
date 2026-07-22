# 阶段 8 编辑器使用说明

## 组成

阶段 8 编辑器由三层组成：

1. `src/text_sandbox_editor_api/`：FastAPI 本地适配层，只返回稳定 JSON DTO。
2. `editor/`：React + TypeScript + Vite 界面，使用 Monaco JSON 编辑器和 Cytoscape 关系图。
3. `src-tauri/`：Tauri 2 桌面壳，负责窗口和本地 Python API 进程生命周期。

前端不执行规则和效果。所有规则判断、事务提交、场景候选分析和命令回放都调用现有 Python 引擎。

## 启动

在仓库根目录：

```powershell
$env:PYTHONPATH = "src"
python -m pip install -e ".[editor]"
python -m text_sandbox_editor_api
```

另开终端：

```powershell
cd editor
npm install
npm run dev
```

打开 `http://localhost:5173`，输入内容包路径，例如 `examples/medieval_town`。

## 编辑流程

1. 从左侧内容树选择场景。
2. 在“结构化表单”中修改 ID、地点、优先级、正文、条件、选项和效果。
3. 需要直接处理完整 JSON 时切换“JSON 源码”。
4. 点击“校验”查看稳定错误码、来源文件和 JSON path。
5. 点击“保存”。保存前会再次执行内容验证，外部修改会返回冲突，不会静默覆盖。

检查器还提供复制、重命名和删除场景。重命名和删除会先检查关系图中的引用；有引用时 API 返回冲突，避免破坏其他内容。

每次成功保存会保留同目录的 `.bak` 文件。恢复时可以把备份文件复制回原文件，再刷新工作区。

## 关系图和运行预览

“关系图”从真实场景 JSON 和世界状态引用生成节点与边。场景、规则、效果、地点、角色、任务、物品和状态路径使用不同节点类型；边中带有来源文件和 JSON path。

“运行预览”会创建内存运行会话。命令执行后可以查看 trace、规则结果、效果变化和候选场景。预览不会修改原始 `world_state.json`。

## API

主要接口：

```text
POST /api/workspaces/open
GET  /api/workspaces/tree
GET  /api/content/scenes
PUT  /api/content/scenes/{scene_id}
GET  /api/metadata/registry
POST /api/validation/content
GET  /api/graph/content
POST /api/runtime/sessions
POST /api/runtime/sessions/{session_id}/commands
POST /api/diagnostics/scene-candidates
POST /api/diagnostics/state-diff
POST /api/diagnostics/changed-by
```

API 默认绑定 `127.0.0.1:8765`。编辑器运行时使用内存会话，关闭 API 后会话状态消失。

## 桌面构建

在目标机器没有 Python 的情况下，先将本地 API 打包为单文件，再由 Tauri 将它作为资源放入安装包。开发机需要 Rust、Node.js 和 PyInstaller：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_editor.ps1
```

脚本会生成 `build/editor-runtime/text-sandbox-editor-api.exe`，构建前端并调用 Tauri。Tauri 配置使用 `editor/dist` 作为前端资源，并优先启动安装包内的 API 单文件；开发环境没有打包 API 时才回退到 `python -m text_sandbox_editor_api`。安装包生成在 `src-tauri/target/release/bundle/`。

仓库还提供 `.github/workflows/phase8-desktop.yml`。推送到 `main` 或手动触发该工作流，会在 GitHub Windows Runner 上使用官方 Rust 工具链构建并上传 NSIS 安装包；这也是本机没有 Rust 时的标准构建路径。
