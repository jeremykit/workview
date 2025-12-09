from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from app.db.models import Job, JobEval


def generate_daily_report(jobs: Iterable[Job], evaluations: Iterable[JobEval], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "daily_report.md"

    eval_map = {e.job_id: e for e in evaluations if e.job_id is not None}
    ranked: List[tuple[Job, JobEval]] = []
    for job in jobs:
        evaluation = eval_map.get(job.id)
        if evaluation:
            ranked.append((job, evaluation))
    ranked.sort(key=lambda item: item[1].match_score, reverse=True)

    lines: List[str] = []
    lines.append(f"# 每日岗位报告 - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("\n本报告由 Playwright 抓取 + LLM 评估自动生成。\n")

    top_items = ranked[:10]
    if not top_items:
        lines.append("目前没有可用的推荐岗位。")
    else:
        for idx, (job, evaluation) in enumerate(top_items, start=1):
            lines.append(f"## {idx}. {job.title} - {job.company}")
            lines.append(f"- 城市：{job.city}")
            lines.append(f"- 薪资：{job.salary}")
            lines.append(f"- 匹配度：{evaluation.match_score}")
            lines.append(f"- 技术匹配：{evaluation.tech_match}")
            lines.append(f"- 经验匹配：{evaluation.experience_match}")
            if evaluation.greeting_messages:
                greetings = " | ".join(evaluation.greeting_messages[:2])
                lines.append(f"- 打招呼：{greetings}")
            lines.append("- JD 摘要：")
            lines.append(f"  {job.jd_full[:300]}...")
            lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
