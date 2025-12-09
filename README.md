# BOSS 直聘自动化岗位助手

该项目使用 **Playwright + FastAPI + SQLModel + OpenAI/Claude**，完成每日职位抓取、AI 匹配、存储与日报输出，支持本地运行和 GitHub Actions 定时任务。

## 功能概览

- Playwright (headless) 抓取 BOSS 直聘职位，保持登录状态。
- 调用 OpenAI 或 Claude 评估匹配度，并生成打招呼文案。
- SQLite + SQLModel 保存岗位与评估结果。
- FastAPI API 供 n8n / GitHub Actions 调用。
- `scripts/daily_run.py` 一键执行抓取 → 评估 → 生成 `output/daily_report.md`。
- GitHub Actions `cron` 每天自动运行并上传日报 artifacts。

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\\Scripts\\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. 登录 BOSS，生成 `storage_state.json`

1. 保证已安装 Playwright CLI（随 `playwright` 安装）。
2. 执行：
   ```bash
   playwright codegen https://www.zhipin.com
   ```
3. 在弹出的浏览器中手动登录账号。
4. 在 codegen 页面保存状态：点击右上角 **Save storage state**（或使用 `--save-storage` 参数）生成 `storage_state.json`，将文件放在项目根目录。

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填写个人配置：

```bash
cp .env.example .env
# 编辑 .env 填写 OpenAI/Claude key、搜索关键词、简历摘要等
```

关键配置：

- `SEARCH_URL`：BOSS 搜索页 URL。
- `RESUME_PROFILE`：你的简历摘要，提供给 LLM 参考。
- `OPENAI_API_KEY` / `CLAUDE_API_KEY`：AI 服务 key，按 `MODEL_PROVIDER` 选择。
- `MODEL_PROVIDER`：`OPENAI` 或 `ANTHROPIC`。
- `ANTHROPIC_API_URL`：可选，Claude 代理/自建网关地址（例如 `https://anyrouter.top`）。
- `MAX_JOBS`：每日抓取前 N 条。

### 4. 初始化数据库并本地运行 API

```bash
uvicorn app.main:app --reload
```

API 路由示例：
- `GET /health`：健康检查
- `GET /jobs`：查看已抓取岗位
- `GET /jobs/{id}/evaluation`：查看 AI 评估
- `POST /run`：异步触发完整流程

### 5. 手动运行每日流程

```bash
python scripts/daily_run.py
```

运行完成后生成：`output/daily_report.md`。

### 6. 查看 SQLite 数据

数据库路径默认 `data/jobs.db`。可使用 `sqlite3` 或 DB 浏览器查看：

```bash
sqlite3 data/jobs.db
sqlite> .tables
sqlite> SELECT title, match_score FROM job JOIN jobeval ON job.id = jobeval.job_id LIMIT 5;
```

### 7. GitHub Actions 配置

在仓库设置 Secrets：

- `OPENAI_API_KEY`
- `CLAUDE_API_KEY`
- `ANTHROPIC_API_URL`（如使用代理）
- `RESUME_PROFILE`
- `SEARCH_URL`

Workflow 每天北京时间 09:00 运行，执行 `python scripts/daily_run.py` 并上传 `output/daily_report.md` 为 artifacts。

### 8. 整体流程

1. Playwright 使用 `storage_state.json` 登录状态抓取职位卡片及 JD。
2. AI (OpenAI/Claude) 评估匹配度，生成打招呼话术。
3. SQLModel 写入 `jobs` 和 `job_eval` 表。
4. 生成 `output/daily_report.md`（Top10 推荐+关键字段+打招呼+JD 摘要）。

如需调整参数，可修改 `app/config.py` 或 `.env`。
