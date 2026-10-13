# Paper Radar

GitHub repository: https://github.com/ZhangYR-Tongji/paper-radar

本项目是一个本地运行、用户自定义的科研论文检索与排序工具。用户自行配置数据源、关键词组和评分权重，系统将配置保存在本地数据库中，下次启动自动加载。支持本地中英文语义匹配，不调用付费模型 API，不分析 PDF 全文。

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

## 评分规则

评分结合标题、摘要的词面匹配与本地语义向量，分数表示与已配置研究方向的匹配程度，不表示论文质量或相关性的概率。当前算法版本为 3。

- 每个关键词组独立计算分数，最终取最高分。增加其他研究方向或未命中的候选词，不会稀释已有匹配。组内优先权重只影响本组，不以其他组的权重为分母；设为 0 时本组不参与评分。
- 正向词是候选表达，命中任意一个即可建立词面主题匹配；必须词是本组的前置条件，需全部出现，语义匹配也不能绕过。没有正向词时，必须词也可作为主题依据。只有研究描述的组可建立语义匹配；空组不匹配任何论文。
- 主题词在标题出现得到 90 分主题分，仅在摘要出现得到 75 分；额外主题词每个加 5 分，最多加 10 分，可选词每个加 5 分，最多加 10 分，主题分封顶 100。仅有可选词时，每词 10 分、封顶 35，不能凭通用方法词进入默认推荐。
- 词面匹配统一大小写、空白和连字符，支持常见英文复数与英文单词边界。空词和同一词的大小写、连字符变体只计一次；额外的语义主题证据由本地模型计算。
- 默认基础权重为主题 0.80、方法 0.05、来源 0、新鲜度 0.15。四项按比例归一化；全部设为 0 时基础分为 0。方法分仅作小幅辅助；来源保持中性 50 分，不根据名称中的 `journal` 等字样推断质量。
- 每组基础分先乘该组优先权重，并以本组主题分为上限。偏好分以 50 为中性，按 `(偏好分 - 50) × 2 × 偏好权重` 加减，默认最多调整 ±10 分。每个不同负向词产生 25 分惩罚项、封顶 100，再乘负向权重（默认 0.20，即每词扣 5 分，最多扣 20 分）；负向词只影响所属方向，论文不因另一个方向的排除词而被扣分。
- 每组调整后得分限制在 0 到本组主题分之间，因此辅助信号和高优先权重无法替代主题匹配。论文取各组最高得分，保留所有匹配组与正向词标签；数值分解及负向词来自最终获胜的组。关闭“参与排序”的来源得分为 0。
- 分类门槛为 80 / 60 / 40：高度相关、值得查看、低优先级，其余过滤。默认推荐门槛为 50；强标题匹配在没有反馈时也可达到高度相关。门槛是规则分档，仍需用用户标注的论文验证实际推荐效果。

首次启动新版时，系统会添加评分版本记录并重算已有论文。完全等于旧默认值的权重自动升级为上述默认值，自定义权重保留；论文、收藏和反馈保留。重算与版本更新在同一事务中完成，之后启动不会重复执行本次升级。手动运行 Alembic 迁移后，仍由应用启动完成评分重算。

## 本地语义匹配

使用 MIT 许可的 [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small)，固定模型 revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`，通过 [FastEmbed](https://github.com/qdrant/fastembed) / ONNX 在 CPU 上计算 384 维向量。研究方向使用 `query:`，论文使用 `passage:`；模型最大输入 512 tokens，优先保留标题和摘要前部。首次模型文件下载约 470 MB，之后加载与推理仅使用本地文件。

新建环境时 `environment.yml` 会安装语义依赖。升级已有环境可运行：

```powershell
conda activate paper-radar
cd backend
python -m pip install -r requirements-semantic.txt
```

打开设置页的“本地语义匹配”，点击“下载并准备本地模型”。下载完成后自动在后台重算已有论文。模型默认位于用户目录 `.cache/paper-radar/models`；可通过 `SEMANTIC_MODEL_CACHE_DIR` 指定绝对缓存目录。模型与向量不会提交到 Git。

在每个关键词组的“研究方向描述”中填写希望找到的研究内容，可使用中文，例如“研究通过拉索驱动柔性机械臂，实现形状控制与接触操作”。系统分别比较完整方向描述与聚焦正向/必须词的核心主题查询，取两者相似度较低值；这可减少描述中的通用方法词稀释研究方向。只有描述的组使用该描述。负向词不会写进语义查询。即使论文使用不同表达、没有原关键词，足够强的语义证据也能成为补充候选；必需词仍需字面满足，负向词仍按组扣分。论文卡片展示“语义候选”方向与可展开依据，语义召回不会伪造关键词命中。

默认相似度门槛为 0.82。E5 的 cosine 有较高基线，不能直接将相似度乘 100 当作相关概率：双重匹配的较低相似度低于门槛时不提供语义证据；达到门槛时语义主题分为 60，并线性增长至相似度 0.92 时的 100 分（门槛调高时上界至少比门槛高 0.02，且不超过 1）。主题分取 `max(词面主题分, 语义主题分 × 语义影响强度)`，默认影响强度 0.75，之后沿用现有方向优先级、权重和惩罚。默认仅凭语义的最终分数最多 75，进入补充候选，不直接判为“高度相关”。这些门槛为可调整的启发式，需要用用户标注样本验证实际推荐质量；对于细分研究方向，轻量向量模型仍可能混淆相邻主题。

向量缓存在 SQLite/PostgreSQL 的 `semantic_embeddings` 中，按模型 ID、固定 revision、输入格式版本、文本 SHA256 和 query/passage 类型复用；研究描述或论文内容改变时仅计算缺失向量。模型不可用时保留已有有效缓存，对缺失部分使用词面评分，设置页显示准备/失败状态。

启动过程不会下载模型或同步执行长推理；已准备模型的缺失索引由后台补全。设置和反馈先用缓存更新分数，再按需补齐向量。后台任务使用独立数据库会话，最终评分在短事务中重新读取最新配置，避免旧任务覆盖新设置；任务结束期间的新请求会排队补做。空论文文本直接使用词面回退，不会拖垮整批。重启后的中断任务按缺失内容继续，论文列表会在后台完成后自动刷新。

模型文件损坏或实际加载失败时会撤销准备状态。再次点击“下载并准备本地模型”会显式下载修复，成功后恢复离线推理。

语义接口：`GET/PUT /api/settings/semantic`，`POST /api/settings/semantic/prepare`（显式下载与重算），`POST /api/settings/semantic/reindex`（仅用本地模型重算）；后台操作返回 `202`，进度通过 GET 查询。

## GitHub 同步

后续改动默认同步到 GitHub：

```powershell
git status
git add <changed-files>
git commit -m "描述本次改动"
git push
```
