from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


class JobBase(SQLModel):
    title: str
    company: str
    salary: str
    city: str
    detail_url: str
    jd_full: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Job(JobBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    evaluations: list["JobEval"] = Relationship(back_populates="job")


class JobCreate(JobBase):
    pass


class JobEvalBase(SQLModel):
    match_score: float = Field(default=0)
    tech_match: str = Field(default="")
    experience_match: str = Field(default="")
    pros: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    cons: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    recommend: bool = Field(default=False)
    greeting_messages: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class JobEval(JobEvalBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id")
    job: Optional[Job] = Relationship(back_populates="evaluations")


class JobEvalCreate(JobEvalBase):
    job_id: int
