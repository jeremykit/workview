from __future__ import annotations

import asyncio
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from app.ai.evaluator import evaluate_job
from app.config import settings
from app.db.database import get_session, init_db
from app.db.models import Job, JobEval
from app.utils.report import generate_daily_report
from scripts.daily_run import run_daily_pipeline

app = FastAPI(title="Boss Zhipin Job Assistant")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/jobs", response_model=List[Job])
def list_jobs(session: Session = Depends(get_session)) -> List[Job]:
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    return jobs


@app.get("/jobs/{job_id}/evaluation", response_model=JobEval)
def get_evaluation(job_id: int, session: Session = Depends(get_session)) -> JobEval:
    evaluation = session.exec(select(JobEval).where(JobEval.job_id == job_id)).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


@app.post("/run")
async def run_pipeline() -> dict[str, str]:
    asyncio.create_task(run_daily_pipeline())
    return {"message": "Pipeline started"}


@app.post("/jobs/{job_id}/evaluate", response_model=JobEval)
async def evaluate_single(job_id: int, session: Session = Depends(get_session)) -> JobEval:
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    evaluation = evaluate_job(job, settings.resume_profile, settings.get_api_key())
    evaluation.job_id = job_id
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    return evaluation


@app.post("/report")
def build_report(session: Session = Depends(get_session)) -> dict[str, str]:
    jobs = session.exec(select(Job)).all()
    evaluations = session.exec(select(JobEval)).all()
    path = generate_daily_report(jobs, evaluations, settings.output_dir)
    return {"report_path": str(path)}
