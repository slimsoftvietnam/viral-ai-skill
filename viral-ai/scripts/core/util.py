"""Hàm nhỏ dùng chung: log, thang đo, bộ dò từ khoá, định dạng số kiểu Việt."""
from __future__ import annotations

import math
import re
import sys
import threading
from datetime import datetime, timedelta, timezone

ICT = timezone(timedelta(hours=7))
_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


def to_int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


# ───────── thang đo ─────────

def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def log_scale(x: float, lo: float, hi: float) -> float:
    """Đưa x về 0..1 theo thang log giữa lo và hi."""
    if x <= 0:
        return 0.0
    return clamp01((math.log10(x) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)))


# ───────── từ khoá ─────────

def build_kw_regex(words: list[str]) -> re.Pattern:
    parts = sorted({re.escape(w.lower()) for w in words if w.strip()}, key=len, reverse=True) or ["zzzznone"]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])", re.I)


class Relevance:
    """Bài được coi là đúng chủ đề khi có ≥1 từ khoá mạnh hoặc ≥2 từ khoá yếu khác nhau."""

    _strip = re.compile(r"@[\w.]+|https?://\S+")

    def __init__(self, strong: list[str], weak: list[str] | None = None, exclude: list[str] | None = None):
        self.strong = build_kw_regex(strong)
        self.weak = build_kw_regex(weak or [])
        self.bad = build_kw_regex(exclude or [])

    def excluded(self, text: str) -> bool:
        return bool(self.bad.search(text or ""))

    def relevant(self, *texts: str) -> bool:
        # bỏ @mention và link trước khi dò (tránh dính các bài chỉ gọi "@grok")
        blob = self._strip.sub(" ", " ".join(t for t in texts if t))
        if self.strong.search(blob):
            return True
        return len({m.group(0).lower() for m in self.weak.finditer(blob)}) >= 2


# ───────── định dạng số kiểu Việt (dùng cho báo cáo) ─────────

def num(n) -> str:
    """9,4 triệu / 639 nghìn / 842."""
    if n is None:
        return "–"
    n = float(n)
    if n >= 1e6:
        return f"{n / 1e6:.1f}".replace(".", ",").replace(",0", "") + " triệu"
    if n >= 1e4:
        return f"{n / 1e3:.0f} nghìn"
    if n >= 1e3:
        return f"{n / 1e3:.1f}".replace(".", ",").replace(",0", "") + " nghìn"
    return f"{n:.0f}"


def short(n) -> str:
    if n is None:
        return "–"
    n = float(n)
    if n >= 1e6:
        return f"{n / 1e6:.1f}".replace(".", ",").replace(",0", "") + "tr"
    if n >= 1e3:
        return f"{n / 1e3:.0f}k"
    return f"{n:.0f}"


def pct(x) -> str:
    if x is None:
        return "–"
    return f"{x * 100:.2f}".replace(".", ",") + "%"


def times(x) -> str:
    if x is None:
        return "–"
    if x >= 100:
        return f"{x:.0f}×"
    return f"{x:.1f}".replace(".", ",") + "×"


def when(created_utc: str) -> str:
    dt = datetime.strptime(created_utc, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).astimezone(ICT)
    return dt.strftime("%H:%M %d/%m")


def age(h: float) -> str:
    return f"{h:.0f} giờ trước" if h >= 1 else "dưới 1 giờ"
