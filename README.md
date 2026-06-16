# Paper Radar

GitHub repository: https://github.com/ZhangYR-Tongji/paper-radar

本项目是一个本地运行、用户自定义的科研论文检索与排序工具。用户自行配置数据源、关键词组和评分权重，系统将配置保存在本地数据库中，下次启动自动加载。MVP 阶段不接入 LLM，不做自动摘要，不分析 PDF 全文。

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
conda activate paper-radar
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

- 已创建 FastAPI 应用、数据库模型、Settings API、Fetch API、Paper API、Feedback API。
- 已实现 arXiv、OpenAlex、Crossref、Semantic Scholar 元数据适配器；OSF 默认禁用。
- 已实现手动增量 fetch、source × keyword group cursor、去重、规则评分、分类和反馈偏好更新。
- 已创建 Next.js 应用壳和 MVP 页面路由：`/`、`/settings`、`/library`、`/feedback`、`/search`、`/fetch-runs/[id]`。
- 前端页面已接入真实后端 API，可配置来源/关键词/权重、手动抓取、查看推荐、反馈和文献库。
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
