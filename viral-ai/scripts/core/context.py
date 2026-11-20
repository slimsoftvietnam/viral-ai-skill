"""Bối cảnh ngoài nền tảng: chủ đề AI giới công nghệ đang bàn (Hacker News, miễn phí, không cần key)."""
from __future__ import annotations

import re

from .http import Http


def hackernews(http: Http, since_ts: int, min_points: int, kw_re: re.Pattern) -> list[dict]:
    url = ("https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=100"
           f"&numericFilters=created_at_i%3E{since_ts},points%3E{min_points}")
    _, d = http.get_json(url)
    out = []
    for h in (d or {}).get("hits", []):
        title = h.get("title") or ""
        if kw_re.search(title):
            out.append({"title": title, "points": h.get("points"), "comments": h.get("num_comments"),
                        "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                        "hn": f"https://news.ycombinator.com/item?id={h.get('objectID')}"})
    out.sort(key=lambda x: -(x["points"] or 0))
    return out[:15]
