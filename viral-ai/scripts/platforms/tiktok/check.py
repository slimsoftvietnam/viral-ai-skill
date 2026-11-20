"""Kiểm nhanh vài kênh TikTok theo tiêu chí kênh mẫu, không cần chạy cả bản kiểm định.

    viral.py check tiktok handle1 handle2 …

Chỉ đo được điều kiện 2, 3, 4 (hoạt động, thắng lặp lại, đủ lớn). Điều kiện 1 (đúng ngách) và 5
(làm lại được) cần người xem video mới quyết được, nên lệnh này in caption 3 video tốt nhất để tham khảo.
"""
from __future__ import annotations

import statistics
import time

from core.http import Http
from core.store import Store

from .collector import Sources

MIN_PER_WEEK = 2
MAX_NEWEST_DAYS = 7
MIN_BREAKOUTS = 2
MIN_BEST_VIEWS = 20000


def check(handles: list[str]) -> int:
    S = Store("tiktok").settings()
    src = Sources(Http(S["http"]))
    now = time.time()
    for raw in handles:
        h = raw.strip().lstrip("@").split("?")[0].rstrip("/").split("@")[-1]
        user, vids, st = src.creator(h)
        vids = [v for v in vids if not v.get("pinned")]
        if not vids:
            print(f"@{h}: không lấy được video ({st}). Kiểm lại tên kênh, hoặc kênh không cho nhúng.\n")
            continue
        views = [v["views"] or 0 for v in vids]
        med = statistics.median(views)
        ages = [(now - v["created_ts"]) / 86400 for v in vids]
        span = max(max(ages), 1)
        per_week = len(vids) / span * 7
        brk = sum(1 for x in views if med and x >= 3 * med)
        best = max(views)
        tests = [
            ("Còn hoạt động", per_week >= MIN_PER_WEEK and min(ages) <= MAX_NEWEST_DAYS,
             f"{per_week:.1f} video mỗi tuần, video mới nhất {min(ages):.1f} ngày trước"),
            ("Thắng lặp lại", brk >= MIN_BREAKOUTS, f"{brk} video gấp từ 3 lần mức thường trong {len(vids)} video gần nhất"),
            ("Đủ lớn", best >= MIN_BEST_VIEWS, f"video tốt nhất {best:,} lượt xem, mức thường {int(med):,}"),
        ]
        ok = sum(1 for _, passed, _ in tests if passed)
        verdict = "ĐẠT cả 3 điều kiện đo được" if ok == 3 else f"đạt {ok}/3 điều kiện đo được"
        print(f"@{h} — {(user or {}).get('name', '')} — {(user or {}).get('followers', 0):,} follower — {verdict}")
        for name, passed, detail in tests:
            print(f"   [{'x' if passed else ' '}] {name}: {detail}")
        for v in sorted(vids, key=lambda v: -(v["views"] or 0))[:3]:
            print(f"       {v['views']:>9,}  {(v.get('text') or '').replace(chr(10), ' ')[:100]}")
        print()
    print("Còn hai điều kiện phải tự xem video: kênh có đúng ngách của bạn không, và một người có làm lại được không.")
    return 0
