"""Thu thập và chấm điểm bài viral về AI trên X trong N giờ gần nhất.

Không mở trình duyệt, không cần API key. Nguồn dữ liệu:
  1. FxTwitter API v2  (api.fxtwitter.com/2)  — timeline từng tài khoản + tìm kiếm. Miễn phí.
  2. X syndication     (syndication.twitter.com) — dự phòng khi FxTwitter lỗi. Miễn phí, ~30 request/cửa sổ.
  3. Hacker News Algolia — bối cảnh chủ đề nóng ngoài X. Miễn phí.
  4. (tuỳ chọn, trả phí) xAI Grok x_search — chỉ chạy khi có XAI_API_KEY và bật trong settings.

Chạy qua CLI chung:  viral.py collect x [--hours 24] [--limit-accounts 20] [--no-search] [--out <thư mục>]
"""
from __future__ import annotations

import json
import math
import os
import re
import statistics
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from core import context
from core.http import Http
from core.store import Store, local_now
from core.util import build_kw_regex, clamp01, log, log_scale, to_int as _int

PLATFORM = "x"
FX = "https://api.fxtwitter.com/2"
SYND = "https://syndication.twitter.com/srv/timeline-profile/screen-name/"


# ───────────────────────── Chuẩn hoá bài đăng ─────────────────────────


def norm_fx(t: dict) -> dict | None:
    """Chuẩn hoá một status của FxTwitter v2 về định dạng chung."""
    if not t or t.get("type") not in (None, "status") or not t.get("id"):
        return None
    a = t.get("author") or {}
    media = (t.get("media") or {}).get("all") or []
    mtypes = [m.get("type") for m in media if m.get("type")]
    vdur = max([m.get("duration") or 0 for m in media if m.get("type") in ("video", "gif")] or [0])
    card = t.get("card") or {}
    q = t.get("quote") or None
    rb = t.get("reposted_by") or None
    rt = t.get("replying_to") or None
    views = t.get("views")
    return {
        "id": str(t["id"]),
        "url": t.get("url") or f"https://x.com/{a.get('screen_name')}/status/{t['id']}",
        "author": a.get("screen_name") or "",
        "author_name": a.get("name") or "",
        "followers": _int(a.get("followers")),
        "verified": ((a.get("verification") or {}).get("type") or ""),
        "text": t.get("text") or "",
        "lang": t.get("lang") or "",
        "created_ts": _int(t.get("created_timestamp")),
        "likes": _int(t.get("likes")),
        "reposts": _int(t.get("reposts", t.get("retweets"))),
        "quotes": _int(t.get("quotes")),
        "replies": _int(t.get("replies")),
        "bookmarks": _int(t.get("bookmarks")),
        "views": _int(views) if views is not None else None,
        "media": mtypes,
        "video_seconds": round(vdur) if vdur else 0,
        "long_post": bool(t.get("is_note_tweet")),
        "link": card.get("url") or "",
        "link_title": card.get("title") or "",
        "community_note": bool(t.get("community_note")),
        "sensitive": bool(t.get("possibly_sensitive")),
        "is_reply": bool(rt),
        "reposted_by": (rb or {}).get("screen_name") or "",
        "quote": norm_fx(q) if q else None,
    }


_TW_TIME = "%a %b %d %H:%M:%S %z %Y"


def norm_synd(t: dict) -> dict | None:
    """Chuẩn hoá tweet từ endpoint syndication (không có views/bookmarks)."""
    if not t or not t.get("id_str"):
        return None
    u = t.get("user") or {}
    try:
        ts = int(datetime.strptime(t["created_at"], _TW_TIME).timestamp())
    except Exception:
        ts = 0
    media = ((t.get("extended_entities") or {}).get("media")) or ((t.get("entities") or {}).get("media")) or []
    mtypes = [("gif" if m.get("type") == "animated_gif" else m.get("type")) for m in media if m.get("type")]
    rs = t.get("retweeted_status")
    if rs:
        inner = norm_synd(rs)
        if inner:
            inner["reposted_by"] = u.get("screen_name") or ""
        return inner
    qs = t.get("quoted_status")
    return {
        "id": t["id_str"],
        "url": f"https://x.com/{u.get('screen_name')}/status/{t['id_str']}",
        "author": u.get("screen_name") or "",
        "author_name": u.get("name") or "",
        "followers": _int(u.get("followers_count")),
        "verified": "blue" if u.get("is_blue_verified") else "",
        "text": t.get("full_text") or t.get("text") or "",
        "lang": t.get("lang") or "",
        "created_ts": ts,
        "likes": _int(t.get("favorite_count")),
        "reposts": _int(t.get("retweet_count")),
        "quotes": _int(t.get("quote_count")),
        "replies": _int(t.get("reply_count")),
        "bookmarks": 0,
        "views": None,
        "media": mtypes,
        "video_seconds": 0,
        "long_post": False,
        "link": "",
        "link_title": "",
        "community_note": False,
        "sensitive": bool(t.get("possibly_sensitive")),
        "is_reply": bool(t.get("in_reply_to_status_id_str")),
        "reposted_by": "",
        "quote": norm_synd(qs) if qs else None,
    }


