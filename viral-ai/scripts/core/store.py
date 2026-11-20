"""Lưu trữ theo nền tảng: cấu hình, dữ liệu từng ngày, lịch sử các lần quét.

Bố cục trên đĩa:
    config/<nền tảng>/settings.json, watchlist.json
    data/<nền tảng>/<ngày>/candidates.json, analysis.json, accounts_report.json
    data/<nền tảng>/history.json
    reports/<nền tảng>/<ngày>.html, latest.html
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import os

ENGINE = Path(__file__).resolve().parent.parent          # thư mục scripts/ của skill
TEMPLATE = ENGINE.parent / "assets" / "config-mau"         # cấu hình mẫu đi kèm skill
POINTER = Path.home() / ".viral-ai" / "home.txt"           # ghi nhớ thư mục làm việc giữa các phiên
DEFAULT_NAME = "viral-ai-data"


def find_home() -> Path:
    """Thư mục làm việc (config/, data/, reports/) nằm NGOÀI skill để cập nhật skill không mất dữ liệu.

    Thứ tự: biến môi trường VIRAL_AI_HOME (viral.py --home đặt biến này) → file ghi nhớ →
    thư mục quen thuộc trong thư mục hiện tại → bố cục cũ (config/ nằm cạnh mã nguồn) → mặc định.
    """
    env = os.environ.get("VIRAL_AI_HOME", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    try:
        saved = Path(POINTER.read_text(encoding="utf-8").strip())
        if (saved / "config").is_dir():
            return saved
    except Exception:
        pass
    cwd = Path.cwd()
    for cand in (cwd / DEFAULT_NAME, cwd / "x-viral-ai", cwd):
        if (cand / "config" / "kenh.md").exists():
            return cand
    if (ENGINE / "config").is_dir():
        return ENGINE
    return cwd / DEFAULT_NAME


ROOT = find_home()
HISTORY_KEEP_DAYS = 10


class Store:
    def __init__(self, platform: str):
        self.platform = platform
        self.config_dir = ROOT / "config" / platform
        self.data_dir = ROOT / "data" / platform
        self.report_dir = ROOT / "reports" / platform
        self.history_path = self.data_dir / "history.json"

    # ── cấu hình
    def settings(self) -> dict:
        return json.loads((self.config_dir / "settings.json").read_text(encoding="utf-8"))

    def watchlist(self) -> dict:
        return json.loads((self.config_dir / "watchlist.json").read_text(encoding="utf-8"))

    # ── dữ liệu từng ngày
    def day_dir(self, date: str = "") -> Path | None:
        if date:
            return self.data_dir / date
        if not self.data_dir.exists():
            return None
        days = sorted(d for d in self.data_dir.iterdir() if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name))
        return days[-1] if days else None

    def write_run(self, result: dict, report: dict, out: str = "") -> Path:
        out_dir = Path(out) if out else self.data_dir / result["meta"]["date"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "candidates.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        (out_dir / "accounts_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        return out_dir

    # ── lịch sử: để không gợi ý lại bài cũ và đo đà tăng giữa hai lần quét
    def load_history(self) -> dict:
        if self.history_path.exists():
            try:
                return json.loads(self.history_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_history(self, history: dict) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def annotate_from_history(p: dict, history: dict, now: float) -> None:
        """Gắn seen_before / picked_before / đà tăng lượt xem từ lần quét trước vào bài p."""
        h = history.get(p["id"])
        if h and h.get("runs"):
            last = h["runs"][-1]
            dt_h = (now - last["ts"]) / 3600
            p["seen_before"] = True
            p["first_seen"] = h.get("first_seen")
            p["picked_before"] = bool(h.get("picked"))
            if dt_h >= 0.5 and p.get("views") is not None and last.get("views") is not None:
                p["views_gain_since_last_run"] = p["views"] - last["views"]
                p["views_per_hour_recent"] = int((p["views"] - last["views"]) / dt_h)
        else:
            p["seen_before"] = False
            p["picked_before"] = False

    @staticmethod
    def update_history(history: dict, posts: list[dict], now: float) -> dict:
        for p in posts:
            h = history.setdefault(p["id"], {"first_seen": int(now), "runs": []})
            h["runs"].append({"ts": int(now), "views": p.get("views"), "likes": p.get("likes")})
            h["runs"] = h["runs"][-12:]
            h["created_ts"] = p["created_ts"]
        return {k: v for k, v in history.items() if now - v.get("created_ts", now) < HISTORY_KEEP_DAYS * 86400}

    def mark_picked(self, ids: list[str], date: str) -> None:
        hist = self.load_history()
        if not hist:
            return
        for i in ids:
            if str(i) in hist:
                hist[str(i)]["picked"] = date
        self.save_history(hist)


def local_now() -> datetime:
    return datetime.now().astimezone()
