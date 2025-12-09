from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import Session, select

from app.ai.evaluator import evaluate_job
from app.browser.collect_jobs import collect_jobs
from app.config import settings
from app.db.database import engine, init_db
from app.db.models import Job, JobCreate, JobEval
from app.utils.notion import push_jobs_to_notion
from app.utils.report import generate_daily_report


logger = logging.getLogger(__name__)


async def _save_jobs(session: Session, jobs: List[JobCreate]) -> List[Job]:
    saved: List[Job] = []
    for job_data in jobs:
        existing = session.exec(select(Job).where(Job.detail_url == job_data.detail_url)).first()
        if existing:
            saved.append(existing)
            continue
        job = Job(**job_data.model_dump())
        session.add(job)
        session.commit()
        session.refresh(job)
        saved.append(job)
    return saved


def _evaluate_jobs(session: Session, jobs: List[Job]) -> List[JobEval]:
    evaluations: List[JobEval] = []
    resume_profile = settings.load_resume_profile()
    for job in jobs:
        existing_eval = session.exec(select(JobEval).where(JobEval.job_id == job.id)).first()
        if existing_eval:
            evaluations.append(existing_eval)
            continue
        try:
            evaluation = evaluate_job(job, resume_profile, settings.get_api_key())
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to evaluate job %s (%s)", job.title, job.id)
            evaluation = JobEval(
                job_id=job.id,
                match_score=0,
                tech_match="评估失败：模型调用异常",
                experience_match=str(exc),
                pros=[],
                cons=[],
                recommend=False,
                greeting_messages=[],
            )
        evaluation.job_id = job.id
        session.add(evaluation)
        session.commit()
        session.refresh(evaluation)
        evaluations.append(evaluation)
    return evaluations


async def run_daily_pipeline() -> None:
    init_db()
    jobs = await collect_jobs(settings.search_url, settings.max_jobs)
    with Session(engine) as session:
        stored_jobs = await _save_jobs(session, jobs)
        evaluations = _evaluate_jobs(session, stored_jobs)
    generate_daily_report(stored_jobs, evaluations, settings.output_dir)
    if settings.notion_api_key and settings.notion_database_id:
        created_pages = await push_jobs_to_notion(
            stored_jobs,
            evaluations,
            settings.notion_api_key,
            settings.notion_database_id,
        )
        print(f"Pushed {len(created_pages)} jobs to Notion database")
    print(f"Daily pipeline completed at {datetime.utcnow().isoformat()} with {len(jobs)} jobs")


if __name__ == "__main__":
    asyncio.run(run_daily_pipeline())