def norm_tio(t: dict) -> dict | None:
    """Chuẩn hoá tweet của twitterapi.io (nguồn dự phòng cần key, có đủ lượt xem và lượt lưu)."""
    if not t or not t.get("id"):
        return None
    a = t.get("author") or {}
    if t.get("isRetweet") and t.get("retweeted_tweet"):
        inner = norm_tio(t["retweeted_tweet"])
        if inner:
            inner["reposted_by"] = a.get("userName") or ""
        return inner
    try:
        ts = int(datetime.strptime(t.get("createdAt") or "", _TW_TIME).timestamp())
    except Exception:
        ts = 0
    urls = ((t.get("entities") or {}).get("urls")) or []
    media = ((t.get("extendedEntities") or {}).get("media")) or []
    mtypes = [("gif" if m.get("type") == "animated_gif" else m.get("type")) for m in media if m.get("type")]
    q = t.get("quoted_tweet")
    views = t.get("viewCount")
    return {
        "id": str(t["id"]),
        "url": t.get("url") or f"https://x.com/{a.get('userName')}/status/{t['id']}",
        "author": a.get("userName") or "",
        "author_name": a.get("name") or "",
        "followers": _int(a.get("followers")),
        "verified": "blue" if a.get("isBlueVerified") else "",
        "text": t.get("text") or "",
        "lang": t.get("lang") or "",
        "created_ts": ts,
        "likes": _int(t.get("likeCount")),
        "reposts": _int(t.get("retweetCount")),
        "quotes": _int(t.get("quoteCount")),
        "replies": _int(t.get("replyCount")),
        "bookmarks": _int(t.get("bookmarkCount")),
        "views": _int(views) if views is not None else None,
        "media": mtypes,
        "video_seconds": 0,
        "long_post": False,
        "link": (urls[0].get("expanded_url") or "") if urls else "",
        "link_title": "",
        "community_note": False,
        "sensitive": bool(t.get("possiblySensitive")),
        "is_reply": bool(t.get("isReply")),
        "reposted_by": "",
        "quote": norm_tio(q) if q else None,
    }


# ───────────────────────── Nguồn dữ liệu ─────────────────────────

TIO = "https://api.twitterapi.io/twitter"


