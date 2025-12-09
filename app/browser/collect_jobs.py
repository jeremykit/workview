from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 确保输出目录存在
Path("output").mkdir(exist_ok=True)


async def _human_pause(min_s: float = 0.5, max_s: float = 1.5) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


async def collect_jobs(search_url: str, max_count: int | None = None) -> List[JobCreate]:
    max_items = max_count or settings.max_jobs
    jobs: List[JobCreate] = []
    logger.info(f"开始爬取职位，目标 URL: {search_url}，最大数量: {max_items}")

    async with async_playwright() as p:
        logger.info(f"启动浏览器")
        browser = await p.chromium.launch(
            headless=False,  # 改为有头模式，更难被检测
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        # 仅当 storage_state.json 存在时才加载
        storage_state = None
        if settings.storage_state_path.exists():
            logger.info(f"加载登录状态: {settings.storage_state_path}")
            storage_state = str(settings.storage_state_path)
        else:
            logger.info("未找到 storage_state.json，以游客模式访问")

        context = await browser.new_context(
            storage_state=storage_state,
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
        # 增强反检测
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        page = await context.new_page()

        logger.info("访问搜索页面...")
        await page.goto(search_url, wait_until='networkidle')
        await _human_pause(3, 5)

        current_url = page.url
        logger.info(f"页面加载完成，当前 URL: {current_url}")

        # 检测是否跳转到登录或验证页
        if any(keyword in current_url.lower() for keyword in ['login', 'security-check', 'verify', 'captcha']):
            await page.screenshot(path='output/debug_security_check.png')
            logger.warning(f"检测到安全验证页面: {current_url}")
            logger.warning("截图已保存到 output/debug_security_check.png")
            logger.warning("=" * 60)
            logger.warning("请在浏览器窗口中完成滑块验证")
            logger.warning("验证完成后，程序将自动继续...")
            logger.warning("=" * 60)

            # 等待跳转回目标页面（最多等待 120 秒）
            try:
                await page.wait_for_url(
                    lambda url: 'security-check' not in url and 'login' not in url,
                    timeout=120000
                )
                logger.info(f"验证完成，已跳转到: {page.url}")
                await _human_pause(2, 4)
            except Exception as e:
                await page.screenshot(path='output/debug_verification_timeout.png')
                logger.error(f"等待验证超时: {e}")
                logger.error("截图已保存到 output/debug_verification_timeout.png")
                await context.close()
                await browser.close()
                raise RuntimeError("安全验证超时，请手动完成验证后重试")

        logger.info("模拟滚动页面...")
        for i in range(3):
            await page.mouse.wheel(0, random.randint(400, 800))
            await _human_pause(1, 2)
            logger.info(f"  滚动 {i+1}/3")

        logger.info(f"查找职位卡片，选择器: {LIST_ITEM_SELECTOR}")
        try:
            cards = await page.query_selector_all(LIST_ITEM_SELECTOR)
        except Exception as e:
            await page.screenshot(path='output/debug_query_failed.png')
            logger.error(f"查询职位卡片失败: {e}")
            logger.error("截图已保存到 output/debug_query_failed.png")
            await context.close()
            await browser.close()
            raise

        if not cards:
            await page.screenshot(path='output/debug_no_cards.png')
            logger.warning("未找到职位卡片，可能选择器失效或页面结构变化")
            logger.warning("截图已保存到 output/debug_no_cards.png")

        logger.info(f"找到 {len(cards)} 个职位卡片")
        for idx, card in enumerate(cards, 1):
            if len(jobs) >= max_items:
                logger.info(f"已达到最大数量 {max_items}，停止抓取")
                break

            logger.info(f"处理第 {idx}/{len(cards)} 个卡片")
            title = (await (await card.query_selector(TITLE_SELECTOR)).inner_text()) if await card.query_selector(TITLE_SELECTOR) else ""
            company = (await (await card.query_selector(COMPANY_SELECTOR)).inner_text()) if await card.query_selector(COMPANY_SELECTOR) else ""
            salary = (await (await card.query_selector(SALARY_SELECTOR)).inner_text()) if await card.query_selector(SALARY_SELECTOR) else ""
            city = (await (await card.query_selector(CITY_SELECTOR)).inner_text()) if await card.query_selector(CITY_SELECTOR) else ""
            link_handle = await card.query_selector(DETAIL_LINK_SELECTOR)
            detail_url = await link_handle.get_attribute("href") if link_handle else None

            if not title and not company and not salary:
                logger.warning(f"卡片 {idx} 所有字段为空，可能选择器失效")

            logger.info(f"  标题: {title[:30] if title else '(空)'}")
            logger.info(f"  公司: {company[:30] if company else '(空)'}")
            logger.info(f"  薪资: {salary}")
            logger.info(f"  城市: {city}")

            if not detail_url:
                logger.warning(f"卡片 {idx} 未找到详情链接，跳过")
                continue
            if detail_url.startswith("/"):
                detail_url = f"https://www.zhipin.com{detail_url}"
            logger.info(f"  详情页: {detail_url}")

            logger.info(f"打开详情页抓取完整 JD...")
            detail_page = await context.new_page()
            await detail_page.goto(detail_url)
            await detail_page.wait_for_timeout(1500)
            jd_elem = await detail_page.query_selector(JD_FULL_SELECTOR)
            jd_full = await jd_elem.inner_text() if jd_elem else ""

            if not jd_full:
                logger.warning(f"详情页未找到 JD 内容，选择器: {JD_FULL_SELECTOR}")
            else:
                logger.info(f"  JD 长度: {len(jd_full)} 字符")

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
            logger.info(f"成功收集第 {len(jobs)} 个职位")

        await context.close()
        await browser.close()

    logger.info(f"爬取完成，共收集 {len(jobs)} 个职位")
    return jobs
