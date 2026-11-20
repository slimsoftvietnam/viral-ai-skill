"""Cài đặt lần đầu và báo trạng thái, để skill luôn biết người dùng đang ở bước nào."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

from . import store

PLACEHOLDER = "CHƯA ĐIỀN"
PLATFORMS = ("x", "tiktok")


def setup(home: str = "") -> int:
    """Tạo thư mục làm việc và chép cấu hình mẫu. Không ghi đè file đã có."""
    root = Path(home).expanduser().resolve() if home else store.ROOT
    created, kept = [], []
    for sub in ("config", "data", "reports"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    for src in sorted(store.TEMPLATE.rglob("*")):
        if not src.is_file():
            continue
        dst = root / "config" / src.relative_to(store.TEMPLATE)
        if dst.exists():
            kept.append(dst)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        created.append(dst)
    guide = store.ENGINE.parent / "assets" / "huong-dan.html"
    if guide.exists():
        shutil.copyfile(guide, root / "huong-dan.html")
    try:
        store.POINTER.parent.mkdir(parents=True, exist_ok=True)
        store.POINTER.write_text(str(root), encoding="utf-8")
    except Exception as ex:  # không ghi nhớ được thì vẫn dùng được qua --home
        print(f"Không ghi nhớ được thư mục làm việc ({ex}). Lần sau thêm --home \"{root}\".", file=sys.stderr)
    store.ROOT = root
    print(f"THƯ MỤC LÀM VIỆC: {root}")
    print(f"Đã tạo {len(created)} file cấu hình, giữ nguyên {len(kept)} file có sẵn.")
    if (root / "huong-dan.html").exists():
        print(f"Tài liệu hướng dẫn: {root / 'huong-dan.html'}")
    print()
    return status()


def _channels(text: str) -> list[str]:
    """Tên kênh là phần trong ngoặc `...` ở các tiêu đề cấp 3 của mục 'Kênh của tôi'."""
    names = [m.group(1).strip() for m in re.finditer(r"^###[^\n`]*\(`([^`\n]+)`\)", text, re.M)]
    return [n for n in names if PLACEHOLDER not in n]


def _latest(root: Path, platform: str) -> dict:
    d = root / "data" / platform
    days = sorted(p.name for p in d.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)) if d.is_dir() else []
    if not days:
        return {}
    day = days[-1]
    return {
        "date": day,
        "candidates": (d / day / "candidates.json").exists(),
        "analysis": (d / day / "analysis.json").exists(),
        "report": (root / "reports" / platform / f"{day}.html").exists(),
    }


def status() -> int:
    """In trạng thái và BƯỚC TIẾP THEO. Skill gọi lệnh này đầu mỗi phiên."""
    root = store.ROOT
    today = store.local_now().strftime("%Y-%m-%d")
    print(f"Thư mục làm việc: {root}")
    print(f"Python: {sys.version.split()[0]}")
    if not (root / "config").is_dir():
        print("Trạng thái: CHƯA CÀI ĐẶT")
        print("BƯỚC TIẾP THEO: chạy `viral.py setup` (thêm --home <thư mục> nếu muốn đặt ở nơi khác).")
        return 0

    kenh = root / "config" / "kenh.md"
    text = kenh.read_text(encoding="utf-8") if kenh.exists() else ""
    chans = _channels(text)
    todo = text.count(PLACEHOLDER)
    m = re.search(r"Số ý tưởng mỗi kênh mỗi lần quét\D*(\d+)", text)
    per = int(m.group(1)) if m else 3
    print(f"Hồ sơ kênh: {len(chans)} kênh ({', '.join(chans) or 'chưa có'}); còn {todo} chỗ {PLACEHOLDER}; {per} ý tưởng mỗi kênh")

    for nt in PLATFORMS:
        wl = root / "config" / nt / "watchlist.json"
        n = 0
        if wl.exists():
            try:
                n = sum(len(g.get("handles", [])) for g in json.loads(wl.read_text(encoding="utf-8")).get("groups", []))
            except Exception:
                n = -1
        last = _latest(root, nt)
        if last:
            state = "đã có báo cáo" if last["report"] else ("đã thu thập, chưa viết phân tích" if not last["analysis"] else "đã phân tích, chưa xuất báo cáo")
            print(f"{nt}: {n} tài khoản theo dõi; lần quét gần nhất {last['date']} ({state})")
        else:
            print(f"{nt}: {n} tài khoản theo dõi; chưa quét lần nào")
    keys = {"TWITTERAPI_IO_KEY": "X dự phòng", "APIFY_TOKEN": "TikTok bổ sung"}
    print("Nguồn dự phòng: " + "; ".join(f"{lab} {'ĐÃ bật' if os.environ.get(k) else 'chưa bật'}" for k, lab in keys.items()))

    lasts = {nt: _latest(root, nt) for nt in PLATFORMS}
    if not chans or todo:
        step = "THIẾT LẬP HỒ SƠ KÊNH — hỏi người dùng về kênh của họ rồi điền config/kenh.md (xem references/thiet-lap.md)."
    elif not any(lasts.values()):
        step = "QUÉT LẦN ĐẦU — chạy `viral.py collect x` và `viral.py collect tiktok`."
    else:
        pend = [nt for nt, l in lasts.items() if l and l["candidates"] and not l["report"] and l["date"] == today]
        done_today = [nt for nt, l in lasts.items() if l and l["report"] and l["date"] == today]
        if pend:
            step = f"HOÀN TẤT LẦN QUÉT HÔM NAY — viết analysis.json rồi `viral.py render` cho: {', '.join(pend)}."
        elif len(done_today) == len(PLATFORMS):
            step = "HÔM NAY ĐÃ QUÉT XONG — mời người dùng chọn ý tưởng để viết kịch bản, hoặc chỉnh danh sách kênh."
        else:
            step = "QUÉT HÔM NAY — chạy `viral.py collect` cho nền tảng chưa quét hôm nay."
    print(f"BƯỚC TIẾP THEO: {step}")
    return 0