class Sources:
    def __init__(self, http: Http, cfg: dict, paid: dict | None = None):
        self.http = http
        self.synd_budget = cfg.get("syndication_fallback_budget", 20)
        paid = paid or {}
        # twitterapi.io: chỉ gọi khi FxTwitter không trả được dữ liệu, và có trần số lần gọi để chặn chi phí
        self.tio_key = os.environ.get("TWITTERAPI_IO_KEY") if paid.get("twitterapi_io", True) else None
        self.tio_budget = paid.get("twitterapi_io_max_calls", 60)
        self._lock = threading.Lock()
        self.used = {"fxtwitter_timeline": 0, "twitterapi_timeline": 0, "syndication_timeline": 0,
                     "fxtwitter_search": 0, "twitterapi_search": 0}

    def _count(self, k: str) -> None:
        with self._lock:
            self.used[k] = self.used.get(k, 0) + 1

    def _tio(self, path: str, params: dict) -> dict | None:
        """Một lần gọi twitterapi.io (tối đa 20 bài, tính phí theo số bài trả về). None nếu không có key hoặc hết trần."""
        if not self.tio_key:
            return None
        with self._lock:
            if self.tio_budget <= 0:
                return None
            self.tio_budget -= 1
        st, d = self.http.get_json(f"{TIO}/{path}?{urllib.parse.urlencode(params)}", headers={"X-API-Key": self.tio_key}, retries=2)
        if st != 200 or not isinstance(d, dict) or d.get("status") == "error":
            return None
        return d

    def tio_timeline(self, handle: str) -> list[dict]:
        d = self._tio("user/last_tweets", {"userName": handle, "includeReplies": "false"})
        if not d:
            return []
        tweets = (d.get("data") or {}).get("tweets") or d.get("tweets") or []
        out = [p for p in (norm_tio(x) for x in tweets) if p]
        if out:
            self._count("twitterapi_timeline")
        return out

    def tio_search(self, q: str, feed: str) -> list[dict]:
        d = self._tio("tweet/advanced_search", {"query": q, "queryType": "Top" if feed == "top" else "Latest"})
        out = [p for p in (norm_tio(x) for x in (d or {}).get("tweets") or []) if p]
        if out:
            self._count("twitterapi_search")
        return out

    def timeline(self, handle: str) -> tuple[list[dict], str]:
        """Trả về (danh sách bài, nguồn). Thứ tự: FxTwitter → twitterapi.io (nếu có key) → syndication."""
        status, d = self.http.get_json(f"{FX}/profile/{urllib.parse.quote(handle)}/statuses?count=40")
        if d and isinstance(d.get("results"), list) and d["results"]:
            self._count("fxtwitter_timeline")
            return [p for p in (norm_fx(x) for x in d["results"]) if p], "fxtwitter"
        if status in (204,):
            return [], "fxtwitter"
        out = self.tio_timeline(handle)
        if out:
            return out, "twitterapi.io"
        with self._lock:
            allowed = self.synd_budget > 0
            if allowed:
                self.synd_budget -= 1
        if not allowed:
            return [], f"lỗi({status})"
        st, body = self.http.get(SYND + urllib.parse.quote(handle), retries=1)
        if st != 200:
            return [], f"lỗi({status}/{st})"
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', body, re.S)
        if not m:
            return [], "lỗi(parse)"
        try:
            entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
        except Exception:
            return [], "lỗi(parse)"
        out = []
        for e in entries:
            tw = (e.get("content") or {}).get("tweet")
            p = norm_synd(tw) if tw else None
            if p:
                out.append(p)
        self._count("syndication_timeline")
        return out, "syndication"

    def search(self, q: str, feed: str, retries: int | None = None) -> list[dict]:
        url = f"{FX}/search?q={urllib.parse.quote(q)}&feed={feed}&count=40"
        _, d = self.http.get_json(url, retries=retries)
        if d and isinstance(d.get("results"), list) and d["results"]:
            self._count("fxtwitter_search")
            return [p for p in (norm_fx(x) for x in d["results"]) if p]
        return self.tio_search(q, feed)  # FxTwitter rỗng hoặc lỗi → nguồn dự phòng (rỗng nếu không có key)

    def status(self, post_id: str) -> dict | None:
        _, d = self.http.get_json(f"{FX}/status/{post_id}")
        if d and d.get("status"):
            return norm_fx(d["status"])
        if d and d.get("tweet"):
            return norm_fx(d["tweet"])
        return None
def xai_discover(http: Http, model: str, hours: int) -> list[str]:
    """Tuỳ chọn trả phí: nhờ Grok x_search liệt kê bài viral về AI. Chỉ lấy ID bài,
    số liệu vẫn được kiểm chứng lại qua FxTwitter. CHƯA kiểm thử thực tế vì cần API key."""
    key = os.environ.get("XAI_API_KEY")
    if not key:
        return []
    now = datetime.now(timezone.utc)
    frm = datetime.fromtimestamp(now.timestamp() - hours * 3600, timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "model": model,
        "input": [{"role": "user", "content":
                   f"Find the 40 most viral X posts about AI (models, agents, AI tools, AI video, robotics, AI industry news) "
                   f"posted in the last {hours} hours. Prefer posts with very high views, reposts and quotes, including posts "
                   f"from small accounts that broke out. Return only a list of post URLs, one per line."}],
        "tools": [{"type": "x_search", "from_date": frm}],
    }
    st, body = http.get("https://api.x.ai/v1/responses", data=json.dumps(payload).encode(),
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, retries=1)
    if st != 200:
        log(f"  xAI x_search lỗi HTTP {st}")
        return []
    return list(dict.fromkeys(re.findall(r"(?:x|twitter)\.com/\w+/status/(\d{10,20})", body)))
def weighted_engagement(p: dict, w: dict) -> float:
    return (p["likes"] * w["likes"] + p["replies"] * w["replies"] + p["bookmarks"] * w["bookmarks"]
            + p["reposts"] * w["reposts"] + p["quotes"] * w["quotes"])


