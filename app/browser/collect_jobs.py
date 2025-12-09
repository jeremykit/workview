from __future__ import annotations

import asyncio
import random
from typing import List

from playwright.async_api import async_playwright

from app.browser.selectors import (
    CITY_SELECTOR,
    COMPANY_SELECTOR,
    DETAIL_LINK_SELECTOR,
    JD_FULL_SELECTOR,
    LIST_ITEM_SELECTOR,
    SALARY_SELECTOR,
    TITLE_SELECTOR,
)
from app.config import settings
from app.db.models import JobCreate


async def _human_pause(min_s: float = 0.5, max_s: float = 1.5) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


async def collect_jobs(search_url: str, max_count: int | None = None) -> List[JobCreate]:
    max_items = max_count or settings.max_jobs
    jobs: List[JobCreate] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=str(settings.storage_state_path))
        page = await context.new_page()
        await page.goto(search_url)
        await page.wait_for_timeout(2000)

        for _ in range(3):
            await page.mouse.wheel(0, random.randint(400, 800))
            await _human_pause()

        cards = await page.query_selector_all(LIST_ITEM_SELECTOR)
        for card in cards:
            if len(jobs) >= max_items:
                break
            title = (await (await card.query_selector(TITLE_SELECTOR)).inner_text()) if await card.query_selector(TITLE_SELECTOR) else ""
            company = (await (await card.query_selector(COMPANY_SELECTOR)).inner_text()) if await card.query_selector(COMPANY_SELECTOR) else ""
            salary = (await (await card.query_selector(SALARY_SELECTOR)).inner_text()) if await card.query_selector(SALARY_SELECTOR) else ""
            city = (await (await card.query_selector(CITY_SELECTOR)).inner_text()) if await card.query_selector(CITY_SELECTOR) else ""
            link_handle = await card.query_selector(DETAIL_LINK_SELECTOR)
            detail_url = await link_handle.get_attribute("href") if link_handle else None
            if not detail_url:
                continue
            if detail_url.startswith("/"):
                detail_url = f"https://www.zhipin.com{detail_url}"

            detail_page = await context.new_page()
            await detail_page.goto(detail_url)
            await detail_page.wait_for_timeout(1500)
            jd_elem = await detail_page.query_selector(JD_FULL_SELECTOR)
            jd_full = await jd_elem.inner_text() if jd_elem else ""
            await detail_page.close()
            await _human_pause()

            jobs.append(
                JobCreate(
                    title=title.strip(),
                    company=company.strip(),
                    salary=salary.strip(),
                    city=city.strip(),
                    detail_url=detail_url,
                    jd_full=jd_full.strip(),
                )
            )

        await context.close()
        await browser.close()
    return jobs
