# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""viral.py — cổng vào duy nhất của skill viral-ai. Chỉ dùng thư viện chuẩn, Python 3.10 trở lên.

    python viral.py status                  (đang ở bước nào, làm gì tiếp)
    python viral.py setup [--home THƯ_MỤC]  (tạo thư mục làm việc, chép cấu hình mẫu; không ghi đè)
    python viral.py collect x
    python viral.py collect tiktok --hours 168
    python viral.py render x
    python viral.py check tiktok handle1 handle2           (kiểm nhanh kênh trước khi thêm vào danh sách)
    python viral.py audit all                              (kiểm định cả danh sách, mỗi 2–4 tuần)

Thư mục làm việc (config/, data/, reports/) nằm ngoài skill. Thêm --home THƯ_MỤC vào bất kỳ lệnh nào để chỉ định.

collect: thu thập + chấm điểm      → data/<nền tảng>/<ngày>/candidates.json   (máy làm phần số)
(Claude viết analysis.json theo skill viral-ai)                              (AI làm phần chữ)
render : ghép số + chữ thành báo cáo → reports/<nền tảng>/<ngày>.html
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import os

sys.path.insert(0, str(Path(__file__).resolve().parent))

# --home phải được đọc trước khi nạp core.store, vì thư mục làm việc được xác định lúc nạp.
if "--home" in sys.argv:
    _i = sys.argv.index("--home")
    if _i + 1 < len(sys.argv):
        os.environ["VIRAL_AI_HOME"] = sys.argv[_i + 1]
        del sys.argv[_i:_i + 2]

import platforms  # noqa: E402
from core import audit, report, setup  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Săn nội dung viral về AI (X, TikTok)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Liệt kê các nền tảng")
    sub.add_parser("status", help="Trạng thái cài đặt và bước tiếp theo")
    sub.add_parser("setup", help="Tạo thư mục làm việc và chép cấu hình mẫu (không ghi đè)")

    c = sub.add_parser("collect", help="Thu thập và chấm điểm")
    c.add_argument("platform", choices=list(platforms.PLATFORMS))
    c.add_argument("--hours", type=int, default=None, help="Cửa sổ thời gian (mặc định theo settings: 48)")
    c.add_argument("--limit-accounts", type=int, default=0, help="Chỉ quét N tài khoản đầu (để thử nhanh)")
    c.add_argument("--no-search", action="store_true", help="Bỏ bước tìm kiếm/khám phá")
    c.add_argument("--out", default="", help="Thư mục kết quả tạm (không ghi lịch sử)")

    r = sub.add_parser("render", help="Xuất báo cáo HTML từ candidates.json + analysis.json")
    r.add_argument("platform", choices=list(platforms.PLATFORMS))
    r.add_argument("--date", default="", help="Ngày YYYY-MM-DD (mặc định: ngày mới nhất có dữ liệu)")

    a = sub.add_parser("audit", help="Kiểm định danh sách: kênh nào đáng quét hằng ngày, kênh nào nên bỏ")
    a.add_argument("platform", choices=list(platforms.PLATFORMS) + ["all", "report"])
    a.add_argument("--limit-accounts", type=int, default=0, help="Chỉ kiểm N tài khoản đầu (để thử nhanh)")
    a.add_argument("--extra", nargs="*", default=[], help="Handle ngoài danh sách muốn kiểm thử")

    k = sub.add_parser("check", help="Kiểm nhanh vài kênh TikTok theo tiêu chí kênh mẫu")
    k.add_argument("platform", choices=["tiktok"])
    k.add_argument("handles", nargs="+", help="Tên kênh hoặc link kênh")

    args = ap.parse_args()
    if args.cmd == "list":
        for k, v in platforms.PLATFORMS.items():
            print(f"{k:<8} {v}")
        return 0
    if args.cmd == "status":
        return setup.status()
    if args.cmd == "setup":
        return setup.setup(os.environ.get("VIRAL_AI_HOME", ""))
    if args.cmd == "check":
        from platforms.tiktok.check import check
        return check(args.handles)
    if args.cmd == "audit":
        import importlib
        names = list(platforms.PLATFORMS) if args.platform in ("all", "report") else [args.platform]
        mods = {n: importlib.import_module(f"platforms.{n}.audit") for n in names}
        if args.platform != "report":
            for n in names:
                audit.run(n, mods[n], args)
        all_mods = {n: importlib.import_module(f"platforms.{n}.audit") for n in platforms.PLATFORMS}
        return audit.render(platforms.PLATFORMS, {n: m.PROFILE_URL for n, m in all_mods.items()}, audit.load_notes())
    collector, display = platforms.get(args.platform)
    if args.cmd == "collect":
        return collector.collect(args)
    return report.render(args.platform, display, args.date)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
