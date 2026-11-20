"""Kiểm định danh sách X: lấy khoảng 20 mục mới nhất trên timeline của từng tài khoản qua FxTwitter."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor

from core.audit import summarize
from core.http import Http
from core.util import Relevance, log

from .collector import Sources

PROFILE_URL = "https://x.com/{}"
AUDIT_DEFAULTS = {"hit_floor": 100000, "base_min_age_hours": 12, "candidate_min_followers": 20000}


def _candidates(store, known: set[str], min_followers: int) -> list[str]:
    """Tác giả ngoài danh sách có bài lọt vào lần quét gần nhất và có lượng follower đáng kể."""
    d = store.day_dir()
    if not d or not (d / "candidates.json").exists():
        return []
    posts = json.loads((d / "candidates.json").read_text(encoding="utf-8"))["posts"]
    return sorted({p["author"] for p in posts if p["author"].lower() not in known and (p.get("followers") or 0) >= min_followers})


def sample(args, store, A: dict) -> tuple[list[dict], dict]:
    S, WL = store.settings(), store.watchlist()
    src = Sources(Http(S["http"]), S["http"], S.get("optional_paid"))
    rel = Relevance(S["ai_keywords"], S.get("ai_keywords_weak"), S.get("exclude_keywords"))
    now = time.time()
    accts: dict[str, dict] = {}
    for g in WL["groups"]:
        for h in g["handles"]:
            accts.setdefault(h.lower(), {"handle": h, "group": g["name"], "kind": g["kind"], "lang": "en",
                                         "filter": g.get("filter", "none"), "candidate": False})
    extra = list(getattr(args, "extra", None) or []) + _candidates(store, set(accts), A["candidate_min_followers"])
    for h in extra:
        accts.setdefault(h.lower(), {"handle": h, "group": "Ứng viên", "kind": "koc", "lang": "en", "filter": "keyword", "candidate": True})
    todo = list(accts.values())[: args.limit_accounts or None]
    log(f"Kiểm định {len(todo)} tài khoản X…")

    def job(a: dict) -> dict:
        items, source = src.timeline(a["handle"])
        if not items:  # FxTwitter thỉnh thoảng trả rỗng tạm thời
            time.sleep(3)
            items, source = src.timeline(a["handle"])
        row = {k: a[k] for k in ("handle", "group", "kind", "lang", "candidate")}
        hl = a["handle"].lower()
        own = [p for p in items if p["author"].lower() == hl and not p["reposted_by"] and not p["is_reply"]]
        row.update(status="ok" if items else f"lỗi({source})", followers=max((p["followers"] for p in own), default=None))
        posts = []
        for p in own:
            blob = " ".join([p["text"], p.get("link_title") or "", (p.get("quote") or {}).get("text") or ""])
            is_ai = rel.relevant(blob) and not rel.excluded(p["text"])
            posts.append({"created_ts": p["created_ts"], "views": p["views"], "ai": is_ai or a["filter"] == "none",
                          "kw_ai": is_ai, "url": p["url"], "text": p["text"]})
        row.update(summarize(posts, now, A["hit_floor"], A["base_min_age_hours"]))
        row["ai_share"] = round(sum(p["kw_ai"] for p in posts) / len(posts), 2) if posts else 0
        # vai trò khuếch đại: số bài của người khác mà tài khoản này repost
        row["reposts_in_sample"] = sum(1 for p in items if p["reposted_by"])
        if items and not own:
            row["status"] = "ok"
        return row

    with ThreadPoolExecutor(max_workers=S["http"]["concurrency"]) as ex:
        rows = list(ex.map(job, todo))
    return rows, {"sample_note": "khoảng 20 mục mới nhất trên timeline mỗi tài khoản, chỉ tính bài gốc (bỏ trả lời và repost).",
                  "candidates_checked": len(extra)}
