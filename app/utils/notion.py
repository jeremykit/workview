from __future__ import annotations

import logging
from typing import Iterable, List, Optional

import httpx

from app.db.models import Job, JobEval

NOTION_API_BASE = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _build_properties(job: Job, evaluation: Optional[JobEval]) -> dict:
    properties: dict = {
        "Name": {"title": [{"text": {"content": job.title[:200]}}]},
        "Company": {"rich_text": [{"text": {"content": job.company[:200]}}]},
        "City": {"rich_text": [{"text": {"content": job.city[:100]}}]},
        "Salary": {"rich_text": [{"text": {"content": job.salary[:100]}}]},
        "Detail URL": {"url": job.detail_url},
    }

    if evaluation:
        properties["Match Score"] = {"number": evaluation.match_score}
        properties["Recommend"] = {"checkbox": evaluation.recommend}
        if evaluation.greeting_messages:
            greetings = " | ".join(evaluation.greeting_messages[:2])
            properties["Greeting"] = {"rich_text": [{"text": {"content": greetings[:200]}}]}
    return properties


async def push_jobs_to_notion(
    jobs: Iterable[Job],
    evaluations: Iterable[JobEval],
    api_key: str,
    database_id: str,
    top_n: int = 10,
) -> List[str]:
    """Push top ranked jobs into a Notion database.

    The target database should contain properties: Name (title), Company (rich text),
    City (rich text), Salary (rich text), Detail URL (url), Match Score (number),
    Recommend (checkbox), and Greeting (rich text). Extra properties are ignored.

    Returns a list of created page IDs for visibility.
    """

    eval_map = {e.job_id: e for e in evaluations if e.job_id is not None}
    ranked: List[tuple[Job, Optional[JobEval]]] = []
    for job in jobs:
        ranked.append((job, eval_map.get(job.id)))
    ranked.sort(key=lambda pair: pair[1].match_score if pair[1] else 0, reverse=True)
    selected = ranked[:top_n]

    headers = _build_headers(api_key)
    created_ids: List[str] = []

    async with httpx.AsyncClient(timeout=15) as client:
        for job, evaluation in selected:
            payload = {
                "parent": {"database_id": database_id},
                "properties": _build_properties(job, evaluation),
            }
            try:
                response = await client.post(NOTION_API_BASE, headers=headers, json=payload)
                response.raise_for_status()
                created_ids.append(response.json().get("id", ""))
            except Exception as exc:  # pragma: no cover - network dependent
                logging.warning("Failed to push job to Notion: %s", exc)
                continue

    return created_ids
