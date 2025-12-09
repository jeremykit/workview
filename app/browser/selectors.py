from __future__ import annotations

"""
BOSS 直聘页面选择器（基于 2024-12 实际页面结构）
"""

# 列表页选择器
LIST_ITEM_SELECTOR = "li.job-card-box"
TITLE_SELECTOR = "a.job-name"
COMPANY_SELECTOR = "span.boss-name"
SALARY_SELECTOR = "span.job-salary"
CITY_SELECTOR = "span.company-location"
DETAIL_LINK_SELECTOR = "a.job-name"  # href 即详情链接

# 详情页选择器（需验证）
JD_FULL_SELECTOR = "div.job-sec-text"
