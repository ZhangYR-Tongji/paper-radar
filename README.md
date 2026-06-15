# Design-AI Paper Radar

GitHub repository: https://github.com/ZhangYR-Tongji/design-ai-paper-radar

本项目是一个本地优先的论文检索与排序工具，用于发现 AI-assisted design research 相关新论文。MVP 阶段不接入 LLM，不做自动摘要，不分析 PDF 全文。

## 目录结构

```text
backend/    FastAPI + SQLAlchemy 后端
frontend/   Next.js + React + TypeScript + Tailwind 前端
doc.md      项目需求说明
environment.yml
ENVIRONMENT_SETUP.md
```

## 启动环境

```powershell
conda activate design-ai-paper-radar
```

如需从零复现环境，参考 `ENVIRONMENT_SETUP.md`。

## 启动后端

```powershell
cd backend
python -m app.cli
uvicorn app.main:app --reload --port 8000
```

后端健康检查：

```powershell
curl http://localhost:8000/api/health
```

## 启动前端

```powershell
cd frontend
npm run dev
```

默认前端地址：

```text
http://localhost:3000
```

## 当前脚手架状态

- 已创建 FastAPI 应用、数据库模型、种子数据、Settings API、占位 Fetch/Paper/Feedback API。
- 已创建 Next.js 应用壳和 MVP 页面路由：`/`、`/settings`、`/library`、`/feedback`、`/search`、`/fetch-runs/[id]`。
- 本地开发默认使用 SQLite，后续可通过 `DATABASE_URL` 切换 PostgreSQL。

## GitHub 同步

后续改动默认同步到 GitHub：

```powershell
git status
git add <changed-files>
git commit -m "描述本次改动"
git push
```
