"""Sổ đăng ký nền tảng. Thêm nền tảng mới = thêm một thư mục platforms/<tên>/ có collector.py và display.py,
rồi ghi tên vào PLATFORMS. Phần lõi (core/) và CLI (viral.py) không cần sửa.

Hợp đồng của một nền tảng:
    collector.collect(args) -> int
        Đọc config/<tên>/, ghi data/<tên>/<ngày>/candidates.json theo khung chung (xem docs/kien-truc.md).
    display.<hằng số và hàm>
        Cho core/report.py biết cách gọi tên, bày số liệu và giải thích phương pháp của nền tảng đó.
"""
from __future__ import annotations

import importlib
from types import ModuleType

PLATFORMS = {
    "x": "X (Twitter)",
    "tiktok": "TikTok",
}


def get(name: str) -> tuple[ModuleType, ModuleType]:
    """Trả về (collector, display) của nền tảng."""
    if name not in PLATFORMS:
        raise SystemExit(f"Không có nền tảng '{name}'. Đang có: {', '.join(PLATFORMS)}")
    return (importlib.import_module(f"platforms.{name}.collector"),
            importlib.import_module(f"platforms.{name}.display"))
