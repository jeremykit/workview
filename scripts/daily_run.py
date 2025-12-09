from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.ai.evaluator import evaluate_job
from app.browser.collect_jobs import collect_jobs
from app.config import settings
from app.db.database import engine, init_db
from app.db.models import Job, JobCreate, JobEval
from app.utils.report import generate_daily_report


async def _save_jobs(session: Session, jobs: List[JobCreate]) -> List[Job]:
    saved: List[Job] = []
    for job_data in jobs:
        existing = session.exec(select(Job).where(Job.detail_url == job_data.detail_url)).first()
        if existing:
            saved.append(existing)
            continue
        job = Job(**job_data.dict())
        session.add(job)
        session.commit()
        session.refresh(job)
        saved.append(job)
    return saved


def _evaluate_jobs(session: Session, jobs: List[Job]) -> List[JobEval]:
    evaluations: List[JobEval] = []
    for job in jobs:
        existing_eval = session.exec(select(JobEval).where(JobEval.job_id == job.id)).first()
        if existing_eval:
            evaluations.append(existing_eval)
            continue
        evaluation = evaluate_job(job, settings.resume_profile, settings.get_api_key())
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
    print(f"Daily pipeline completed at {datetime.utcnow().isoformat()} with {len(jobs)} jobs")


if __name__ == "__main__":
    asyncio.run(run_daily_pipeline())
