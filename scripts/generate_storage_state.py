#!/usr/bin/env python3
"""生成 BOSS 直聘登录状态文件"""

import asyncio
from playwright.async_api import async_playwright


async def generate_storage_state():
    """打开浏览器，等待手动登录，然后保存 storage state"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.zhipin.com")

        print("=" * 60)
        print("请在打开的浏览器中手动登录 BOSS 直聘")
        print("登录成功后，回到终端按 Enter 键继续...")
        print("=" * 60)

        input()  # 等待用户按 Enter

        # 保存 storage state
        await context.storage_state(path="storage_state.json")
        print("✓ storage_state.json 已保存到项目根目录")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(generate_storage_state())
