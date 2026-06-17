# Paper Radar

GitHub repository: https://github.com/ZhangYR-Tongji/paper-radar

本项目是一个本地运行、用户自定义的科研论文检索与排序工具。用户自行配置数据源、关键词组和评分权重，系统将配置保存在本地数据库中，下次启动自动加载。MVP 阶段不接入 LLM，不做自动摘要，不分析 PDF 全文。

## 目录结构

```text
backend/    FastAPI + SQLAlchemy 后端
frontend/   Next.js + React + TypeScript + Tailwind 前端
desktop/    Electron 桌面端壳
doc.md      项目需求说明
environment.yml
ENVIRONMENT_SETUP.md
```

## 桌面端一键启动

Windows 用户优先使用项目根目录的快捷方式：

```text
Paper Radar.lnk
```

它指向 `desktop\dist\win-unpacked\Paper Radar.exe`，双击后会隐藏启动后端 `127.0.0.1:8000` 和前端 `localhost:3000`，不会弹出 PowerShell/CMD 窗口。关闭桌面窗口时，前端和后端后台进程会一起停止。

首次构建或重新构建 Windows 桌面端：

```powershell
cd "C:\Users\10519\Desktop\paper ladar\desktop"
npm install
npm run build
```

Windows 构建会在项目根目录自动生成 `Paper Radar.lnk`。如果移动了项目目录或需要手动重建快捷方式，可在项目根目录执行：

```powershell
.\create-windows-shortcut.ps1
```

如果 `3000` 或 `8000` 端口已被占用，桌面应用会弹出错误提示，请先关闭已有服务后再启动。运行日志写入：

```text
.runtime\logs\backend.log
.runtime\logs\frontend.log
```

调试桌面壳时可在 `desktop` 目录执行：

```powershell
npm start
```

### macOS 桌面端

macOS 版本使用同一套 Electron 桌面壳，但需要在 macOS 机器上构建：

```bash
cd "/path/to/paper ladar/desktop"
npm install
npm run build:mac
```

构建完成后打开：

```text
desktop/dist/mac*/Paper Radar.app
```

macOS 桌面端同样会隐藏启动后端 `127.0.0.1:8000` 和前端 `localhost:3000`，关闭窗口时会停止前后端后台进程。它会自动查找 `paper-radar` Conda 环境，支持常见的 Miniconda、Anaconda 和 Miniforge 安装位置；如果环境不在常规位置，可先设置：

```bash
export PAPER_RADAR_CONDA_ENV_DIR="/absolute/path/to/envs/paper-radar"
```

如果端口已被占用，应用会弹出错误提示。运行日志仍写入：

```text
.runtime/logs/backend.log
.runtime/logs/frontend.log
```

如需从零复现环境，参考 `ENVIRONMENT_SETUP.md`。

## 开发环境

```powershell
conda activate paper-radar
```

默认开发服务地址：

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
Health:   http://127.0.0.1:8000/api/health
```

## 开发：启动后端

```powershell
cd backend
python -m app.cli
uvicorn app.main:app --reload --port 8000
```

后端健康检查：

```powershell
curl http://localhost:8000/api/health
```

## 常用 API

清空所有检索运行记录：

```powershell
curl -X POST http://localhost:8000/api/fetch/runs/clear
```

该接口会删除 `fetch_runs`、`fetch_run_items` 和 `fetch_cursors`，并重置数据源的最近成功/错误状态；不会删除已入库论文、文献库、反馈、数据源配置或关键词组。如果当前有检索任务正在运行，接口会返回 `409`。

## 开发：启动前端

```powershell
cd frontend
npm run dev
```

默认前端地址：

```text
http://localhost:3000
```

## 当前脚手架状态

- 已创建 FastAPI 应用、数据库模型、Settings API、Fetch API、Paper API、Feedback API。
- 已实现 arXiv、OpenAlex、Crossref、Semantic Scholar 元数据适配器；OSF 默认禁用。
- 已实现手动增量 fetch、source × keyword group cursor、去重、规则评分、分类和反馈偏好更新。
- 已创建 Next.js 应用壳和 MVP 页面路由：`/`、`/settings`、`/library`、`/feedback`、`/search`、`/fetch-runs/[id]`。
- 前端页面已接入真实后端 API，可配置来源/关键词/权重、手动抓取、查看推荐、反馈和文献库。
- 已支持单篇和文献库批量导出 `RIS` / `BibTeX`，可导入 Zotero。
- 发布版不预置任何领域关键词组；用户在设置页新建的关键词组会保存到本地 SQLite 数据库。
- 本地开发默认使用 SQLite，后续可通过 `DATABASE_URL` 切换 PostgreSQL。

## GitHub 同步

后续改动默认同步到 GitHub：

```powershell
git status
git add <changed-files>
git commit -m "描述本次改动"
git push
```
