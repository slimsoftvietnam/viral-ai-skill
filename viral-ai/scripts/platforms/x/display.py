"""Cách bày số liệu của X trong báo cáo. core/report.py đọc các hằng số và hàm ở đây."""
from __future__ import annotations

from html import escape as e

from core.util import num, pct, short, times

NAME = "X"
NOUN = "bài"
TITLE = "Bài viral về AI trên X hôm nay"
PAGE_TITLE = "Viral AI trên X"
OPEN_LABEL = "Mở bài gốc trên X"
FRESHNESS_NOTE = "Số liệu lấy trực tiếp từ X tại thời điểm quét, mở bài gốc để xem con số mới nhất."

SIGNAL = {"luu-nhieu": "Được lưu nhiều", "tranh-luan": "Nhiều tranh luận", "nhieu-quote": "Nhiều người quote",
          "lan-truyen-manh": "Tỷ lệ chia sẻ cao", "vuot-tep-follower": "Lan ra ngoài tệp follower", "co-video": "Có video",
          "co-hinh": "Có hình", "bai-dai": "Bài dài", "kol-khuech-dai": "KOL chia sẻ lại", "con-moi": "Dưới 12 giờ",
          "co-community-note": "Có Community Note", "nghi-quang-cao": "Nghi chạy quảng cáo"}
WARN_SIGNALS = {"co-community-note", "nghi-quang-cao"}
ORIGIN = {"own": "Tài khoản trong danh sách", "amplified": "Được KOL chia sẻ lại", "discovery": "Tìm qua tìm kiếm"}
SCORE_BARS = [("Quy mô", "scale"), ("Độ vượt trội", "outlier"), ("Tốc độ", "velocity"), ("Chất lượng", "quality")]
QUICK_COL = ("Thích", lambda p: short(p["likes"]))


def metrics(p: dict) -> list[tuple[str, str, bool]]:
    """9 ô số liệu trên thẻ: (giá trị, nhãn, có phải số chính)."""
    has_base = bool(p["baseline_posts"])
    return [
        (num(p["views"]) + (" (ước lượng)" if p["views_estimated"] else ""), "Lượt xem", True),
        (times(p["outlier_ratio"]) if has_base else times(p["reach_ratio"]), "So với mức thường" if has_base else "Xem / follower", True),
        (f"{short(p['views_per_hour'])}/giờ", "Tốc độ xem", True),
        (num(p["likes"]), "Thích", False),
        (num(p["reposts"]), "Repost", False),
        (num(p["quotes"]), "Quote", False),
        (num(p["replies"]), "Trả lời", False),
        (num(p["bookmarks"]), "Lưu", False),
        (pct(p["er"]), "Tỷ lệ tương tác", False),
    ]


def media_note(p: dict) -> list[str]:
    out = []
    if "video" in p["media"]:
        out.append(f"video {p['video_seconds']} giây" if p["video_seconds"] else "video")
    if "photo" in p["media"]:
        out.append(f"{p['media'].count('photo')} ảnh")
    if p["link"]:
        out.append("có link ngoài")
    return out


def extra_html(p: dict) -> str:
    """Phần phụ dưới tóm tắt: trích bài được quote."""
    q = p.get("quote")
    return f'<p class="quote">Trích bài được quote (@{e(q["author"])}): {e(q["text"][:220])}</p>' if q else ""


def brief_source(p: dict) -> str:
    return f"{p['url']} (@{p['author']}, {num(p['views'])} lượt xem, {num(p['likes'])} thích)"


def stat_tiles(meta: dict, n_picks: int, n_now: int) -> list[tuple[str, str]]:
    tc = meta["tier_counts"]
    return [
        (str(meta["accounts_ok"]), f"tài khoản quét được trên {meta['accounts_scanned']}"),
        (str(meta["posts_in_window"]), f"bài về AI trong {meta['window_hours']} giờ"),
        (str(tc.get("mega", 0) + tc.get("viral", 0)), f"bài đạt chuẩn viral ({tc.get('mega', 0)} siêu viral)"),
        (str(n_picks), f"bài chọn cho kênh, {n_now} bài nên làm ngay"),
    ]


def context_sections(cand: dict) -> list[tuple[str, str]]:
    return []


def method_html(meta: dict) -> str:
    T, W = meta["settings"]["tiers"], meta["settings"]["weights"]
    used = meta["sources_used"]
    failed = ", ".join("@" + a for a in meta["accounts_failed"]) or "không có"
    return f"""
        <p>Một bài được coi là viral khi nó lan ra ngoài tệp người theo dõi của tác giả với tốc độ bất thường. X không công bố ngưỡng chính thức, nên báo cáo này dùng bốn phép đo cùng lúc thay vì chỉ nhìn lượt xem.</p>
        <ul>
          <li><b>Quy mô ({int(W['score']['scale'] * 100)}% điểm).</b> Lượt xem tuyệt đối, tính theo thang log.</li>
          <li><b>Độ vượt trội ({int(W['score']['outlier'] * 100)}%).</b> Tương tác của bài so với trung vị các bài gần đây của chính tác giả. Bài của tài khoản 5 triệu follower đạt 500 nghìn lượt xem là bình thường, còn tài khoản 5 nghìn follower đạt con số đó là hiện tượng.</li>
          <li><b>Tốc độ ({int(W['score']['velocity'] * 100)}%).</b> Lượt xem mỗi giờ kể từ lúc đăng.</li>
          <li><b>Chất lượng tương tác ({int(W['score']['quality'] * 100)}%).</b> Tỷ lệ tương tác trên lượt xem, tỷ lệ chia sẻ (repost, quote) và tỷ lệ lưu.</li>
        </ul>
        <p>Tương tác có trọng số: thích ×{W['engagement']['likes']}, trả lời ×{W['engagement']['replies']}, lưu ×{W['engagement']['bookmarks']}, repost ×{W['engagement']['reposts']}, quote ×{W['engagement']['quotes']}. Hành động chia sẻ được tính nặng hơn vì đó là thứ đưa bài tới người lạ.</p>
        <ul>
          <li><span class="pill t-mega">Siêu viral</span> từ {num(T['mega_views'])} lượt xem trong cửa sổ quét.</li>
          <li><span class="pill t-viral">Viral</span> từ {num(T['viral_views'])} lượt xem và gấp {T['viral_outlier']} lần mức thường (hoặc tỷ lệ tương tác từ {pct(T['viral_er'])}).</li>
          <li><span class="pill t-breakout">Bứt phá</span> gấp {T['breakout_outlier']} lần mức thường, từ {num(T['breakout_views'])} lượt xem. Đây là viral trong ngách.</li>
          <li><span class="pill t-rising">Đang lên</span> đăng chưa quá {T['rising_max_age_hours']} giờ, từ {num(T['rising_views_per_hour'])} lượt xem mỗi giờ.</li>
          <li><span class="pill t-hot">Đáng chú ý</span> qua ngưỡng tối thiểu nhưng chưa đạt các mức trên.</li>
        </ul>
        <p>Bài có lượt xem rất cao nhưng tỷ lệ tương tác dưới 0,2% bị gắn nhãn nghi chạy quảng cáo và bị trừ điểm, vì lượt xem mua được còn tương tác thì không.</p>
        <p class="foot">Nguồn: FxTwitter API (timeline {used.get('fxtwitter_timeline', 0)} lượt, tìm kiếm {used.get('fxtwitter_search', 0)} lượt), X syndication ({used.get('syndication_timeline', 0)} lượt). Tài khoản không lấy được lần này: {e(failed)}.</p>"""
