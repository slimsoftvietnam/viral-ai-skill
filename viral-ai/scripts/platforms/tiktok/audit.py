"""Kiểm định danh sách TikTok: lấy 12 video mới nhất của từng kênh từ trang nhúng công khai."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from core.audit import summarize
from core.http import Http
from core.util import Relevance, log

from .collector import _VI_AI_RE, Sources

PROFILE_URL = "https://www.tiktok.com/@{}"
AUDIT_DEFAULTS = {"hit_floor": 100000, "hit_floor_by_kind": {"vn": 20000}, "base_min_age_hours": 24}


def sample(args, store, A: dict) -> tuple[list[dict], dict]:
    S, WL = store.settings(), store.watchlist()
    src = Sources(Http(S["http"]))
    rel = Relevance(S["ai_keywords"], S.get("ai_keywords_weak"), S.get("exclude_keywords"))
    now = time.time()
    accts: dict[str, dict] = {}
    for g in WL["groups"]:
        for h in g["handles"]:
            accts.setdefault(h.lower(), {"handle": h, "group": g["name"], "kind": g["kind"], "lang": g.get("lang", "en"),
                                         "filter": g.get("filter", "keyword"), "candidate": False})
    for h in getattr(args, "extra", None) or []:
        accts.setdefault(h.lower(), {"handle": h, "group": "Ứng viên", "kind": "creator", "lang": "en", "filter": "keyword", "candidate": True})
    todo = list(accts.values())[: args.limit_accounts or None]
    log(f"Kiểm định {len(todo)} kênh TikTok…")

    def job(a: dict) -> dict:
        user, vids, status = src.creator(a["handle"])
        row = {k: a[k] for k in ("handle", "group", "kind", "lang", "candidate")}
        row.update(status=status if user and vids else (status if not user else "không có video công khai"),
                   followers=user["followers"] if user else None)
        posts = []
        for v in vids:
            text = _VI_AI_RE.sub(" ", v["text"]) if a["lang"] == "vi" else v["text"]
            # tỷ lệ AI luôn đo bằng từ khoá, kể cả với nhóm không lọc, để biết kênh có còn đúng chủ đề không
            is_ai = rel.relevant(text) and not rel.excluded(v["text"])
            posts.append({"created_ts": v["created_ts"], "views": v["views"], "ai": is_ai or a["filter"] == "none",
                          "kw_ai": is_ai, "url": v["url"], "text": v["text"], "pinned": v["pinned"]})
        floor = A.get("hit_floor_by_kind", {}).get(a["kind"], A["hit_floor"])
        row.update(summarize(posts, now, floor, A["base_min_age_hours"]))
        own = [p for p in posts if not p["pinned"]]
        row["ai_share"] = round(sum(p["kw_ai"] for p in own) / len(own), 2) if own else 0
        return row

    with ThreadPoolExecutor(max_workers=S["http"]["concurrency"]) as ex:
        rows = list(ex.map(job, todo))
    return rows, {"sample_note": "tối đa 12 video mới nhất mỗi kênh, không tính video ghim. Chỉ có lượt xem.",
                  "http": src.http.stats if hasattr(src.http, "stats") else {}}
