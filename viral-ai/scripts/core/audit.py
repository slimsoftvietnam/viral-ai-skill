"""Kiểm định danh sách tài khoản: kênh nào đáng quét hằng ngày, kênh nào nên bỏ, cần bao nhiêu kênh.

Mỗi nền tảng tự lấy mẫu (platforms/<tên>/audit.py: sample(args, store) -> (rows, info)); phần xếp hạng và báo cáo
ở đây dùng chung. Một dòng (row) cho mỗi tài khoản:

    handle, group, kind, lang, status, candidate (ngoài danh sách), followers,
    n_posts, n_ai, ai_share, span_days, ai_per_week, newest_days_ago,
    median_views, best_views, best_url, best_text, hits, hits_per_week, breakouts, hit_floor
"""
from __future__ import annotations

import html
import json
import statistics
import time
from pathlib import Path

from .store import ROOT, Store, local_now
from .util import log

TIERS = [
    ("hoc", "Học format", "Nhà sáng tạo ra bài trúng đều. Quét hằng ngày và tự theo dõi bằng tài khoản của bạn để học cách làm."),
    ("loi", "Nguồn tin lõi", "Hãng và trang tin ra bài trúng đều. Quét hằng ngày để bắt tin sớm."),
    ("giu", "Giữ", "Còn hoạt động, thỉnh thoảng có bài trúng. Quét hằng ngày, không cần tự theo dõi."),
    ("du-bi", "Dự bị", "Còn đăng nhưng trong mẫu chưa có bài nào trúng. Xét lại sau 2–4 tuần."),
    ("bo", "Nên bỏ", "Ngừng đăng, không còn nói về AI, hoặc không lấy được dữ liệu."),
]
CREATOR_KINDS = {"koc", "kol", "creator", "vn", "discovery", ""}
DEFAULTS = {"stale_days": 30, "dead_days": 120, "min_span_days": 3, "active_days": 10, "min_ai_share": 0.15, "core_hits_per_week": 1.0, "core_min_hits": 2}


def summarize(posts: list[dict], now: float, hit_floor: int, base_min_age_h: float) -> dict:
    """posts: bài gốc của chính tài khoản, mỗi bài có created_ts, views, ai (bool), url, text, pinned (tuỳ)."""
    own = [p for p in posts if not p.get("pinned")]
    ai = [p for p in own if p["ai"]]
    ts = [p["created_ts"] for p in own if p["created_ts"]]
    span = max((max(ts) - min(ts)) / 86400, 1.0) if len(ts) >= 2 else 7.0
    span = max(span, (now - min(ts)) / 86400) if ts else span   # tính cả khoảng lặng từ bài mới nhất đến nay
    settled = [p["views"] or 0 for p in ai if now - p["created_ts"] >= base_min_age_h * 3600] or [p["views"] or 0 for p in ai]
    med = statistics.median(settled) if settled else 0
    hits = [p for p in ai if (p["views"] or 0) >= hit_floor]
    best = max(ai, key=lambda p: p["views"] or 0, default=None)
    return {
        "n_posts": len(own), "n_ai": len(ai), "ai_share": round(len(ai) / len(own), 2) if own else 0,
        "span_days": round(span, 1), "ai_per_week": round(len(ai) / span * 7, 1),
        "newest_days_ago": round((now - max(ts)) / 86400, 1) if ts else None,
        "median_views": int(med), "best_views": (best["views"] or 0) if best else 0,
        "best_url": best["url"] if best else "", "best_text": (best["text"] or "")[:160] if best else "",
        "hits": len(hits), "hits_per_week": round(len(hits) / span * 7, 1),
        "breakouts": sum(1 for p in ai if med and (p["views"] or 0) >= 3 * med and (p["views"] or 0) >= hit_floor / 2),
        "hit_floor": hit_floor,
    }


