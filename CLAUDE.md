# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BOSS 直聘自动化岗位助手：使用 Playwright + FastAPI + SQLModel + OpenAI/Claude 实现职位抓取、AI 匹配评估、数据持久化和日报生成。支持本地运行和 GitHub Actions 定时任务。

## Development Setup

### 依赖安装
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 登录状态生成
```bash
playwright codegen https://www.zhipin.com
# 手动登录后保存 storage_state.json 到项目根目录
```

### 环境配置
复制 `.env.example` 为 `.env`，填写：
- `SEARCH_URL`：BOSS 搜索页 URL
- `RESUME_PROFILE` 或 `RESUME_PROFILE_URL`：简历内容或在线简历地址
- `OPENAI_API_KEY` / `CLAUDE_API_KEY`：根据 `MODEL_PROVIDER` 选择
- `MODEL_PROVIDER`：`OPENAI` 或 `ANTHROPIC`
- `NOTION_API_KEY` / `NOTION_DATABASE_ID`：可选，用于同步到 Notion

## Common Commands

### 本地开发
```bash
# 启动 FastAPI 服务
uvicorn app.main:app --reload

# 运行完整流程（抓取 + 评估 + 报告）
python scripts/daily_run.py
```

### 数据库操作
```bash
# 查看 SQLite 数据
sqlite3 data/jobs.db
# 示例查询
SELECT title, match_score FROM job
JOIN jobeval ON job.id = jobeval.job_id
ORDER BY match_score DESC LIMIT 10;
```

### 测试单个组件
```bash
# 测试职位抓取（需先在 Python REPL 中）
python
>>> from app.browser.collect_jobs import collect_jobs
>>> import asyncio
>>> jobs = asyncio.run(collect_jobs("SEARCH_URL", 5))

# 测试 AI 评估（需先在 Python REPL 中）
>>> from app.ai.evaluator import evaluate_job
>>> from app.db.models import Job
>>> evaluation = evaluate_job(job_instance, resume_text, api_key)
```

## Architecture

### 数据流
1. **Playwright 爬虫** (`app/browser/collect_jobs.py`)：使用 `storage_state.json` 维持登录，抓取职位列表和详情页 JD
2. **数据持久化** (`app/db/`)：SQLModel 定义 `Job` 和 `JobEval` 表，SQLite 存储
3. **AI 评估** (`app/ai/evaluator.py`)：调用 OpenAI 或 Claude API，解析 JSON 响应生成匹配度、优缺点和打招呼文案
4. **报告生成** (`app/utils/report.py`)：输出 Top10 岗位到 `output/daily_report.md`
5. **Notion 同步**（可选，`app/utils/notion.py`）：推送 Top10 到 Notion Database

### 核心模块

**`app/config.py`**：Pydantic BaseSettings 管理环境变量，`load_resume_profile()` 优先使用 `RESUME_PROFILE`，为空时从 `RESUME_PROFILE_URL` 抓取

**`app/browser/collect_jobs.py`**：
- 使用 `storage_state_path` 加载登录 cookies
- 随机滚动和延迟模拟人类行为
- 为每个职位卡片打开详情页获取完整 JD

**`app/ai/evaluator.py`**：
- `_build_prompt()`：构造包含简历和 JD 的提示词，要求返回结构化 JSON
- `evaluate_job()`：根据 `MODEL_PROVIDER` 调用 OpenAI 或 Anthropic API
- `_parse_response()`：容错 JSON 解析，提取花括号内容

**`app/db/models.py`**：
- `Job`：职位基本信息（标题、公司、薪资、城市、详情链接、JD 全文）
- `JobEval`：AI 评估结果（匹配分数、技术匹配、经验匹配、优缺点、推荐标志、打招呼文案）
- 使用 SQLModel 一对多关系：`Job.evaluations` ↔ `JobEval.job`

**`scripts/daily_run.py`**：
- `_save_jobs()`：去重保存，跳过已存在的 `detail_url`
- `_evaluate_jobs()`：批量评估，跳过已评估的职位
- `run_daily_pipeline()`：orchestrate 完整流程，可选推送 Notion

**`app/main.py`**：FastAPI 应用，提供：
- `GET /health`：健康检查
- `GET /jobs`：列出所有职位
- `GET /jobs/{id}/evaluation`：获取评估结果
- `POST /run`：异步触发完整流程
- `POST /jobs/{id}/evaluate`：单独评估一个职位
- `POST /report`：生成日报

### Playwright Selectors

**`app/browser/selectors.py`**：定义 BOSS 直聘页面选择器常量（`LIST_ITEM_SELECTOR`, `TITLE_SELECTOR`, `COMPANY_SELECTOR`, `JD_FULL_SELECTOR` 等）。如 BOSS 页面结构变化，仅需修改此文件。

### GitHub Actions

**`.github/workflows/daily.yml`**：
- 每天 UTC 01:00（北京时间 09:00）自动运行
- 设置 Python 3.11、安装依赖、执行 `scripts/daily_run.py`
- 上传 `output/daily_report.md` 为 artifact

需在 GitHub Secrets 中配置：`OPENAI_API_KEY`, `CLAUDE_API_KEY`, `ANTHROPIC_API_URL`, `RESUME_PROFILE`, `RESUME_PROFILE_URL`, `SEARCH_URL`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`

## Important Notes

- **登录状态维护**：`storage_state.json` 包含 BOSS 直聘登录 cookies，需定期更新（过期后重新运行 `playwright codegen`）
- **反爬策略**：`_human_pause()` 和随机滚动减少被检测风险，调整 `collect_jobs.py` 中的延迟参数
- **AI Provider 切换**：修改 `.env` 中的 `MODEL_PROVIDER` 和对应 API key
- **Notion 集成**：Notion Database 需包含字段：`Name` (Title), `Company`, `City`, `Salary`, `Detail URL` (URL), `Match Score` (Number), `Recommend` (Checkbox), `Greeting` (Rich text)
- **简历来源优先级**：`RESUME_PROFILE` 非空时直接使用，否则从 `RESUME_PROFILE_URL` 抓取（缓存在 `Settings._cached_resume`）
- **数据库位置**：默认 `data/jobs.db`，可通过 `DATABASE_URL` 环境变量修改
- **去重逻辑**：根据 `detail_url` 判断职位是否已存在，避免重复抓取和评估