def score_post(p: dict, baseline: dict | None, now: float, S: dict) -> None:
    W, SC, T = S["weights"], S["scales"], S["tiers"]
    age_h = max((now - p["created_ts"]) / 3600, 0.5)
    views_est = p["views"] is None
    views = p["views"] if p["views"] is not None else p["likes"] * 100  # ước lượng thô khi thiếu views
    views = max(views, 1)
    E = weighted_engagement(p, W["engagement"])
    interactions = p["likes"] + p["replies"] + p["reposts"] + p["quotes"] + p["bookmarks"]
    er = interactions / views
    share_rate = (p["reposts"] + p["quotes"]) / views
    save_rate = p["bookmarks"] / views
    vph = views / age_h

    # 1) Quy mô
    s_scale = log_scale(views, SC["views_floor"], SC["views_ceiling"]) * 100

    # 2) Độ vượt trội so với mức thường của chính tác giả
    outlier_ratio, outlier_basis = None, ""
    if baseline and baseline.get("n", 0) >= 4 and baseline.get("median_E", 0) > 0:
        outlier_ratio = E / baseline["median_E"]
        outlier_basis = f"so với trung vị {baseline['n']} bài gần đây của @{p['author']}"
        s_out = clamp01(math.log10(max(outlier_ratio, 1)) / math.log10(SC["outlier_ceiling"])) * 100
    else:
        reach = views / max(p["followers"], 1000)
        outlier_basis = "ước lượng theo lượt xem / follower (chưa có lịch sử tác giả)"
        s_out = log_scale(reach, SC["reach_ratio_floor"], SC["reach_ratio_ceiling"]) * 100
    reach_ratio = views / max(p["followers"], 1)

    # 3) Tốc độ
    s_vel = log_scale(vph, SC["velocity_floor"], SC["velocity_ceiling"]) * 100

    # 4) Chất lượng tương tác
    s_qual = (clamp01(er / SC["er_excellent"]) * 60
              + clamp01(share_rate / SC["share_rate_excellent"]) * 25
              + clamp01(save_rate / SC["save_rate_excellent"]) * 15)

    ws = W["score"]
    bonus = min(len(p.get("amplifiers", [])) * W["amplifier_bonus_each"], W["amplifier_bonus_max"])
    total = min(ws["scale"] * s_scale + ws["outlier"] * s_out + ws["velocity"] * s_vel + ws["quality"] * s_qual + bonus, 100)

    # Bài nghi được chạy quảng cáo: lượt xem rất cao nhưng gần như không ai tương tác.
    # Lượt xem mua được, tương tác thì không → hạ điểm theo tỷ lệ tương tác.
    ad_floor = SC.get("ad_er_floor", 0.0025)
    suspected_ad = (not views_est) and views >= 100000 and er < SC.get("ad_er_flag", 0.0015)
    if not views_est and er < ad_floor:
        total *= max(er / ad_floor, 0.35)

    # Xếp hạng theo định nghĩa viral
    o = outlier_ratio if outlier_ratio is not None else (reach_ratio if reach_ratio >= 1 else 0)
    if suspected_ad:
        tier = "hot"
    elif views >= T["mega_views"]:
        tier = "mega"
    elif (views >= T["viral_views"] and (o >= T["viral_outlier"] or er >= T["viral_er"])) or \
         (o >= T["viral_alt_outlier"] and views >= T["viral_alt_views"]):
        tier = "viral"
    elif o >= T["breakout_outlier"] and views >= T["breakout_views"]:
        tier = "breakout"
    elif age_h <= T["rising_max_age_hours"] and vph >= T["rising_views_per_hour"]:
        tier = "rising"
    else:
        tier = "hot"

    # Dấu hiệu gợi ý "vì sao viral" (bằng chứng số liệu cho bước phân tích)
    sig = []
    L = max(p["likes"], 1)
    if p["bookmarks"] / L >= 0.45:
        sig.append("luu-nhieu")          # hữu ích, đáng lưu → hợp video hướng dẫn
    if p["replies"] / L >= 0.25:
        sig.append("tranh-luan")         # gây tranh cãi → hợp video quan điểm
    if p["quotes"] / max(p["reposts"], 1) >= 0.5 and p["quotes"] >= 100:
        sig.append("nhieu-quote")        # mọi người thêm ý kiến riêng
    if (p["reposts"] + p["quotes"]) / L >= 0.2:
        sig.append("lan-truyen-manh")    # tỷ lệ chia sẻ cao
    if reach_ratio >= 3:
        sig.append("vuot-tep-follower")  # lan ra ngoài tệp người theo dõi
    if "video" in p["media"]:
        sig.append("co-video")
    elif p["media"]:
        sig.append("co-hinh")
    if p["long_post"]:
        sig.append("bai-dai")
    if p.get("amplifiers"):
        sig.append("kol-khuech-dai")
    if age_h <= 12:
        sig.append("con-moi")
    if p["community_note"]:
        sig.append("co-community-note")  # cảnh báo: nội dung bị cộng đồng đính chính
    if suspected_ad:
        sig.append("nghi-quang-cao")     # cảnh báo: lượt xem cao bất thường so với tương tác

    p.update({
        "age_hours": round(age_h, 1),
        "views_estimated": views_est,
        "views_used": int(views),
        "engagement_weighted": int(E),
        "er": round(er, 4),
        "share_rate": round(share_rate, 5),
        "save_rate": round(save_rate, 5),
        "views_per_hour": int(vph),
        "reach_ratio": round(reach_ratio, 2),
        "outlier_ratio": round(outlier_ratio, 2) if outlier_ratio is not None else None,
        "outlier_basis": outlier_basis,
        "score": round(total, 1),
        "score_parts": {"scale": round(s_scale), "outlier": round(s_out), "velocity": round(s_vel),
                        "quality": round(s_qual), "bonus": bonus},
        "tier": tier,
        "signals": sig,
    })