def classify(r: dict, A: dict) -> tuple[str, str]:
    if r["status"] != "ok":
        if "400" in r["status"] or "không tồn tại" in r["status"] or "không có video" in r["status"]:
            return "bo", f"không lấy được dữ liệu ({r['status']})"
        return "du-bi", f"lần này không lấy được dữ liệu ({r['status']}), cần kiểm tra lại handle"
    age = r["newest_days_ago"]
    if r["n_posts"] == 0:
        return "du-bi", "các mục gần nhất chỉ có trả lời và repost, không có bài gốc"
    if age is None or age > A["dead_days"]:
        return "bo", f"bài mới nhất cách đây {age} ngày"
    if age > A["stale_days"]:
        if r["hits"] >= 2:
            return "giu", f"đăng thưa (bài mới nhất {age} ngày trước) nhưng {r['hits']}/{r['n_ai']} bài về AI đều trúng"
        return "bo", f"bài mới nhất cách đây {age} ngày, không có bài trúng đều"
    if r["hits"] == 0 and (r["n_ai"] == 0 or r["ai_share"] < A["min_ai_share"]):
        if r["span_days"] < A["min_span_days"]:
            return "du-bi", f"mẫu chỉ phủ {r['span_days']} ngày và chưa thấy bài về AI, chưa đủ để kết luận"
        return "bo", f"chỉ {round(r['ai_share'] * 100)}% bài trong {r['span_days']} ngày gần đây nói về AI, không bài nào trúng"
    if age <= A["active_days"] and r["hits"] >= A["core_min_hits"] and r["hits_per_week"] >= A["core_hits_per_week"]:
        why = f"{r['hits']}/{r['n_ai']} bài về AI trong {r['span_days']} ngày đạt ngưỡng"
        return ("hoc" if r["kind"] in CREATOR_KINDS else "loi"), why
    if r["hits"] >= 1 or r["breakouts"] >= 1:
        return "giu", f"{r['hits']}/{r['n_ai']} bài về AI trong {r['span_days']} ngày đạt ngưỡng"
    return "du-bi", f"{r['n_ai']} bài về AI trong {r['span_days']} ngày, chưa bài nào đạt ngưỡng"


def coverage(rows: list[dict]) -> dict:
    """Cần bao nhiêu tài khoản để giữ được 80% / 95% số bài trúng mỗi tuần."""
    ranked = sorted((r for r in rows if r.get("hits_per_week")), key=lambda r: -r["hits_per_week"])
    total = sum(r["hits_per_week"] for r in ranked)
    out, acc = {"total_hits_per_week": round(total, 1), "accounts_with_hits": len(ranked)}, 0.0
    for i, r in enumerate(ranked, 1):
        acc += r["hits_per_week"]
        for pct in (50, 80, 95):
            if f"n{pct}" not in out and acc >= total * pct / 100:
                out[f"n{pct}"] = i
    return out


def run(platform: str, mod, args) -> int:
    store = Store(platform)
    S = store.settings()
    A = {**DEFAULTS, **getattr(mod, "AUDIT_DEFAULTS", {}), **S.get("audit", {})}
    rows, info = mod.sample(args, store, A)
    for r in rows:
        r["tier"], r["why"] = classify(r, A)
    in_list = [r for r in rows if not r.get("candidate")]
    result = {
        "platform": platform, "date": local_now().strftime("%Y-%m-%d"), "generated_ts": int(time.time()),
        "rules": A, "info": info, "coverage": coverage(in_list),
        "tier_counts": {k: sum(1 for r in in_list if r["tier"] == k) for k, _, _ in TIERS},
        "accounts": sorted(rows, key=lambda r: (-r.get("hits_per_week", 0), -r.get("median_views", 0))),
    }
    out = store.data_dir / "audit" / f"{result['date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Đã ghi {out}")
    log(f"Xếp hạng: {result['tier_counts']} | độ phủ: {result['coverage']}")
    return 0


# ───────── báo cáo HTML gộp mọi nền tảng ─────────

def _n(v) -> str:
    if v is None:
        return "–"
    v = float(v)
    if v >= 1e6:
        return f"{v / 1e6:.1f}".replace(".", ",").replace(",0", "") + " tr"
    if v >= 1e3:
        return f"{v / 1e3:.0f} N"
    return f"{v:.0f}"


