# 环境配置说明

本项目使用 Conda 管理本地开发环境，当前已创建环境：

```powershell
conda activate paper-radar
```

## 已配置内容

- Python 3.11.15
- Node.js 20.20.2
- npm 10.8.2
- Git 2.54.0
- GitHub CLI 2.94.0
- 后端依赖：FastAPI、SQLAlchemy、Alembic、Pydantic Settings、httpx、rapidfuzz、arxiv、psycopg、pytest、ruff 等

MVP 阶段建议先用 SQLite 开发；后续需要生产一致性时再安装 PostgreSQL 或 Docker。

## 从零复现

在项目根目录执行：

```powershell
conda env create -f environment.yml
conda activate paper-radar
```

如环境已存在，需要更新依赖：

```powershell
conda env update -n paper-radar -f environment.yml --prune
conda activate paper-radar
```

## 验证环境

```powershell
python --version
node --version
npm --version
git --version
gh --version
python -c "import fastapi, sqlalchemy, httpx, rapidfuzz, arxiv, psycopg; print('backend deps ok')"
```

## 前端依赖说明

前端工程位于 `frontend/`。首次拉取项目或依赖变化后执行：

```powershell
cd frontend
npm install
npm run dev
```

不要在 MVP 阶段安装或接入 OpenAI API、LangChain、本地 LLM、PDF 全文分析等依赖。
