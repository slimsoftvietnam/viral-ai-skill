"""Cách bày số liệu của TikTok trong báo cáo. core/report.py đọc các hằng số và hàm ở đây."""
from __future__ import annotations

from html import escape as e

from core.util import num, pct, short, times

NAME = "TikTok"
NOUN = "video"
TITLE = "Video viral về AI trên TikTok hôm nay"
PAGE_TITLE = "Viral AI trên TikTok"
OPEN_LABEL = "Mở video gốc trên TikTok"
FRESHNESS_NOTE = "Lượt xem lấy từ trang nhúng công khai của TikTok tại thời điểm quét, TikTok làm tròn con số này. Mở video gốc để xem số mới nhất và số thích, bình luận, chia sẻ."

SIGNAL = {"vuot-tep-follower": "Lượt xem gấp đôi follower trở lên", "tk-nho-bung-no": "Tài khoản nhỏ bùng nổ",
          "vuot-xa-muc-thuong": "Gấp 5 lần mức thường trở lên", "con-moi": "Dưới 12 giờ", "duoc-ghim": "Được ghim",
          "dang-tang-toc": "Đang tăng tốc", "luu-nhieu": "Được lưu nhiều", "chia-se-manh": "Chia sẻ nhiều",
          "tranh-luan": "Nhiều bình luận", "thieu-so-tuong-tac": "Chưa có số thích, chia sẻ",
          "ngoai-cua-so": "Đăng trước cửa sổ 48 giờ, còn nóng trong tuần", "nghi-quang-cao": "Nghi chạy quảng cáo"}
WARN_SIGNALS = {"nghi-quang-cao"}
ORIGIN = {"brand": "Tài khoản hãng", "creator": "Nhà sáng tạo quốc tế", "vn": "Nhà sáng tạo Việt", "discovery": "Tìm qua hashtag"}
SCORE_BARS = [("Quy mô", "scale"), ("Độ vượt trội", "outlier"), ("Tốc độ", "velocity"),
              ("Lan ngoài tệp", "reach"), ("Chất lượng", "quality")]
QUICK_COL = ("Xem/giờ", lambda p: short(p["views_per_hour"]))


def metrics(p: dict) -> list[tuple[str, str, bool]]:
    has_base = p["outlier_ratio"] is not None
    cells = [
        (num(p["views"]), "Lượt xem", True),
        (times(p["outlier_ratio"]) if has_base else "–", "So với mức thường", True),
        (f"{short(p['views_per_hour'])}/giờ", "Tốc độ xem", True),
        (num(p.get("baseline_median_views")), "Mức thường của kênh", False),
        (times(p["reach_ratio"]), "Xem / follower", False),
        (num(p["followers"]), "Follower", False),
    ]
    if p["likes"] is not None:
        cells += [(num(p["likes"]), "Thích", False), (num(p["shares"]), "Chia sẻ", False), (pct(p["er"]), "Tỷ lệ tương tác", False)]
    return cells


def media_note(p: dict) -> list[str]:
    out = []
    if p.get("video_seconds"):
        out.append(f"video {p['video_seconds']} giây")
    if p.get("lang") == "vi":
        out.append("tiếng Việt")
    return out


def extra_html(p: dict) -> str:
    tags = " ".join("#" + t for t in p.get("hashtags", [])[:8])
    return f'<p class="quote">Hashtag gốc: {e(tags)}</p>' if tags else ""


def brief_source(p: dict) -> str:
    base = f", gấp {times(p['outlier_ratio'])} mức thường của kênh" if p["outlier_ratio"] is not None else ""
    return f"{p['url']} (@{p['author']}, {num(p['views'])} lượt xem{base})"


def stat_tiles(meta: dict, n_picks: int, n_now: int) -> list[tuple[str, str]]:
    tc = meta["tier_counts"]
    return [
        (str(meta["accounts_ok"]), f"tài khoản quét được trên {meta['accounts_scanned']}"),
        (str(meta["posts_in_window"]), f"video về AI đăng trong {meta['window_hours']} giờ"),
        (str(tc.get("mega", 0) + tc.get("viral", 0) + tc.get("breakout", 0)), f"video vượt mức thường ({tc.get('mega', 0)} siêu viral, {tc.get('viral', 0)} viral, {tc.get('breakout', 0)} bứt phá)"),
        (str(n_picks), f"video chọn cho kênh, {n_now} video nên làm ngay"),
    ]