def _latest(platform: str) -> dict | None:
    d = ROOT / "data" / platform / "audit"
    files = sorted(d.glob("*.json")) if d.exists() else []
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1c1b19;--mut:#6b6860;--line:#e3e0d8;--acc:#b4532a;--ok:#2f6b4f;--warn:#9a6b00;--bad:#9b2c2c}
@media(prefers-color-scheme:dark){:root{--bg:#161513;--card:#1f1e1b;--ink:#ece9e2;--mut:#a09c92;--line:#34322d;--acc:#e08a5f;--ok:#7fc4a0;--warn:#e0b354;--bad:#e08080}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1080px;margin:0 auto;padding:28px 18px 60px}h1{font-size:26px;margin:0 0 6px}h2{font-size:20px;margin:36px 0 8px;border-top:2px solid var(--ink);padding-top:14px}
h3{font-size:16px;margin:22px 0 4px}p{margin:6px 0}.mut{color:var(--mut)}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}.tile b{display:block;font-size:22px}.tile span{color:var(--mut);font-size:13px}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mut);font-weight:600;white-space:nowrap}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}tr:last-child td{border-bottom:0}a{color:var(--acc)}
.tag{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:99px;padding:0 8px;color:var(--mut)}
details{margin:8px 0}summary{cursor:pointer;font-weight:600}.box{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:8px;padding:12px 14px;margin:12px 0}
"""


def _table(rows: list[dict], url_fmt: str, with_why: bool = True) -> str:
    if not rows:
        return '<p class="mut">Không có tài khoản nào.</p>'
    h = ['<div class="wrap"><table><tr><th>Kênh</th><th>Nhóm</th><th class="r">Follower</th><th class="r">Bài AI/tuần</th>'
         '<th class="r">Lượt xem thường</th><th class="r">Bài trúng/tuần</th><th class="r">Bài tốt nhất</th>'
         + ("<th>Căn cứ</th>" if with_why else "") + "</tr>"]
    for r in rows:
        best = f'<a href="{html.escape(r["best_url"])}">{_n(r["best_views"])}</a>' if r.get("best_url") else "–"
        cand = ' <span class="tag">ngoài danh sách</span>' if r.get("candidate") else ""
        h.append(f'<tr><td><a href="{url_fmt.format(html.escape(r["handle"]))}">@{html.escape(r["handle"])}</a>{cand}</td>'
                 f'<td class="mut">{html.escape(r.get("group") or "")}</td><td class="r">{_n(r.get("followers"))}</td>'
                 f'<td class="r">{r.get("ai_per_week", "–")}</td><td class="r">{_n(r.get("median_views"))}</td>'
                 f'<td class="r">{r.get("hits_per_week", "–")}</td><td class="r">{best}</td>'
                 + (f'<td class="mut">{html.escape(r.get("why") or "")}</td>' if with_why else "") + "</tr>")
    h.append("</table></div>")
    return "".join(h)


def render(platforms: dict, displays: dict, notes: dict | None = None) -> int:
    """Gộp bản kiểm định mới nhất của mọi nền tảng thành reports/kenh-nen-theo-doi.html."""
    notes = notes or {}
    parts, date = [], ""
    for name, label in platforms.items():
        D = _latest(name)
        if not D:
            continue
        date = max(date, D["date"])
        url_fmt = displays[name]
        rows, cov, tc = D["accounts"], D["coverage"], D["tier_counts"]
        in_list = [r for r in rows if not r.get("candidate")]
        daily = tc["hoc"] + tc["loi"] + tc["giu"]
        parts.append(f'<h2>{html.escape(label)}</h2>')
        if notes.get(name):
            parts.append(f'<div class="box">{notes[name]}</div>')
        parts.append('<div class="tiles">'
                     f'<div class="tile"><b>{len(in_list)}</b><span>kênh đang trong danh sách</span></div>'
                     f'<div class="tile"><b>{daily}</b><span>kênh nên quét hằng ngày</span></div>'
                     f'<div class="tile"><b>{tc["hoc"]}</b><span>kênh nên học format</span></div>'
                     f'<div class="tile"><b>{cov.get("n80", "–")}</b><span>kênh đủ giữ 80% số bài trúng</span></div>'
                     f'<div class="tile"><b>{tc["bo"]}</b><span>kênh nên bỏ</span></div></div>')
        parts.append(f'<p class="mut">Bài trúng: bài về AI đạt từ {_n(D["rules"]["hit_floor"])} lượt xem'
                     + (f' (kênh Việt: từ {_n(D["rules"]["hit_floor_by_kind"]["vn"])})' if D["rules"].get("hit_floor_by_kind", {}).get("vn") else "")
                     + f'. Mẫu: {html.escape(D["info"].get("sample_note", ""))}</p>')
        for key, title, desc in TIERS:
            sub = [r for r in rows if r["tier"] == key and (key != "bo" or not r.get("candidate"))]
            body = f'<p class="mut">{desc}</p>' + _table(sub, url_fmt)
            if key in ("hoc", "loi"):
                parts.append(f"<h3>{title} ({len(sub)})</h3>{body}")
            else:
                parts.append(f"<details><summary>{title} ({len(sub)})</summary>{body}</details>")
    if not parts:
        log("Chưa có bản kiểm định nào. Chạy: viral.py audit all")
        return 1
    intro = notes.get("_intro", "")
    doc = (f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Kênh nên theo dõi</title><style>{CSS}</style></head><body><main>'
           f'<h1>Kênh nên theo dõi để săn nội dung viral về AI</h1><p class="mut">Kiểm định ngày {date}. Số liệu do máy đo từ các bài gần nhất của từng kênh.</p>'
           f'{intro}{"".join(parts)}</main></body></html>')
    out = ROOT / "reports" / "kenh-nen-theo-doi.html"
    out.write_text(doc, encoding="utf-8")
    log(f"Đã ghi {out}")
    return 0


def load_notes() -> dict:
    p = ROOT / "data" / "audit-notes.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
