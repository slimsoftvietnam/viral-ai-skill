"""Thu thập và chấm điểm video viral về AI trên TikTok trong N giờ gần nhất.

Không mở trình duyệt, không cần API key. Nguồn dữ liệu:
  1. Trang nhúng hồ sơ chính thức của TikTok (tiktok.com/embed/@handle) — 12 video mới nhất của mỗi tài khoản,
     kèm lượt xem và số follower. Đây là trang TikTok công khai cho các website nhúng, không có lớp chặn.
     Giới hạn: KHÔNG có lượt thích, bình luận, chia sẻ, lưu; không tìm theo từ khoá hay hashtag.
  2. (tuỳ chọn, cần token) Apify actor — tìm theo hashtag/từ khoá, có đủ số liệu. Tắt mặc định, chưa kiểm thử.
  3. Hacker News Algolia — bối cảnh chủ đề nóng. Miễn phí.

Cố ý KHÔNG dùng: trang video và API nội bộ của TikTok (có lớp chống bot, không vượt qua),
các dịch vụ trung gian đang bị Cloudflare chặn.

Thời điểm đăng được giải mã từ ID video (32 bit cao của ID là thời gian Unix), nên không cần gọi thêm.

Chạy qua CLI chung:  viral.py collect tiktok [--hours 24] [--limit-accounts 20] [--out <thư mục>]
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
from core.util import Relevance, clamp01, log, log_scale, to_int

PLATFORM = "tiktok"
EMBED = "https://www.tiktok.com/embed/@"
_STATE_RE = re.compile(r'<script id="__FRONTITY_CONNECT_STATE__"[^>]*>(.*?)</script>', re.S)
_TAG_RE = re.compile(r"#([^\s#@]+)")
_MENTION_RE = re.compile(r"@([A-Za-z0-9_.]{2,24})")
# Trong tiếng Việt "ai" viết thường nghĩa là "người nào". Với tài khoản Việt chỉ tính "AI" viết hoa hoặc hashtag #ai.
_VI_AI_RE = re.compile(r"(?<![#\w])ai(?!\w)")


def id_to_ts(video_id: str) -> int:
    """ID video TikTok chứa thời điểm tạo ở 32 bit cao."""
    try:
        return int(video_id) >> 32
    except (TypeError, ValueError):
        return 0


# ───────────────────────── Nguồn dữ liệu ─────────────────────────

class Sources:
    def __init__(self, http: Http):
        self.http = http
        self._lock = threading.Lock()
        self.used = {"tiktok_embed": 0, "apify": 0}

    def _count(self, k: str) -> None:
        with self._lock:
            self.used[k] = self.used.get(k, 0) + 1

    def creator(self, handle: str) -> tuple[dict | None, list[dict], str]:
        """Trả về (thông tin tài khoản, danh sách video đã chuẩn hoá, trạng thái)."""
        st, body = self.http.get(EMBED + urllib.parse.quote(handle))
        if st != 200:
            return None, [], f"lỗi({st})"
        m = _STATE_RE.search(body)
        if not m:
            return None, [], "lỗi(không có dữ liệu nhúng)"
        try:
            data = json.loads(m.group(1))["source"]["data"]
            node = next(v for k, v in data.items() if k.startswith("/embed/@"))
        except Exception:
            return None, [], "lỗi(parse)"
        ui = node.get("userInfo") or {}
        vl = node.get("videoList") or []
        if not ui.get("uniqueId") or node.get("isError"):
            return None, [], f"lỗi(tài khoản không tồn tại hoặc riêng tư, code {ui.get('code')})"
        self._count("tiktok_embed")
        user = {
            "handle": ui.get("uniqueId"), "name": ui.get("nickname") or "", "followers": to_int(ui.get("followerCount")),
            "hearts": to_int(ui.get("heartCount")), "verified": bool(ui.get("verified")), "bio": ui.get("signature") or "",
        }
        ids = [to_int(v.get("id")) for v in vl]
        vids = []
        for i, v in enumerate(vl):
            vid = str(v.get("id") or "")
            if not vid or v.get("privateItem"):
                continue
            # video ghim nằm đầu danh sách nhưng cũ hơn một video đứng sau nó
            pinned = any(ids[i] < later for later in ids[i + 1:])
            vids.append(norm_video(vid, v.get("desc") or "", user, to_int(v.get("playCount")), pinned=pinned))
        return user, vids, "ok"

    def apify_discover(self, cfg: dict, hours: int) -> list[dict]:
        """Tuỳ chọn: tìm video theo hashtag/từ khoá qua Apify (cần APIFY_TOKEN, có gói miễn phí giới hạn).
        CHƯA kiểm thử thực tế vì cần token. Trả về video đã chuẩn hoá, có đủ thích/bình luận/chia sẻ/lưu."""
        return self._apify(cfg, {
            "hashtags": cfg.get("hashtags", []), "searchQueries": cfg.get("search_queries", []),
            "resultsPerPage": cfg.get("results_per_query", 30), "oldestPostDateUnified": f"{max(hours // 24, 1)} days",
        })

    def apify_enrich(self, cfg: dict, urls: list[str]) -> dict[str, dict]:
        """Lấy thích/bình luận/chia sẻ/lưu cho các video đã lọt vòng (theo URL). Trả về {id video: video}.
        Tính phí theo số video trả về, nên chỉ gọi cho nhóm đầu bảng."""
        if not urls:
            return {}
        return {v["id"]: v for v in self._apify(cfg, {"postURLs": urls, "resultsPerPage": 1})}

    def apify_profiles(self, cfg: dict, handles: list[str], per_profile: int = 12) -> dict[str, list[dict]]:
        """Dự phòng khi trang nhúng không trả được một kênh. Trả về {handle thường: danh sách video}."""
        out: dict[str, list[dict]] = {}
        if handles:
            for v in self._apify(cfg, {"profiles": handles, "resultsPerPage": per_profile, "profileSorting": "latest"}):
                out.setdefault(v["author"].lower(), []).append(v)
        return out

    def _apify(self, cfg: dict, payload: dict) -> list[dict]:
        token = os.environ.get("APIFY_TOKEN")
        if not token:
            return []
        actor = cfg.get("apify_actor", "clockworks~tiktok-scraper")
        payload = {**payload, "shouldDownloadVideos": False, "shouldDownloadCovers": False, "shouldDownloadSubtitles": False}
        url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
        old_timeout, self.http.timeout = self.http.timeout, 300
        try:
            st, body = self.http.get(url, data=json.dumps(payload).encode(), retries=1,
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        finally:
            self.http.timeout = old_timeout
        if st not in (200, 201):
            log(f"  Apify lỗi HTTP {st}")
            return []
        try:
            items = json.loads(body)
        except json.JSONDecodeError:
            return []
        out = []
        for it in items if isinstance(items, list) else []:
            am = it.get("authorMeta") or {}
            vid = str(it.get("id") or "")
            name = am.get("name") or it.get("authorMeta.name")  # một số bản xuất làm phẳng trường
            if not vid or not name or it.get("errorCode"):
                continue
            user = {"handle": name, "name": am.get("nickName") or "", "followers": to_int(am.get("fans") or it.get("authorMeta.fans")),
                    "hearts": to_int(am.get("heart")), "verified": bool(am.get("verified")), "bio": am.get("signature") or ""}
            p = norm_video(vid, it.get("text") or "", user, to_int(it.get("playCount")), pinned=bool(it.get("isPinned")))
            p.update({"likes": to_int(it.get("diggCount")), "comments": to_int(it.get("commentCount")),
                      "shares": to_int(it.get("shareCount")), "saves": to_int(it.get("collectCount")),
                      "video_seconds": to_int((it.get("videoMeta") or {}).get("duration"))})
            if it.get("createTime"):
                p["created_ts"] = to_int(it["createTime"])
            out.append(p)
        self._count("apify")
        return out


def norm_video(vid: str, desc: str, user: dict, views: int, pinned: bool = False) -> dict:
    return {
        "id": vid,
        "url": f"https://www.tiktok.com/@{user['handle']}/video/{vid}",
        "author": user["handle"], "author_name": user["name"], "followers": user["followers"],
        "verified": "verified" if user["verified"] else "",
        "text": desc.strip(),
        "hashtags": [t.lower() for t in _TAG_RE.findall(desc)][:15],
        "mentions": [m for m in _MENTION_RE.findall(desc)][:8],
        "created_ts": id_to_ts(vid),
        "views": views,
        "likes": None, "comments": None, "shares": None, "saves": None,  # nguồn miễn phí không có
        "video_seconds": 0,
        "pinned": pinned,
    }


# ───────────────────────── Chấm điểm ─────────────────────────

def score_video(p: dict, baseline: dict | None, now: float, S: dict) -> None:
    W, SC, T = S["weights"]["score"], S["scales"], S["tiers"]
    age_h = max((now - p["created_ts"]) / 3600, 0.5)
    views = max(p["views"], 1)
    vph = views / age_h
    reach_ratio = views / max(p["followers"], 1)

    # 1) Quy mô
    s_scale = log_scale(views, SC["views_floor"], SC["views_ceiling"]) * 100

    # 2) Độ vượt trội so với mức thường của chính tài khoản (trung vị lượt xem các video khác)
    outlier_ratio, outlier_basis = None, ""
    if baseline and baseline["n"] >= S["baseline_min_videos"] and baseline["median_views"] > 0:
        outlier_ratio = views / baseline["median_views"]
        outlier_basis = f"so với trung vị lượt xem {baseline['n']} video gần đây của @{p['author']}"
        s_out = clamp01(math.log10(max(outlier_ratio, 1)) / math.log10(SC["outlier_ceiling"])) * 100
    else:
        outlier_basis = "ước lượng theo lượt xem / follower (tài khoản có quá ít video để so)"
        s_out = log_scale(reach_ratio, SC["reach_ratio_floor"], SC["reach_ratio_ceiling"]) * 100

    # 3) Tốc độ
    s_vel = log_scale(vph, SC["velocity_floor"], SC["velocity_ceiling"]) * 100

    # 4) Phần thứ tư: chất lượng tương tác nếu nguồn có số liệu, nếu không thì độ lan ra ngoài tệp follower
    has_eng = p["likes"] is not None
    er = share_rate = save_rate = None
    if has_eng:
        inter = p["likes"] + (p["comments"] or 0) + (p["shares"] or 0) + (p["saves"] or 0)
        er = inter / views
        share_rate = (p["shares"] or 0) / views
        save_rate = (p["saves"] or 0) / views
        s_4 = (clamp01(er / SC["er_excellent"]) * 60 + clamp01(share_rate / SC["share_rate_excellent"]) * 25
               + clamp01(save_rate / SC["save_rate_excellent"]) * 15)
        fourth = "quality"
    else:
        s_4 = log_scale(reach_ratio, SC["reach_ratio_floor"], SC["reach_ratio_ceiling"]) * 100
        fourth = "reach"

    total = min(W["scale"] * s_scale + W["outlier"] * s_out + W["velocity"] * s_vel + W["fourth"] * s_4, 100)

    # Tài khoản hãng có video vọt lên hàng chục lần mức thường: gần như luôn là quảng cáo trả tiền (Spark Ads),
    # không phải lan truyền tự nhiên. Nguồn miễn phí không có số tương tác để kiểm chứng, nên gắn nhãn và trừ điểm.
    suspected_ad = (p.get("kind") == "brand" and outlier_ratio is not None and outlier_ratio >= SC["ad_outlier_flag"]
                    and (er is None or er < SC["ad_er_flag"]))
    if suspected_ad:
        total *= 0.6

    o = outlier_ratio if outlier_ratio is not None else (reach_ratio if reach_ratio >= 1 else 0)
    if views >= T["mega_views"]:
        tier = "mega"
    elif (views >= T["viral_views"] and o >= T["viral_outlier"]) or (o >= T["viral_alt_outlier"] and views >= T["viral_alt_views"]):
        tier = "viral"
    elif o >= T["breakout_outlier"] and views >= T["breakout_views"]:
        tier = "breakout"
    elif age_h <= T["rising_max_age_hours"] and vph >= T["rising_views_per_hour"]:
        tier = "rising"
    else:
        tier = "hot"

    sig = []
    if suspected_ad:
        sig.append("nghi-quang-cao")
    if reach_ratio >= 2:
        sig.append("vuot-tep-follower")      # lượt xem gấp ≥2 lần follower: đã lên For You của người lạ
    if p["followers"] < 50000 and views >= 250000:
        sig.append("tk-nho-bung-no")          # tài khoản nhỏ mà nổ: công thức nội dung tự thân, đáng học nhất
    if outlier_ratio is not None and outlier_ratio >= 5:
        sig.append("vuot-xa-muc-thuong")
    if age_h <= 12:
        sig.append("con-moi")
    if p.get("pinned"):
        sig.append("duoc-ghim")
    if has_eng:
        L = max(p["likes"], 1)
        if (p["saves"] or 0) / L >= 0.15:
            sig.append("luu-nhieu")
        if (p["shares"] or 0) / L >= 0.10:
            sig.append("chia-se-manh")
        if (p["comments"] or 0) / L >= 0.05:
            sig.append("tranh-luan")
    else:
        sig.append("thieu-so-tuong-tac")      # nguồn miễn phí không có thích/bình luận/chia sẻ

    p.update({
        "age_hours": round(age_h, 1),
        "views_estimated": False,
        "er": round(er, 4) if er is not None else None,
        "share_rate": round(share_rate, 5) if share_rate is not None else None,
        "save_rate": round(save_rate, 5) if save_rate is not None else None,
        "views_per_hour": int(vph),
        "reach_ratio": round(reach_ratio, 2),
        "outlier_ratio": round(outlier_ratio, 2) if outlier_ratio is not None else None,
        "outlier_basis": outlier_basis,
        "baseline_posts": baseline["n"] if baseline else 0,
        "baseline_median_views": int(baseline["median_views"]) if baseline else None,
        "score": round(total, 1),
        "score_parts": {"scale": round(s_scale), "outlier": round(s_out), "velocity": round(s_vel), fourth: round(s_4)},
        "tier": tier,
        "signals": sig,
    })


# ───────────────────────── Chương trình chính ─────────────────────────

def collect(args) -> int:
    """args: hours, limit_accounts, no_search, out (xem viral.py)."""
    store = Store(PLATFORM)
    S = store.settings()
    WL = store.watchlist()
    hours = args.hours or S["window_hours"]
    now = time.time()
    since = now - hours * 3600

    http = Http(S["http"])
    src = Sources(http)
    rel = Relevance(S["ai_keywords"], S.get("ai_keywords_weak"), S.get("exclude_keywords"))

    accounts: dict[str, dict] = {}
    for g in WL["groups"]:
        for h in g["handles"]:
            accounts.setdefault(h.lower(), {"handle": h, "group": g["name"], "kind": g["kind"],
                                            "filter": g.get("filter", "keyword"), "lang": g.get("lang", "en")})
    acc_list = list(accounts.values())
    if args.limit_accounts:
        acc_list = acc_list[: args.limit_accounts]

    posts: dict[str, dict] = {}
    baselines: dict[str, dict] = {}
    acct_report: list[dict] = []
    mention_count: dict[str, int] = {}
    lock = threading.Lock()
    base_min_age = S["baseline_min_age_hours"] * 3600

    def make_baseline(vids: list[dict], exclude_id: str = "") -> dict | None:
        others = [v for v in vids if not v["pinned"] and v["id"] != exclude_id]
        vals = [v["views"] for v in others if now - v["created_ts"] >= base_min_age]
        if len(vals) < S["baseline_min_videos"]:
            # kênh đăng dày (báo chí): 12 video mới nhất đều chưa đủ một ngày → nới xuống 6 giờ
            vals = [v["views"] for v in others if now - v["created_ts"] >= 6 * 3600]
        return {"n": len(vals), "median_views": statistics.median(vals)} if vals else None

    week_since = now - S.get("week_context_days", 7) * 86400
    older_hits: list[dict] = []   # video AI ngoài cửa sổ nhưng còn trong tuần: dùng làm bối cảnh
    floors = S.get("min_views_by_kind", {})

    def floor_of(p: dict) -> int:
        return floors.get(p["kind"], S["min_views"])

    def is_relevant(text: str, lang: str) -> bool:
        if lang == "vi":
            text = _VI_AI_RE.sub(" ", text)
        return rel.relevant(text)

    def ingest(a: dict, user: dict, vids: list[dict]) -> dict:
        n_window = n_ai = 0
        for v in vids:
            is_ai = a["filter"] == "none" or is_relevant(v["text"], a["lang"])
            n_ai += is_ai
            if not is_ai or rel.excluded(v["text"]):
                continue
            if v["created_ts"] < since:
                if v["created_ts"] >= week_since and not v["pinned"]:
                    with lock:
                        older_hits.append(dict(v, group=a["group"], kind=a["kind"], lang=a["lang"], origin=a["kind"],
                                               sources=[f"embed:@{a['handle']}"], in_watchlist=True, late=True))
                continue
            n_window += 1
            v = dict(v, group=a["group"], kind=a["kind"], lang=a["lang"], origin=a["kind"], sources=[f"embed:@{a['handle']}"],
                     in_watchlist=True)
            with lock:
                posts[v["id"]] = v
                for m in v["mentions"]:
                    if m.lower() not in accounts:
                        mention_count[m.lower()] = mention_count.get(m.lower(), 0) + 1
        with lock:
            b = make_baseline(vids)
            if b:
                baselines[a["handle"].lower()] = {"all": vids, **b}
        newest = max((v["created_ts"] for v in vids), default=0)
        return {"handle": a["handle"], "group": a["group"], "status": "ok", "followers": user["followers"],
                "fetched": len(vids), "in_window": n_window, "ai_share": round(n_ai / len(vids), 2) if vids else 0,
                "newest_days_ago": round((now - newest) / 86400, 1) if newest else None}

    # ── 1. Quét danh sách tài khoản
    log(f"[1/3] Quét {len(acc_list)} tài khoản TikTok (cửa sổ {hours} giờ)…")

    def job(a: dict) -> dict:
        user, vids, status = src.creator(a["handle"])
        if not user or not vids:
            return {"handle": a["handle"], "group": a["group"], "status": status if not user else "không có video công khai",
                    "followers": user["followers"] if user else None, "fetched": 0, "in_window": 0, "ai_share": 0, "newest_days_ago": None}
        return ingest(a, user, vids)

    with ThreadPoolExecutor(max_workers=S["http"]["concurrency"]) as ex:
        futs = [ex.submit(job, a) for a in acc_list]
        for i, f in enumerate(as_completed(futs), 1):
            acct_report.append(f.result())
            if i % 25 == 0:
                log(f"      … {i}/{len(acc_list)} tài khoản, {len(posts)} video trong cửa sổ")
    failed = sorted(r["handle"] for r in acct_report if r["fetched"] == 0)
    log(f"      xong: {len(posts)} video về AI trong cửa sổ; {len(failed)} tài khoản không lấy được")

    disc_cfg = S.get("optional_keyed", {})
    has_apify = bool(os.environ.get("APIFY_TOKEN"))

    # ── 1b. (cần token) dự phòng: kênh mà trang nhúng không trả được thì hỏi lại qua Apify
    if failed and has_apify and disc_cfg.get("apify_failover", True):
        retry = failed[: disc_cfg.get("apify_failover_max", 15)]
        log(f"      dự phòng qua Apify cho {len(retry)} tài khoản…")
        got = src.apify_profiles(disc_cfg, retry)
        for r in acct_report:
            vids = got.get(r["handle"].lower())
            if r["fetched"] == 0 and vids:
                a = accounts[r["handle"].lower()]
                user = {"handle": vids[0]["author"], "name": vids[0]["author_name"], "followers": vids[0]["followers"]}
                r.update(ingest(a, user, vids), status="ok (apify)")
        failed = sorted(r["handle"] for r in acct_report if r["fetched"] == 0)

    # ── 2. (tuỳ chọn) khám phá theo hashtag/từ khoá qua nguồn cần token
    n_disc = 0
    if not args.no_search and disc_cfg.get("apify") and os.environ.get("APIFY_TOKEN"):
        log("[2/3] Khám phá theo hashtag qua Apify (cần token)…")
        for v in src.apify_discover(disc_cfg, hours):
            if v["created_ts"] < since or not rel.relevant(v["text"]) or rel.excluded(v["text"]):
                continue
            if v["id"] in posts:  # đã có từ danh sách: bổ sung số tương tác
                for k in ("likes", "comments", "shares", "saves", "video_seconds"):
                    posts[v["id"]][k] = v[k]
                continue
            hl = v["author"].lower()
            v.update(group="Khám phá", kind="discovery", lang="", origin="discovery", sources=["apify"], in_watchlist=hl in accounts)
            posts[v["id"]] = v
            n_disc += 1
        # lấy mức thường của tác giả ngoài danh sách (tối đa N tác giả có video nhiều lượt xem nhất)
        need = []
        for v in sorted((p for p in posts.values() if p["origin"] == "discovery"), key=lambda p: -p["views"]):
            hl = v["author"].lower()
            if hl not in baselines and hl not in need:
                need.append(hl)
            if len(need) >= S["http"]["max_baseline_lookups"]:
                break

        def job_base(hl: str) -> None:
            _, vids, _ = src.creator(hl)
            b = make_baseline(vids)
            if b:
                with lock:
                    baselines[hl] = {"all": vids, **b}
        with ThreadPoolExecutor(max_workers=S["http"]["concurrency"]) as ex:
            list(ex.map(job_base, need))
    else:
        log("[2/3] Bỏ qua khám phá theo hashtag (nguồn miễn phí không hỗ trợ; xem optional_keyed trong settings)")

    # ── 3. Chấm điểm
    log("[3/3] Chấm điểm…")
    cands = [p for p in posts.values() if p["views"] >= floor_of(p)]
    wk = S.get("week_context", {})
    late = [p for p in older_hits if p["views"] >= floors.get(p["kind"], wk.get("min_views", 50000))]

    # ── 3a. (cần token) bổ sung thích/bình luận/chia sẻ/lưu cho nhóm video nhiều lượt xem nhất
    if has_apify and disc_cfg.get("apify_enrich", True):
        need_eng = sorted((p for p in cands + late if p["likes"] is None), key=lambda p: -p["views"])
        need_eng = need_eng[: disc_cfg.get("apify_enrich_max", 40)]
        if need_eng:
            log(f"      lấy số tương tác cho {len(need_eng)} video qua Apify…")
            full = src.apify_enrich(disc_cfg, [p["url"] for p in need_eng])
            for p in need_eng:
                f = full.get(p["id"])
                if f:
                    for k in ("likes", "comments", "shares", "saves", "video_seconds"):
                        p[k] = f[k]
                    p["views"] = max(p["views"], f["views"])
                    p["sources"] = p["sources"] + ["apify"]
            log(f"      có số tương tác cho {sum(1 for p in need_eng if p['likes'] is not None)}/{len(need_eng)} video")

    history = store.load_history()
    for p in cands + late:
        p.setdefault("late", False)
        b = baselines.get(p["author"].lower())
        base = make_baseline(b["all"], exclude_id=p["id"]) if b else None
        score_video(p, base, now, S)
        Store.annotate_from_history(p, history, now)
        if p.get("views_per_hour_recent") and p["views_per_hour_recent"] > p["views_per_hour"] * 1.3 and p["age_hours"] > 6:
            p["signals"].append("dang-tang-toc")  # tốc độ từ lần quét trước cao hơn tốc độ trung bình: thuật toán đang đẩy
        if p["late"]:
            p["signals"].append("ngoai-cua-so")
    cands.sort(key=lambda p: -p["score"])
    # "Còn nóng trong tuần": video ngoài cửa sổ chính nhưng vẫn vượt xa mức thường của kênh
    late = sorted((p for p in late if (p["outlier_ratio"] or 0) >= wk.get("min_outlier", 3)),
                  key=lambda p: -p["score"])[: wk.get("max_items", 12)]

    quota = S["max_out"]
    top = []
    for o, n in quota.items():
        top += [p for p in cands if p["origin"] == o][:n]
    top.sort(key=lambda p: -p["score"])
    top += late
    history = Store.update_history(history, cands + late, now)

    hn = []
    if S.get("context_sources", {}).get("hackernews"):
        hn = context.hackernews(http, int(since), S["context_sources"].get("hackernews_min_points", 150), rel.strong)

    # hashtag nổi trong các video đạt ngưỡng: tín hiệu chủ đề
    tag_stats: dict[str, dict] = {}
    for p in cands:
        for t in set(p["hashtags"]):
            ts = tag_stats.setdefault(t, {"tag": t, "videos": 0, "views": 0})
            ts["videos"] += 1
            ts["views"] += p["views"]
    generic = set(S.get("generic_hashtags", []))
    top_tags = sorted((t for t in tag_stats.values() if t["tag"] not in generic and t["videos"] >= 2), key=lambda t: -t["views"])[:20]
    suggested = sorted(({"handle": h, "mentions": n} for h, n in mention_count.items() if n >= 2), key=lambda x: -x["mentions"])[:15]

    out_posts = []
    for i, p in enumerate(top, 1):
        out_posts.append({
            "n": i, "id": p["id"], "url": p["url"],
            "author": p["author"], "author_name": p["author_name"], "followers": p["followers"], "verified": p["verified"],
            "group": p["group"], "kind": p["kind"], "lang": p["lang"], "in_watchlist": p["in_watchlist"], "origin": p["origin"],
            "created_utc": datetime.fromtimestamp(p["created_ts"], timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "age_hours": p["age_hours"],
            "text": p["text"][:900], "hashtags": p["hashtags"], "mentions": p["mentions"],
            "video_seconds": p["video_seconds"], "pinned": p["pinned"], "late": p["late"],
            "views": p["views"], "views_estimated": False,
            "likes": p["likes"], "comments": p["comments"], "shares": p["shares"], "saves": p["saves"],
            "er": p["er"], "share_rate": p["share_rate"], "save_rate": p["save_rate"],
            "views_per_hour": p["views_per_hour"], "reach_ratio": p["reach_ratio"],
            "outlier_ratio": p["outlier_ratio"], "outlier_basis": p["outlier_basis"],
            "baseline_posts": p["baseline_posts"], "baseline_median_views": p["baseline_median_views"],
            "score": p["score"], "score_parts": p["score_parts"], "tier": p["tier"], "signals": p["signals"],
            "amplifiers": [], "sources": p["sources"],
            "seen_before": p["seen_before"], "picked_before": p["picked_before"],
            "views_gain_since_last_run": p.get("views_gain_since_last_run"),
            "views_per_hour_recent": p.get("views_per_hour_recent"),
        })

    tiers: dict[str, int] = {}
    for p in cands:
        tiers[p["tier"]] = tiers.get(p["tier"], 0) + 1

    ln = local_now()
    result = {
        "meta": {
            "platform": PLATFORM,
            "generated_local": ln.strftime("%Y-%m-%d %H:%M %z"), "generated_ts": int(now), "date": ln.strftime("%Y-%m-%d"),
            "window_hours": hours,
            "accounts_scanned": len(acc_list), "accounts_ok": len(acc_list) - len(failed), "accounts_failed": failed,
            "posts_in_window": len(posts), "posts_passing_floor": len(cands), "posts_out": len(out_posts),
            "discovery_posts": n_disc, "has_engagement_stats": any(p["likes"] is not None for p in cands),
            "tier_counts": tiers, "sources_used": src.used, "http": http.stats,
            "settings": {"min_views": S["min_views"], "max_picks": S["max_picks"], "weights": S["weights"], "tiers": S["tiers"],
                         "scales": S["scales"]},
        },
        "context": {"hackernews": hn, "top_hashtags": top_tags, "suggested_handles": suggested},
        "posts": out_posts,
    }
    out_dir = store.write_run(result, {"accounts": sorted(acct_report, key=lambda r: r["handle"].lower())}, args.out)
    if not args.out:
        store.save_history(history)

    print(f"\nĐÃ LƯU: {out_dir / 'candidates.json'}")
    print(f"Tài khoản: {result['meta']['accounts_ok']}/{len(acc_list)} OK | Video AI trong {hours}h: {len(posts)} | Đạt ngưỡng: {len(cands)} | Xuất: {len(out_posts)}")
    print(f"Phân hạng: {tiers} | HTTP: {http.stats}")
    if failed:
        print("Không lấy được:", ", ".join(failed))
    print(f"\n{'#':>2} {'điểm':>5} {'hạng':<8} {'views':>10} {'×thường':>7} {'v/giờ':>8} {'giờ':>5}  tác giả / mô tả")
    for p in out_posts:
        o = f"{p['outlier_ratio']:.1f}" if p["outlier_ratio"] is not None else "–"
        txt = re.sub(r"\s+", " ", p["text"])[:60]
        mark = {"brand": "H", "creator": "C", "vn": "V", "discovery": "D"}.get(p["origin"], "?") + ("*" if p["late"] else " ")
        ad = " [nghi QC]" if "nghi-quang-cao" in p["signals"] else ""
        print(f"{p['n']:>2} {p['score']:>5} {p['tier']:<8} {p['views']:>10,} {o:>7} {p['views_per_hour']:>8,} {p['age_hours']:>5}  {mark} @{p['author']}:{ad} {txt}")
    print(f"\n(H = tài khoản hãng; C = nhà sáng tạo quốc tế; V = kênh Việt; D = khám phá qua nguồn cần token; * = đăng trước cửa sổ {hours}h nhưng còn nóng trong tuần)")
    if top_tags:
        print("Hashtag nổi:", ", ".join(f"#{t['tag']}({t['videos']})" for t in top_tags[:12]))
    if suggested:
        print("Tài khoản được nhắc nhiều, chưa có trong danh sách:", ", ".join(f"@{s['handle']}({s['mentions']})" for s in suggested))
    return 0