def context_sections(cand: dict) -> list[tuple[str, str]]:
    ctx = cand.get("context", {})
    out = []
    tags = ctx.get("top_hashtags") or []
    if tags:
        rows = "".join(f'<li><b>#{e(t["tag"])}</b> <span class="muted num">{t["videos"]} video, {num(t["views"])} lượt xem</span></li>' for t in tags[:15])
        out.append(("Hashtag xuất hiện nhiều trong các video đạt ngưỡng", f"<ul>{rows}</ul>"))
    sug = ctx.get("suggested_handles") or []
    if sug:
        rows = "".join(f'<li><a href="https://www.tiktok.com/@{e(s["handle"])}" target="_blank" rel="noopener">@{e(s["handle"])}</a> <span class="muted num">được nhắc {s["mentions"]} lần</span></li>' for s in sug)
        out.append(("Tài khoản được nhắc nhiều, chưa có trong danh sách theo dõi", f"<ul>{rows}</ul>"))
    return out


def method_html(meta: dict) -> str:
    S = meta["settings"]
    T, W, SC = S["tiers"], S["weights"]["score"], S["scales"]
    failed = ", ".join("@" + a for a in meta["accounts_failed"]) or "không có"
    fourth = ("Chất lượng tương tác: tỷ lệ tương tác, chia sẻ và lưu trên lượt xem." if meta.get("has_engagement_stats")
              else "Lượt xem chia cho số follower. Trên TikTok, video lên For You của người lạ thì lượt xem vượt xa số follower.")
    return f"""
        <p>TikTok không công bố ngưỡng viral. Thuật toán For You phân phối từng video theo phản ứng của người xem (xem hết, xem lại, chia sẻ, lưu, bình luận), không theo số follower. Vì vậy một video được coi là viral khi nó <b>vượt xa mức thường của chính kênh đó</b> và tiếp tục được đẩy tới người lạ.</p>
        <ul>
          <li><b>Quy mô ({int(W['scale'] * 100)}% điểm).</b> Lượt xem, thang log từ {num(SC['views_floor'])} đến {num(SC['views_ceiling'])}.</li>
          <li><b>Độ vượt trội ({int(W['outlier'] * 100)}%).</b> Lượt xem của video chia cho trung vị lượt xem các video khác của cùng kênh (không tính video ghim, chỉ tính video đã đăng hơn một ngày). Đây là phép đo quan trọng nhất: nó cho biết nội dung thắng, không phải kênh thắng.</li>
          <li><b>Tốc độ ({int(W['velocity'] * 100)}%).</b> Lượt xem mỗi giờ kể từ lúc đăng.</li>
          <li><b>Phần thứ tư ({int(W['fourth'] * 100)}%).</b> {fourth}</li>
        </ul>
        <ul>
          <li><span class="pill t-mega">Siêu viral</span> từ {num(T['mega_views'])} lượt xem trong cửa sổ quét.</li>
          <li><span class="pill t-viral">Viral</span> từ {num(T['viral_views'])} lượt xem và gấp {T['viral_outlier']} lần mức thường, hoặc gấp {T['viral_alt_outlier']} lần với từ {num(T['viral_alt_views'])} lượt xem.</li>
          <li><span class="pill t-breakout">Bứt phá</span> gấp {T['breakout_outlier']} lần mức thường, từ {num(T['breakout_views'])} lượt xem. Viral trong ngách.</li>
          <li><span class="pill t-rising">Đang lên</span> đăng chưa quá {T['rising_max_age_hours']} giờ, từ {num(T['rising_views_per_hour'])} lượt xem mỗi giờ.</li>
          <li><span class="pill t-hot">Đáng chú ý</span> qua ngưỡng {num(S['min_views'])} lượt xem nhưng chưa đạt các mức trên.</li>
        </ul>
        <p><b>Giới hạn của nguồn miễn phí.</b> Báo cáo chỉ thấy 12 video mới nhất của các tài khoản trong danh sách theo dõi, và chỉ có lượt xem. Số thích, bình luận, chia sẻ, lưu không có, nên chưa lọc được video chạy quảng cáo: video của tài khoản hãng có lượt xem cao bất thường cần được nhìn với sự nghi ngờ. Video viral của người lạ ngoài danh sách sẽ bị sót, trừ khi bật nguồn tìm theo hashtag trong <span class="num">config/tiktok/settings.json</span>.</p>
        <p class="foot">Nguồn: trang nhúng hồ sơ TikTok ({meta['sources_used'].get('tiktok_embed', 0)} lượt), Apify ({meta['sources_used'].get('apify', 0)} lượt). Tài khoản không lấy được lần này: {e(failed)}.</p>"""