def collect(args) -> int:
    """args: hours, limit_accounts, no_search, out (xem viral.py)."""
    store = Store(PLATFORM)
    S = store.settings()
    WL = store.watchlist()
    hours = args.hours or S["window_hours"]
    now = time.time()
    since = now - hours * 3600

    http = Http(S["http"])
    src = Sources(http, S["http"], S.get("optional_paid"))
    kw_strong = build_kw_regex(S["ai_keywords"])
    kw_weak = build_kw_regex(S.get("ai_keywords_weak") or ["zzzznone"])
    kw_bad = build_kw_regex(S.get("exclude_keywords") or ["zzzznone"])

    langs = [x.lower() for x in S.get("languages", [])]
    strip_re = re.compile(r"@\w+|https?://\S+")

    def lang_ok(p: dict) -> bool:
        return not langs or (p.get("lang") or "").lower() in langs

    def ai_relevant(p: dict) -> bool:
        # bỏ @mention và link trước khi dò từ khoá (tránh dính các bài chỉ gọi "@grok")
        blob = " ".join([p["text"], p.get("link_title") or "", (p.get("quote") or {}).get("text") or ""])
        blob = strip_re.sub(" ", blob)
        if kw_strong.search(blob):
            return True
        return len(set(m.group(0).lower() for m in kw_weak.finditer(blob))) >= 2

    # handle → nhóm
    accounts: dict[str, dict] = {}
    for g in WL["groups"]:
        for h in g["handles"]:
            accounts.setdefault(h.lower(), {"handle": h, "group": g["name"], "kind": g["kind"], "filter": g.get("filter", "none")})
    acc_list = list(accounts.values())
    if args.limit_accounts:
        acc_list = acc_list[: args.limit_accounts]

    posts: dict[str, dict] = {}            # id → bài ứng viên
    baselines: dict[str, list[float]] = {}  # handle(lower) → danh sách E của bài gốc cũ hơn 12h
    amplifiers: dict[str, set] = {}        # id → các tài khoản trong danh sách đã repost/quote
    acct_report = []
    lock = threading.Lock()
    Wg = S["weights"]["engagement"]

    def add_candidate(p: dict, source: str, group: str = "", kind: str = "") -> None:
        if not p or not p["created_ts"] or p["created_ts"] < since or p["is_reply"]:
            return
        if kw_bad.search(p["text"]):
            return
        with lock:
            cur = posts.get(p["id"])
            if cur is None:
                p = dict(p)
                p.pop("reposted_by", None)
                p["sources"] = [source]
                p["group"] = group
                p["kind"] = kind
                posts[p["id"]] = p
            else:
                if source not in cur["sources"]:
                    cur["sources"].append(source)
                if cur["views"] is None and p["views"] is not None:  # ưu tiên bản có đủ số liệu
                    for k in ("views", "bookmarks", "video_seconds", "link", "link_title", "long_post", "community_note"):
                        cur[k] = p[k]
                if group and not cur.get("group"):
                    cur["group"], cur["kind"] = group, kind

    def amplify(post_id: str, by: str) -> None:
        with lock:
            amplifiers.setdefault(post_id, set()).add(by)

    def ingest_timeline(handle: str, items: list[dict], group: str, kind: str, filt: str) -> int:
        hl = handle.lower()
        base, n_window = [], 0
        for p in items:
            is_own = p["author"].lower() == hl and not p["reposted_by"]
            if is_own:
                if not p["is_reply"]:
                    if now - p["created_ts"] > 12 * 3600:
                        base.append(weighted_engagement(p, Wg))
                    if p["created_ts"] >= since and (filt == "none" or ai_relevant(p)):
                        add_candidate(p, f"timeline:@{handle}", group, kind)
                        n_window += 1
                q = p.get("quote")
                if q and q["created_ts"] >= since and q["author"].lower() != hl and lang_ok(q) and ai_relevant(q):
                    add_candidate(q, f"quote-bởi:@{handle}")
                    amplify(q["id"], handle)
            else:
                # bài người khác được tài khoản này repost
                if p["created_ts"] >= since and lang_ok(p) and (filt == "none" or ai_relevant(p)):
                    if p["author"].lower() in accounts or ai_relevant(p):
                        add_candidate(p, f"repost-bởi:@{handle}")
                        amplify(p["id"], handle)
        with lock:
            if base:
                baselines[hl] = base
        return n_window

    # ── 1. Quét danh sách tài khoản
    log(f"[1/4] Quét {len(acc_list)} tài khoản (cửa sổ {hours} giờ)…")

    def job_account(a: dict):
        items, source = src.timeline(a["handle"])
        n = ingest_timeline(a["handle"], items, a["group"], a["kind"], a["filter"]) if items else 0
        return {"handle": a["handle"], "group": a["group"], "source": source, "fetched": len(items), "in_window": n}

    with ThreadPoolExecutor(max_workers=S["http"]["concurrency"]) as ex:
        futs = [ex.submit(job_account, a) for a in acc_list]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            acct_report.append(r)
            if i % 25 == 0:
                log(f"      … {i}/{len(acc_list)} tài khoản, {len(posts)} bài trong cửa sổ")
    failed = [r["handle"] for r in acct_report if r["fetched"] == 0]
    log(f"      xong: {len(posts)} bài; {len(failed)} tài khoản không lấy được dữ liệu")

    # ── 2. Tìm kiếm mở rộng (bắt bài viral ngoài danh sách)
    search_report = []
    if not args.no_search:
        qs = S["search_queries"]
        log(f"[2/4] Tìm kiếm mở rộng: {len(qs)} truy vấn…")

        def job_search(q: dict, retries: int | None = 2):
            res = src.search(q["q"], q.get("feed", "latest"), retries=retries)
            n = 0
            for p in res:
                if p["created_ts"] >= since and not p["is_reply"] and lang_ok(p) and ai_relevant(p):
                    add_candidate(p, f"search:{q['q']}")
                    n += 1
            return {"q": q["q"], "feed": q.get("feed", "latest"), "returned": len(res), "in_window": n}

        with ThreadPoolExecutor(max_workers=2) as ex:  # tìm kiếm nhạy cảm hơn timeline → gọi chậm rãi
            for f in as_completed([ex.submit(job_search, q) for q in qs]):
                search_report.append(f.result())
        # FxTwitter search thỉnh thoảng trả rỗng tạm thời → thử lại tuần tự một lượt, có giới hạn thời gian
        empties = [r for r in search_report if r["returned"] == 0]
        if empties:
            log(f"      thử lại {len(empties)} truy vấn rỗng (tối đa 90 giây)…")
            t0, misses = time.time(), 0
            for r in empties:
                if time.time() - t0 > 90 or misses >= 4:
                    break
                time.sleep(2.0)
                r2 = job_search({"q": r["q"], "feed": r["feed"]}, retries=1)
                misses = 0 if r2["returned"] else misses + 1
                r.update(r2)
        log(f"      xong: tổng {len(posts)} bài; {sum(1 for r in search_report if r['returned'] == 0)} truy vấn không có kết quả")

    # ── 2b. (tuỳ chọn) xAI Grok x_search
    xai_ids = []
    if S.get("optional_paid", {}).get("xai_x_search") and os.environ.get("XAI_API_KEY"):
        log("      xAI x_search (trả phí) đang bật…")
        xai_ids = xai_discover(http, S["optional_paid"].get("xai_model", "grok-4.7"), hours)
        for pid in xai_ids:
            if pid not in posts:
                p = src.status(pid)
                if p:
                    add_candidate(p, "xai:x_search")

    # ── 3. Lọc sơ bộ, bổ sung số liệu còn thiếu, lấy lịch sử tác giả cho bài ngoài danh sách
    log("[3/4] Lọc và bổ sung số liệu…")
    for pid, amps in amplifiers.items():
        if pid in posts:
            posts[pid]["amplifiers"] = sorted(amps)

    def passes_floor(p: dict) -> bool:
        v = p["views"] if p["views"] is not None else p["likes"] * 100
        return v >= S["min_views"] or p["likes"] >= S["min_likes"]

    cands = [p for p in posts.values() if passes_floor(p)]

    # bài thiếu views (đến từ nguồn dự phòng) → hỏi lại FxTwitter theo ID
    missing = sorted([p for p in cands if p["views"] is None], key=lambda p: -p["likes"])[:40]
    if missing:
        def job_enrich(p: dict):
            full = src.status(p["id"])
            if full and full["views"] is not None:
                for k in ("views", "bookmarks", "likes", "reposts", "quotes", "replies", "video_seconds", "link", "link_title", "long_post", "community_note", "followers"):
                    p[k] = full[k]
        with ThreadPoolExecutor(max_workers=S["http"]["concurrency"]) as ex:
            list(ex.map(job_enrich, missing))

    # chấm tạm để chọn tác giả ngoài danh sách cần lấy lịch sử
    for p in cands:
        b = baselines.get(p["author"].lower())
        score_post(p, {"n": len(b), "median_E": statistics.median(b)} if b else None, now, S)
    need = []
    for p in sorted(cands, key=lambda p: -p["score"]):
        hl = p["author"].lower()
        if hl not in baselines and hl not in need:
            need.append(hl)
        if len(need) >= S["http"]["max_baseline_lookups"]:
            break
    if need:
        log(f"      lấy lịch sử {len(need)} tác giả ngoài danh sách để tính độ vượt trội…")

        def job_base(hl: str):
            items, _ = src.timeline(hl)
            base = [weighted_engagement(p, Wg) for p in items
                    if p["author"].lower() == hl and not p["reposted_by"] and not p["is_reply"] and now - p["created_ts"] > 12 * 3600]
            if base:
                with lock:
                    baselines[hl] = base
        with ThreadPoolExecutor(max_workers=S["http"]["concurrency"]) as ex:
            list(ex.map(job_base, need))

    # ── 4. Chấm điểm chính thức + lịch sử các lần chạy trước
    log("[4/4] Chấm điểm…")
    history = store.load_history()

    for p in cands:
        b = baselines.get(p["author"].lower())
        base = {"n": len(b), "median_E": statistics.median(b)} if b else None
        score_post(p, base, now, S)
        p["baseline_posts"] = base["n"] if base else 0
        Store.annotate_from_history(p, history, now)

    cands.sort(key=lambda p: -p["score"])
    # Ba rổ, mỗi rổ có hạn mức riêng để bài của người lạ không lấn hết chỗ của nguồn đáng tin:
    #   own        — bài của chính tài khoản trong danh sách (hãng, KOL, KOC)
    #   amplified  — bài của người khác được tài khoản trong danh sách repost/quote
    #   discovery  — bài tìm được qua tìm kiếm
    for p in cands:
        if p["author"].lower() in accounts:
            p["origin"] = "own"
        elif any(s.startswith(("repost-bởi:", "quote-bởi:")) for s in p["sources"]):
            p["origin"] = "amplified"
        else:
            p["origin"] = "discovery"
    quota = {"own": S.get("max_out_own", 25), "amplified": S.get("max_out_amplified", 12), "discovery": S.get("max_out_discovery", 18)}
    top = []
    for o, n in quota.items():
        top += [p for p in cands if p["origin"] == o][:n]
    top.sort(key=lambda p: -p["score"])

    # cập nhật lịch sử (giữ 10 ngày)
    history = Store.update_history(history, cands, now)

    # bối cảnh ngoài X
    hn = []
    if S.get("context_sources", {}).get("hackernews"):
        hn = context.hackernews(http, int(since), S["context_sources"].get("hackernews_min_points", 150), kw_strong)

    # gọn nhẹ cho bước phân tích
    out_posts = []
    for i, p in enumerate(top, 1):
        q = p.get("quote")
        out_posts.append({
            "n": i, "id": p["id"], "url": p["url"],
            "author": p["author"], "author_name": p["author_name"], "followers": p["followers"],
            "verified": p["verified"], "group": p.get("group", ""), "kind": p.get("kind", ""),
            "in_watchlist": p["author"].lower() in accounts, "origin": p["origin"],
            "created_utc": datetime.fromtimestamp(p["created_ts"], timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "age_hours": p["age_hours"], "lang": p["lang"],
            "text": p["text"][:900],
            "quote": {"author": q["author"], "text": q["text"][:300], "url": q["url"]} if q else None,
            "link": p["link"], "link_title": p["link_title"],
            "media": p["media"], "video_seconds": p["video_seconds"], "long_post": p["long_post"],
            "views": p["views"], "views_estimated": p["views_estimated"],
            "likes": p["likes"], "reposts": p["reposts"], "quotes": p["quotes"],
            "replies": p["replies"], "bookmarks": p["bookmarks"],
            "er": p["er"], "share_rate": p["share_rate"], "save_rate": p["save_rate"],
            "views_per_hour": p["views_per_hour"], "reach_ratio": p["reach_ratio"],
            "outlier_ratio": p["outlier_ratio"], "outlier_basis": p["outlier_basis"],
            "baseline_posts": p["baseline_posts"],
            "score": p["score"], "score_parts": p["score_parts"], "tier": p["tier"],
            "signals": p["signals"], "amplifiers": p.get("amplifiers", []),
            "sources": p["sources"][:6],
            "community_note": p["community_note"], "sensitive": p["sensitive"],
            "seen_before": p["seen_before"], "picked_before": p["picked_before"],
            "views_gain_since_last_run": p.get("views_gain_since_last_run"),
            "views_per_hour_recent": p.get("views_per_hour_recent"),
        })

    tiers = {}
    for p in cands:
        tiers[p["tier"]] = tiers.get(p["tier"], 0) + 1

    ln = local_now()
    result = {
        "meta": {
            "platform": PLATFORM,
            "generated_local": ln.strftime("%Y-%m-%d %H:%M %z"),
            "generated_ts": int(now),
            "date": ln.strftime("%Y-%m-%d"),
            "window_hours": hours,
            "accounts_scanned": len(acc_list),
            "accounts_ok": len(acc_list) - len(failed),
            "accounts_failed": sorted(failed),
            "search_queries": len(search_report),
            "search_empty": sorted(r["q"] for r in search_report if r["returned"] == 0),
            "posts_in_window": len(posts),
            "posts_passing_floor": len(cands),
            "posts_out": len(out_posts),
            "tier_counts": tiers,
            "sources_used": src.used,
            "http": http.stats,
            "xai_x_search_ids": len(xai_ids),
            "settings": {"min_views": S["min_views"], "min_likes": S["min_likes"], "max_picks": S["max_picks"],
                         "weights": S["weights"], "tiers": S["tiers"]},
        },
        "context": {"hackernews": hn},
        "posts": out_posts,
    }

    out_dir = store.write_run(result, {"accounts": sorted(acct_report, key=lambda r: r["handle"].lower()), "searches": search_report}, args.out)
    if not args.out:  # chạy thử với --out thì không ghi lịch sử
        store.save_history(history)

    # bảng tóm tắt ra màn hình
    print(f"\nĐÃ LƯU: {out_dir / 'candidates.json'}")
    print(f"Tài khoản: {result['meta']['accounts_ok']}/{len(acc_list)} OK | Bài trong {hours}h: {len(posts)} | Đạt ngưỡng: {len(cands)} | Xuất: {len(out_posts)}")
    print(f"Phân hạng: {tiers} | HTTP: {http.stats}")
    if failed:
        print("Không lấy được:", ", ".join(sorted(failed)))
    print(f"\n{'#':>2} {'điểm':>5} {'hạng':<8} {'views':>10} {'likes':>7} {'×thường':>7} {'giờ':>5}  tác giả / nội dung")
    for p in out_posts:
        o = f"{p['outlier_ratio']:.1f}" if p["outlier_ratio"] is not None else "–"
        v = f"{p['views']:,}" if p["views"] is not None else "?"
        txt = re.sub(r"\s+", " ", p["text"])[:70]
        mark = {"own": "O", "amplified": "A", "discovery": "D"}[p["origin"]]
        print(f"{p['n']:>2} {p['score']:>5} {p['tier']:<8} {v:>10} {p['likes']:>7,} {o:>7} {p['age_hours']:>5}  {mark} @{p['author']}: {txt}")
    print("\n(O = bài của tài khoản trong danh sách; A = được tài khoản trong danh sách repost/quote; D = khám phá qua tìm kiếm)")
    if result["meta"]["search_empty"]:
        print("Truy vấn không có kết quả:", "; ".join(result["meta"]["search_empty"]))
    return 0
