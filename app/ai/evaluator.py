from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from anthropic import Anthropic
from openai import OpenAI

from app.config import ModelProvider, settings
from app.db.models import Job, JobEval


def _build_prompt(job: Job, resume_profile: str) -> str:
    resume_source = (
        f"Portfolio URL (for additional context): {settings.resume_profile_url}\n"
        if settings.resume_profile_url
        else ""
    )
    return (
        "You are a career coach helping a candidate decide if a job is a fit.\n"
        "Use the resume profile and job description to produce a JSON response.\n"
        "Required JSON keys: match_score (0-100), tech_match, experience_match, pros (list), cons (list), "
        "recommend (true/false), greeting_messages (list of 2 short greetings in Chinese).\n"
        "Prioritize alignment with the candidate's personal projects and experience.\n"
        f"Resume Profile:\n{resume_profile}\n\n"
        f"{resume_source}"
        f"Job Title: {job.title}\nCompany: {job.company}\nCity: {job.city}\nSalary: {job.salary}\n"
        f"Job Description:\n{job.jd_full}\n"
        "Return ONLY the JSON string."
    )


def _parse_response(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            snippet = text[brace_start : brace_end + 1]
            return json.loads(snippet)
        raise


def evaluate_job(job: Job, resume_profile: str, api_key: str, provider: ModelProvider | None = None) -> JobEval:
    provider_to_use = provider or settings.model_provider
    prompt = _build_prompt(job, resume_profile)

    if provider_to_use == ModelProvider.ANTHROPIC:
        client = Anthropic(api_key=api_key, base_url=settings.anthropic_api_url)
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text if message.content else "{}"
    else:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise JSON generator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        content = completion.choices[0].message.content or "{}"

    try:
        parsed = _parse_response(content)
    except json.JSONDecodeError:
        parsed = {
            "match_score": 0,
            "tech_match": "解析失败",
            "experience_match": "解析失败",
            "pros": [],
            "cons": [],
            "recommend": False,
            "greeting_messages": [],
        }

    return JobEval(
        job_id=job.id,
        match_score=float(parsed.get("match_score", 0)),
        tech_match=str(parsed.get("tech_match", "")),
        experience_match=str(parsed.get("experience_match", "")),
        pros=list(parsed.get("pros", [])),
        cons=list(parsed.get("cons", [])),
        recommend=bool(parsed.get("recommend", False)),
        greeting_messages=list(parsed.get("greeting_messages", [])),
        evaluated_at=datetime.utcnow(),
    )
